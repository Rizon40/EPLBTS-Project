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
    path('cases/pending/',  views.pending_cases, name='pending_cases'),
    path('cases/<int:pk>/recommend/', views.recommend_hospitals,name='recommend_hospitals'),

    path('transfer/<int:event_pk>/<int:hospital_pk>/',views.create_transfer,name='create_transfer'),
    path('transfers/incoming/', views.incoming_transfers,name='incoming_transfers'),
    path('transfers/<int:pk>/<str:action>/',views.respond_transfer, name='respond_transfer'),

    path('notifications/', views.hospital_notifications, name='hospital_notifications'),
]