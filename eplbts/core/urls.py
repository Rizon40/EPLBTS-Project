from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', lambda request: redirect('dashboard'), name='home'),
    path('triage/submit/', views.submit_triage, name='submit_triage'),
    path('triage/success/<int:pk>/', views.triage_success, name='triage_success'),
    path('hospital/status/update/', views.update_hospital_status, name='update_hospital_status'),
    path('hospitals/', views.hospital_list, name='hospital_list'),
    path('sos/', views.sos_emergency, name='sos_emergency'),
    path('sos/success/<int:pk>/', views.sos_success, name='sos_success'),
]