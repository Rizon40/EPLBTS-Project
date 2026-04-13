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


@login_required
def dashboard_view(request):
    context = {'user': request.user}

    if request.user.role == 'paramedic':
        from core.models import PatientEvent
        context['pending_count'] = PatientEvent.objects.filter(status='pending').count()

    if request.user.role == 'hospital_admin' and request.user.hospital:
        from core.models import TransferRequest, Notification
        context['pending_transfers'] = TransferRequest.objects.filter(
            hospital=request.user.hospital, status='pending'
        ).count()
        context['unread_notifications'] = Notification.objects.filter(
            hospital=request.user.hospital
        ).count()

    return render(request, 'dashboard.html', context)