# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import TriageForm, HospitalStatusForm, SOSForm
from .recommendation import get_hospital_recommendations
from .models import Hospital, HospitalStatus, PatientEvent, TransferRequest, Notification, AuditLog


# 1. Paramedic — Submit Triage
@login_required
def submit_triage(request):
    if request.user.role != 'paramedic':
        messages.error(request, 'Access denied. Only paramedics can submit triage.')
        return redirect('dashboard')

    form = TriageForm()

    if request.method == 'POST':
        form = TriageForm(request.POST)
        if form.is_valid():
            patient_event = form.save(commit=False)
            patient_event.submitted_by = request.user
            patient_event.status = 'pending'
            patient_event.save()

            # Audit Log
            AuditLog.objects.create(
                performed_by=request.user,
                patient_event=patient_event,
                action='triage_submitted',
                description=f'Triage submitted for {patient_event.get_case_type_display()} case.'
            )

            messages.success(request, f'Triage submitted successfully! Case #{patient_event.id}')
            return redirect('triage_success', pk=patient_event.pk)

    return render(request, 'core/submit_triage.html', {'form': form})


# 2. Triage Success Page
@login_required
def triage_success(request, pk):
    patient_event = get_object_or_404(PatientEvent, pk=pk)
    return render(request, 'core/triage_success.html', {'event': patient_event})

# 3. Hospital Admin — Update Status
@login_required
def update_hospital_status(request):
    if request.user.role != 'hospital_admin':
        messages.error(request, 'Access denied. Only hospital admins can update status.')
        return redirect('dashboard')

    # ← এখন user এর linked hospital নিবে
    hospital = request.user.hospital

    if not hospital:
        messages.error(request, 'No hospital assigned to your account. Contact System Admin.')
        return redirect('dashboard')

    latest_status = HospitalStatus.objects.filter(hospital=hospital).first()

    if request.method == 'POST':
        form = HospitalStatusForm(request.POST)
        if form.is_valid():
            status = form.save(commit=False)
            status.hospital = hospital
            status.updated_by = request.user
            status.save()

            AuditLog.objects.create(
                performed_by=request.user,
                action='status_updated',
                description=f'Hospital status updated for {hospital.name}.'
            )

            messages.success(request, f'Hospital status updated for {hospital.name}!')
            return redirect('update_hospital_status')
    else:
        if latest_status:
            form = HospitalStatusForm(instance=latest_status)
        else:
            form = HospitalStatusForm()

    return render(request, 'core/update_hospital_status.html', {
        'form': form,
        'hospital': hospital,
        'latest_status': latest_status,
    })

# 4. Hospital List View (All users)
@login_required
def hospital_list(request):
    hospitals = Hospital.objects.filter(is_active=True)

    for hospital in hospitals:
        hospital.latest_status = HospitalStatus.objects.filter(hospital=hospital).first()

    hospitals_map_data = [
        {
            'id': h.id,
            'name': h.name,
            'lat': float(h.latitude),
            'lng': float(h.longitude),
            'address': h.address,
            'specialty': h.get_specialty_display(),
            'icu': f"{h.latest_status.icu_available} / {h.latest_status.icu_total}" if h.latest_status else "N/A",
            'beds': f"{h.latest_status.bed_available} / {h.latest_status.bed_total}" if h.latest_status else "N/A",
            'accepting': h.latest_status.is_accepting if h.latest_status else False,
        }
        for h in hospitals
    ]

    return render(request, 'core/hospital_list.html', {
        'hospitals': hospitals,
        'hospitals_map_data': hospitals_map_data,
    })

