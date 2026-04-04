from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Hospital, HospitalStatus, PatientEvent, AuditLog
from .forms import TriageForm, HospitalStatusForm, SOSForm


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

    # Attach latest status to each hospital
    for hospital in hospitals:
        hospital.latest_status = HospitalStatus.objects.filter(hospital=hospital).first()

    return render(request, 'core/hospital_list.html', {'hospitals': hospitals})


# 5. Patient — SOS Emergency (Work without Login)
def sos_emergency(request):
    form = SOSForm()

    if request.method == 'POST':
        form = SOSForm(request.POST)
        if form.is_valid():
            patient_event = form.save(commit=False)
            patient_event.phone_number = form.cleaned_data['phone_number']

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