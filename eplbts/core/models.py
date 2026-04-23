from django.db import models
from django.conf import settings


# 1. Hospital
class Hospital(models.Model):
    SPECIALTY_CHOICES = [
        ('general', 'General'),
        ('cardiac', 'Cardiac'),
        ('trauma', 'Trauma'),
        ('neurology', 'Neurology'),
        ('pediatric', 'Pediatric'),
    ]

    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone_number = models.CharField(max_length=15)
    specialty = models.CharField(
        max_length=50,
        choices=SPECIALTY_CHOICES,
        default='general'
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# 2. HospitalStatus (Real-time capacity)
class HospitalStatus(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='statuses'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    icu_total = models.PositiveIntegerField(default=0)
    icu_available = models.PositiveIntegerField(default=0)

    bed_total = models.PositiveIntegerField(default=0)
    bed_available = models.PositiveIntegerField(default=0)

    has_ventilator = models.BooleanField(default=False)
    has_blood_bank = models.BooleanField(default=False)
    has_cath_lab = models.BooleanField(default=False)  # cardiac lab

    is_accepting = models.BooleanField(default=True)  # accepting patients?

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.hospital.name} - Updated: {self.updated_at:%Y-%m-%d %H:%M}"

    @property
    def icu_load_percent(self):
        if self.icu_total == 0:
            return 100
        return round(((self.icu_total - self.icu_available) / self.icu_total) * 100)

    @property
    def bed_load_percent(self):
        if self.bed_total == 0:
            return 100
        return round(((self.bed_total - self.bed_available) / self.bed_total) * 100)


# 3. PatientEvent (Emergency triage case)
class PatientEvent(models.Model):
    CASE_TYPE_CHOICES = [
        ('accident', 'Road Accident'),
        ('heart_attack', 'Heart Attack / Cardiac'),
        ('stroke', 'Stroke / Neurological'),
        ('burn', 'Burns'),
        ('fracture', 'Fracture / Trauma'),
        ('pediatric', 'Pediatric Emergency'),
        ('respiratory', 'Respiratory Distress'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('referred', 'Referred'),
        ('transferred', 'Transferred'),
        ('completed', 'Completed'),
    ]

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='patient_events'
    )

    case_type = models.CharField(max_length=20, choices=CASE_TYPE_CHOICES)

    TRIAGE_CHOICES = [
        ('critical', 'Critical'),
        ('urgent', 'Urgent'),
        ('stable', 'Stable'),
    ]
    triage_level = models.CharField(
        max_length=10,
        choices=TRIAGE_CHOICES,
        default='urgent'
    )

    description = models.TextField(blank=True)

    # Patient info (minimal — no full PII)
    patient_age = models.PositiveIntegerField()
    patient_gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    )

    # Location of emergency
    location_text = models.CharField(max_length=300)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # Requirements
    needs_icu = models.BooleanField(default=False)
    needs_ventilator = models.BooleanField(default=False)
    needs_blood_bank = models.BooleanField(default=False)
    needs_cath_lab = models.BooleanField(default=False)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Case #{self.id} — {self.get_case_type_display()} ({self.status})"


# 4. TransferRequest
class TransferRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('overridden', 'Overridden'),
    ]

    patient_event = models.OneToOneField(
        PatientEvent,
        on_delete=models.CASCADE,
        related_name='transfer_request'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='transfer_requests'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )
    is_overridden = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transfer #{self.id} → {self.hospital.name} ({self.status})"

# 5. Notification
class Notification(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    transfer_request = models.ForeignKey(
        TransferRequest,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    message = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification → {self.hospital.name} [{self.status}]"

# 6. AuditLog
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('triage_submitted', 'Triage Submitted'),
        ('recommendation_viewed', 'Recommendation Viewed'),
        ('transfer_accepted', 'Transfer Accepted'),
        ('transfer_rejected', 'Transfer Rejected'),
        ('override_performed', 'Override Performed'),
        ('status_updated', 'Hospital Status Updated'),
        ('notification_sent', 'Notification Sent'),
    ]

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    patient_event = models.ForeignKey(
        PatientEvent,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs'
    )
    transfer_request = models.ForeignKey(
        TransferRequest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs'
    )

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.get_action_display()} by {self.performed_by}"