# 5. Patient — SOS Emergency (Without Login)
def sos_emergency(request):
    form = SOSForm()

    if request.method == 'POST':
        form = SOSForm(request.POST)
        if form.is_valid():
            patient_event = form.save(commit=False)
            patient_event.phone_number = form.cleaned_data['phone_number']

            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            if lat and lng:
                try:
                    patient_event.latitude = float(lat)
                    patient_event.longitude = float(lng)
                except ValueError:
                    pass

            if request.user.is_authenticated:
                patient_event.submitted_by = request.user

            patient_event.status = 'pending'
            patient_event.save()

            AuditLog.objects.create(
                performed_by=request.user if request.user.is_authenticated else None,
                patient_event=patient_event,
                action='triage_submitted',
                description=f'SOS Emergency: {patient_event.get_case_type_display()} — Phone: {patient_event.phone_number}'
            )

            messages.success(request, 'SOS Emergency submitted! Help is on the way.')
            return redirect('sos_success', pk=patient_event.pk)

    return render(request, 'core/sos_emergency.html', {'form': form})


# 6. SOS Success Page
def sos_success(request, pk):
    patient_event = get_object_or_404(PatientEvent, pk=pk)
    return render(request, 'core/sos_success.html', {'event': patient_event})


# 7. Paramedic — Pending Cases List
@login_required
def pending_cases(request):
    if request.user.role != 'paramedic':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    cases = PatientEvent.objects.filter(status='pending')
    return render(request, 'core/pending_cases.html', {'cases': cases})


# 8. Recommendation — Get Hospital Recommendations
@login_required
def recommend_hospitals(request, pk):
    if request.user.role != 'paramedic':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    patient_event = get_object_or_404(PatientEvent, pk=pk)
    recommendations = get_hospital_recommendations(patient_event)

    map_data = {
        'patient': {
            'lat': float(patient_event.latitude) if patient_event.latitude else None,
            'lng': float(patient_event.longitude) if patient_event.longitude else None,
            'location': patient_event.location_text,
        },
        'hospitals': [
            {
                'name': rec['hospital'].name,
                'lat': float(rec['hospital'].latitude),
                'lng': float(rec['hospital'].longitude),
                'distance': rec['distance_km'],
                'eta': rec['eta_minutes'],
            }
            for rec in recommendations
        ]
    }

    AuditLog.objects.create(
        performed_by=request.user,
        patient_event=patient_event,
        action='recommendation_viewed',
        description=f'Viewed recommendations for Case #{patient_event.id}'
    )

    return render(request, 'core/recommend_hospitals.html', {
        'event': patient_event,
        'recommendations': recommendations,
        'map_data': map_data,
    })

# 9. Paramedic — Create Transfer Request
@login_required
def create_transfer(request, event_pk, hospital_pk):
    if request.user.role != 'paramedic':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    patient_event = get_object_or_404(PatientEvent, pk=event_pk)
    hospital = get_object_or_404(Hospital, pk=hospital_pk)

    # Check if transfer already exists
    if TransferRequest.objects.filter(patient_event=patient_event).exists():
        messages.warning(request, 'Transfer request already exists for this case.')
        return redirect('pending_cases')

    # Create Transfer Request
    transfer = TransferRequest.objects.create(
        patient_event=patient_event,
        hospital=hospital,
        requested_by=request.user,
        status='pending'
    )

    # Update patient event status
    patient_event.status = 'referred'
    patient_event.save()

    # Create Notification for hospital
    Notification.objects.create(
        hospital=hospital,
        transfer_request=transfer,
        message=f'New emergency transfer request: {patient_event.get_case_type_display()} — '
                f'Patient Age: {patient_event.patient_age}, '
                f'Location: {patient_event.location_text}',
        status='sent'
    )

    # Audit Log
    AuditLog.objects.create(
        performed_by=request.user,
        patient_event=patient_event,
        transfer_request=transfer,
        action='triage_submitted',
        description=f'Transfer request sent to {hospital.name} for Case #{patient_event.id}'
    )

    messages.success(request, f'Transfer request sent to {hospital.name}!')
    return redirect('pending_cases')


