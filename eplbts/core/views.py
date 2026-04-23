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

    existing = TransferRequest.objects.filter(patient_event=patient_event).first()
    if existing and existing.status == 'pending':
        messages.error(request, 'Transfer request already pending for this case.')
        return redirect('pending_cases')
    if existing and existing.status == 'accepted':
        messages.error(request, 'This case is already accepted by a hospital.')
        return redirect('pending_cases')
    # Delete rejected transfer so new one can be created
    if existing and existing.status == 'rejected':
        existing.delete()

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

    pending_transfers = TransferRequest.objects.filter(hospital=hospital, status='pending').order_by('-created_at')
    completed_transfers = TransferRequest.objects.filter(hospital=hospital,
                                                         status__in=['accepted', 'rejected']).order_by('-created_at')[
        :20]

    return render(request, 'core/incoming_transfers.html', {
        'pending_transfers': pending_transfers,
        'completed_transfers': completed_transfers,
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
    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, pk):
    if request.user.role != 'hospital_admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    notification = get_object_or_404(Notification, pk=pk, hospital=request.user.hospital)
    notification.status = 'read'
    notification.save()
    messages.success(request, 'Notification marked as read.')
    return redirect('hospital_notifications')


# 13. Authority — Monitoring Dashboard
@login_required
def authority_dashboard(request):
    if request.user.role != 'authority':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Statistics
    total_cases = PatientEvent.objects.count()
    pending_cases_count = PatientEvent.objects.filter(status='pending').count()
    referred_cases = PatientEvent.objects.filter(status='referred').count()
    transferred_cases = PatientEvent.objects.filter(status='transferred').count()
    completed_cases = PatientEvent.objects.filter(status='completed').count()

    total_hospitals = Hospital.objects.filter(is_active=True).count()
    accepting_hospitals = 0
    overloaded_hospitals = 0

    hospitals = Hospital.objects.filter(is_active=True)
    hospital_data = []

    for h in hospitals:
        status = HospitalStatus.objects.filter(hospital=h).first()
        if status:
            if status.is_accepting:
                accepting_hospitals += 1
            if status.icu_available <= 0 or status.bed_available <= 0:
                overloaded_hospitals += 1
            hospital_data.append({
                'hospital': h,
                'status': status,
            })
        else:
            hospital_data.append({
                'hospital': h,
                'status': None,
            })

    total_transfers = TransferRequest.objects.count()
    accepted_transfers = TransferRequest.objects.filter(status='accepted').count()
    rejected_transfers = TransferRequest.objects.filter(status='rejected').count()
    pending_transfers = TransferRequest.objects.filter(status='pending').count()

    # Recent cases
    recent_cases = PatientEvent.objects.all()[:10]

    # Case type breakdown
    from django.db.models import Count
    case_type_stats = PatientEvent.objects.values('case_type').annotate(count=Count('id')).order_by('-count')

    return render(request, 'core/authority_dashboard.html', {
        'total_cases': total_cases,
        'pending_cases_count': pending_cases_count,
        'referred_cases': referred_cases,
        'transferred_cases': transferred_cases,
        'completed_cases': completed_cases,
        'total_hospitals': total_hospitals,
        'accepting_hospitals': accepting_hospitals,
        'overloaded_hospitals': overloaded_hospitals,
        'hospital_data': hospital_data,
        'total_transfers': total_transfers,
        'accepted_transfers': accepted_transfers,
        'rejected_transfers': rejected_transfers,
        'pending_transfers': pending_transfers,
        'recent_cases': recent_cases,
        'case_type_stats': case_type_stats,
    })

# 14. Audit Log View
@login_required
def audit_log_view(request):
    if request.user.role not in ['authority', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    logs = AuditLog.objects.all()[:100]
    return render(request, 'core/audit_log.html', {'logs': logs})


# 15. System Admin — Manage Hospitals
@login_required
def manage_hospitals(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    hospitals = Hospital.objects.all()
    return render(request, 'core/manage_hospitals.html', {'hospitals': hospitals})


# 16. System Admin — Add Hospital
@login_required
def add_hospital(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        phone_number = request.POST.get('phone_number')
        specialty = request.POST.get('specialty')

        if name and address and latitude and longitude:
            Hospital.objects.create(
                name=name,
                address=address,
                latitude=float(latitude),
                longitude=float(longitude),
                phone_number=phone_number or '',
                specialty=specialty or 'general',
                is_active=True,
            )
            messages.success(request, f'Hospital "{name}" added successfully!')
            return redirect('manage_hospitals')
        else:
            messages.error(request, 'Please fill all required fields.')

    return render(request, 'core/add_hospital.html')

# 17. System Admin — Edit Hospital
@login_required
def edit_hospital(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    hospital = get_object_or_404(Hospital, pk=pk)

    if request.method == 'POST':
        hospital.name = request.POST.get('name', hospital.name)
        hospital.address = request.POST.get('address', hospital.address)
        hospital.latitude = float(request.POST.get('latitude', hospital.latitude))
        hospital.longitude = float(request.POST.get('longitude', hospital.longitude))
        hospital.phone_number = request.POST.get('phone_number', hospital.phone_number)
        hospital.specialty = request.POST.get('specialty', hospital.specialty)
        hospital.is_active = request.POST.get('is_active') == 'on'
        hospital.save()

        messages.success(request, f'Hospital "{hospital.name}" updated!')
        return redirect('manage_hospitals')

    return render(request, 'core/edit_hospital.html', {'hospital': hospital})

# 18. System Admin — Delete Hospital
@login_required
def delete_hospital(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    hospital = get_object_or_404(Hospital, pk=pk)
    name = hospital.name
    hospital.delete()
    messages.success(request, f'Hospital "{name}" deleted!')
    return redirect('manage_hospitals')


# 19. System Admin — Manage Users
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

# 20. System Admin — Edit User
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

# 21. User Profile
@login_required
def user_profile(request):
    if request.method == 'POST':
        user = request.user
        new_email = request.POST.get('email', '')
        new_phone = request.POST.get('phone_number', '')

        # Email duplicate check
        from accounts.models import CustomUser
        if new_email and CustomUser.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            messages.error(request, 'This email is already used by another account.')
            return redirect('user_profile')

        # Phone duplicate check
        if new_phone and CustomUser.objects.filter(phone_number=new_phone).exclude(pk=user.pk).exists():
            messages.error(request, 'This phone number is already used by another account.')
            return redirect('user_profile')

        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = new_email
        user.phone_number = new_phone
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


# Export Audit Log as CSV
import csv
from django.http import HttpResponse


@login_required
def export_audit_csv(request):
    if request.user.role not in ['authority', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_log.csv"'

    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Role', 'Action', 'Description', 'Case ID'])

    logs = AuditLog.objects.all()[:500]
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.performed_by.username if log.performed_by else 'System',
            log.performed_by.get_role_display() if log.performed_by else '—',
            log.get_action_display(),
            log.description,
            f'EM-{log.patient_event.id}' if log.patient_event else '—',
        ])

    return response