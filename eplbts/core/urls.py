from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', lambda request: redirect('dashboard'), name='home'),

    # Paramedic
    path('triage/submit/',  views.submit_triage, name='submit_triage'),
    path('triage/success/<int:pk>/', views.triage_success, name='triage_success'),

    # Hospital Admin
    path('hospital/status/update/', views.update_hospital_status, name='update_hospital_status'),

    # Hospital List
    path('hospitals/', views.hospital_list, name='hospital_list'),

    # Patient SOS
    path('sos/', views.sos_emergency, name='sos_emergency'),
    path('sos/success/<int:pk>/', views.sos_success, name='sos_success'),

    # Pending Cases
    path('cases/pending/', views.pending_cases, name='pending_cases'),

    # Recommendations
    path('cases/<int:pk>/recommend/', views.recommend_hospitals, name='recommend_hospitals'),

    # Transfer Request
    path('transfer/<int:event_pk>/<int:hospital_pk>/', views.create_transfer, name='create_transfer'),

    # Hospital Admin — Transfers
    path('transfers/incoming/', views.incoming_transfers, name='incoming_transfers'),
    path('transfers/<int:pk>/<str:action>/',views.respond_transfer, name='respond_transfer'),

    # Notifications
    path('notifications/', views.hospital_notifications, name='hospital_notifications'),
]