# 10. Hospital Admin — Incoming Transfer Requests
@login_required
def incoming_transfers(request):
    if request.user.role != 'hospital_admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    hospital = request.user.hospital

    if not hospital:
        messages.error(request, 'No hospital assigned to your account.')
        return redirect('dashboard')

    transfers = TransferRequest.objects.filter(hospital=hospital).order_by('-created_at')

    return render(request, 'core/incoming_transfers.html', {
        'transfers': transfers,
        'hospital': hospital,
    })

# 11. Hospital Admin — Accept/Reject Transfer
@login_required
def respond_transfer(request, pk, action):
    if request.user.role != 'hospital_admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    transfer = get_object_or_404(TransferRequest, pk=pk)

    # Verify this transfer belongs to admin's hospital
    if transfer.hospital != request.user.hospital:
        messages.error(request, 'Access denied. This transfer is not for your hospital.')
        return redirect('incoming_transfers')

    if action == 'accept':
        transfer.status = 'accepted'
        transfer.save()

        # Update patient event
        transfer.patient_event.status = 'transferred'
        transfer.patient_event.save()

        # Audit Log
        AuditLog.objects.create(
            performed_by=request.user,
            patient_event=transfer.patient_event,
            transfer_request=transfer,
            action='transfer_accepted',
            description=f'{request.user.hospital.name} accepted Case #{transfer.patient_event.id}'
        )

        messages.success(request, f'Transfer accepted for Case #{transfer.patient_event.id}!')

    elif action == 'reject':
        transfer.status = 'rejected'
        transfer.save()

        # Reset patient event to pending
        transfer.patient_event.status = 'pending'
        transfer.patient_event.save()

        # Audit Log
        AuditLog.objects.create(
            performed_by=request.user,
            patient_event=transfer.patient_event,
            transfer_request=transfer,
            action='transfer_rejected',
            description=f'{request.user.hospital.name} rejected Case #{transfer.patient_event.id}'
        )

        messages.warning(request, f'Transfer rejected for Case #{transfer.patient_event.id}.')

    return redirect('incoming_transfers')

# 12. Hospital Admin — Notifications
@login_required
def hospital_notifications(request):
    if request.user.role != 'hospital_admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    hospital = request.user.hospital

    if not hospital:
        messages.error(request, 'No hospital assigned.')
        return redirect('dashboard')

    notifications = Notification.objects.filter(hospital=hospital).order_by('-sent_at')

    return render(request, 'core/notifications.html', {
        'notifications': notifications,
        'hospital': hospital,
    })


# 13. System Admin — Manage Users
@login_required
def manage_users(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    from accounts.models import CustomUser
    users = CustomUser.objects.all().order_by('-date_joined')
    hospitals = Hospital.objects.filter(is_active=True)

    return render(request, 'core/manage_users.html', {
        'users': users,
        'hospitals': hospitals,
    })

# 14. System Admin — Edit User
@login_required
def edit_user(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    from accounts.models import CustomUser
    user = get_object_or_404(CustomUser, pk=pk)
    hospitals = Hospital.objects.filter(is_active=True)

    if request.method == 'POST':
        user.role = request.POST.get('role', user.role)
        hospital_id = request.POST.get('hospital')
        if hospital_id:
            user.hospital = Hospital.objects.get(pk=hospital_id)
        else:
            user.hospital = None
        user.is_active = request.POST.get('is_active') == 'on'
        user.save()

        messages.success(request, f'User "{user.username}" updated!')
        return redirect('manage_users')

    return render(request, 'core/edit_user.html', {
        'edit_user': user,
        'hospitals': hospitals,
    })

# 15. User Profile
@login_required
def user_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        user.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('user_profile')

    return render(request, 'core/user_profile.html')

# 22. System Admin — Reset User Password
@login_required
def reset_user_password(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    from accounts.models import CustomUser
    user = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password and new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Password reset for "{user.username}" successfully!')
            return redirect('manage_users')
        else:
            messages.error(request, 'Passwords do not match.')

    return render(request, 'core/reset_user_password.html', {'reset_user': user})