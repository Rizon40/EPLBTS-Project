from django.db import models

# Create your models here.
# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    ROLE_CHOICES = [
        ('paramedic',   'Paramedic / Ambulance Operator'),
        ('hospital_admin', 'Hospital Administrator'),
        ('authority',   'Authority / Monitoring Officer'),
        ('admin',       'System Administrator'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='paramedic'
    )

    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # Helper properties for templates
    @property
    def is_paramedic(self):
        return self.role == 'paramedic'

    @property
    def is_hospital_admin(self):
        return self.role == 'hospital_admin'

    @property
    def is_authority(self):
        return self.role == 'authority'

    @property
    def is_system_admin(self):
        return self.role == 'admin'