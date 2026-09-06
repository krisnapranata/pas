from django import forms

from .models import Perusahaan


class PerusahaanForm(forms.ModelForm):
    class Meta:
        model = Perusahaan
        fields = ["nama", "nib", "npwp", "alamat", "telepon", "email", "pic", "dokumen_legalitas"]
        widgets = {
            "nama": forms.TextInput(attrs={"class": "form-control"}),
            "nib": forms.TextInput(attrs={"class": "form-control"}),
            "npwp": forms.TextInput(attrs={"class": "form-control"}),
            "alamat": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "telepon": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "pic": forms.TextInput(attrs={"class": "form-control"}),
            "dokumen_legalitas": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nama"].required = True
        self.fields["nama"].error_messages = {"required": "Nama perusahaan wajib diisi."}
