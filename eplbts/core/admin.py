from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Hospital, HospitalStatus, PatientEvent, TransferRequest, Notification, AuditLog

admin.site.register(Hospital)
admin.site.register(HospitalStatus)
admin.site.register(PatientEvent)
admin.site.register(TransferRequest)
admin.site.register(Notification)
admin.site.register(AuditLog)