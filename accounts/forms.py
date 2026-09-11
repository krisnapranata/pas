from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username / Email"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )

class PemohonRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        # Pesan error dalam bahasa Indonesia (lebih jelas)
        self.fields["username"].error_messages = {
            "required": "Username wajib diisi.",
            "unique": "Username sudah terpakai. Silakan pilih username lain.",
            "invalid": "Username hanya boleh huruf, angka, dan @/./+/-/_.",
        }
        self.fields["email"].error_messages = {
            "required": "Email wajib diisi.",
            "invalid": "Format email tidak valid.",
        }
        self.fields["first_name"].error_messages = {
            "required": "Nama depan wajib diisi.",
        }
        self.fields["password1"].error_messages = {
            "required": "Password wajib diisi.",
        }
        self.fields["password2"].error_messages = {
            "required": "Ulangi password Anda.",
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email sudah terdaftar. Silakan gunakan email lain atau masuk.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PEMOHON
        if commit:
            user.save()
        return user


class ProfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "whatsapp",
            "nomor_identitas",
            "instansi",
            "alamat",
            "jabatan",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "whatsapp": forms.TextInput(attrs={"class": "form-control"}),
            "nomor_identitas": forms.TextInput(attrs={"class": "form-control"}),
            "instansi": forms.TextInput(attrs={"class": "form-control"}),
            "alamat": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "jabatan": forms.TextInput(attrs={"class": "form-control"}),
        }
