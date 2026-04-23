from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from django.contrib.auth.decorators import login_required


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm()

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created for {user.username}! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# REPLACE your existing dashboard_view in accounts/views.py
# with this updated version that passes stats to the template
@login_required
def dashboard_view(request):
    context = {'user': request.user}

    # Paramedic stats
    if request.user.role == 'paramedic':
        from core.models import PatientEvent, TransferRequest
        from django.utils import timezone
        today = timezone.now().date()


        context['transferred_today'] = TransferRequest.objects.filter(
            requested_by=request.user, status='accepted', updated_at__date=today
        ).count()


        context['pending_count'] = PatientEvent.objects.filter(status='pending').count()
        context['active_cases'] = PatientEvent.objects.filter(
            status__in=['pending', 'referred']
        ).count()


        recent = PatientEvent.objects.order_by('-created_at')[:5]
        for case in recent:
            tr = TransferRequest.objects.filter(patient_event=case).first()
            case.hospital_name = tr.hospital.name if tr and tr.hospital else '—'
        context['recent_cases'] = recent
        for case in recent:
            tr = TransferRequest.objects.filter(patient_event=case).first()
            case.hospital_name = tr.hospital.name if tr and tr.hospital else '—'
        context['recent_cases'] = recent

    # Hospital Admin stats
    elif request.user.role == 'hospital_admin':
        from core.models import TransferRequest, Notification, HospitalStatus
        hospital = getattr(request.user, 'hospital', None)
        if hospital:
            context['hospital_name'] = hospital.name
            context['pending_transfers'] = TransferRequest.objects.filter(
                hospital=hospital, status='pending'
            ).count()
            context['unread_notifications'] = Notification.objects.filter(
                hospital=hospital, status='sent'
            ).count()

            status = HospitalStatus.objects.filter(hospital=hospital).order_by('-updated_at').first()
            if status:
                context['icu_info'] = f"{status.icu_available}/{status.icu_total}"
                context['bed_info'] = f"{status.bed_available}/{status.bed_total}"
    # Authority stats
    elif request.user.role == 'authority':
        from core.models import Hospital, PatientEvent, TransferRequest
        from django.utils import timezone
        today = timezone.now().date()

        context['total_hospitals'] = Hospital.objects.filter(is_active=True).count()
        context['total_active_cases'] = PatientEvent.objects.filter(
            status__in=['pending', 'referred']
        ).count()
        context['total_transfers'] = TransferRequest.objects.filter(
            created_at__date=today
        ).count()

    # System Admin stats
    elif request.user.role == 'admin':
        from core.models import Hospital, AuditLog
        from accounts.models import CustomUser

        context['total_users'] = CustomUser.objects.count()
        context['total_hospitals'] = Hospital.objects.count()
        context['total_logs'] = AuditLog.objects.count()

    # Patient stats
    elif request.user.role == 'patient':
        from core.models import Hospital
        context['total_hospitals'] = Hospital.objects.filter(is_active=True).count()

    return render(request, 'dashboard.html', context)