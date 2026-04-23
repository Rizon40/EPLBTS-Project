from django import forms
from .models import PatientEvent, HospitalStatus, Hospital


# 1. Paramedic Triage Form
class TriageForm(forms.ModelForm):
    class Meta:
        model = PatientEvent
        fields = [
            'case_type', 'triage_level', 'description',
            'patient_age', 'patient_gender',
            'location_text', 'latitude', 'longitude',
            'needs_icu', 'needs_ventilator',
            'needs_blood_bank', 'needs_cath_lab',
        ]
        widgets = {
            'triage_level': forms.Select(attrs={'class': 'form-select'}),
            'case_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'patient_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'patient_gender': forms.Select(attrs={'class': 'form-select'}),
            'location_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dhanmondi, Dhaka'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'needs_icu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_ventilator': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_blood_bank': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_cath_lab': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['triage_level'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False

# 2. Hospital Status Update Form
class HospitalStatusForm(forms.ModelForm):
    class Meta:
        model = HospitalStatus
        fields = [
            'icu_total', 'icu_available',
            'bed_total', 'bed_available',
            'has_ventilator', 'has_blood_bank', 'has_cath_lab',
            'is_accepting',
        ]
        widgets = {
            'icu_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'icu_available': forms.NumberInput(attrs={'class': 'form-control'}),
            'bed_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'bed_available': forms.NumberInput(attrs={'class': 'form-control'}),
            'has_ventilator': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_blood_bank': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_cath_lab': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_accepting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# 3. Patient SOS Emergency Form (Without Login)
class SOSForm(forms.ModelForm):
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 01712345678'
        }),
        label='Contact Phone Number'
    )

    location_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Your Location'
        }),
        label='Your Location (Optional)'
    )

    class Meta:
        model = PatientEvent
        fields = [
            'case_type', 'description',
            'patient_age', 'patient_gender',
            'location_text',
        ]
        widgets = {
            'case_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Briefly describe the emergency'}),
            'patient_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'patient_gender': forms.Select(attrs={'class': 'form-select'}),
        }