from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and CustomUser.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError('This phone number is already registered.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'patient'
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):

    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )