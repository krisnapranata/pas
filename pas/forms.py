from django import forms
from django.core.validators import FileExtensionValidator

from .models import DokumenPengajuan, PengajuanPAS


class PengajuanForm(forms.ModelForm):
    class Meta:
        model = PengajuanPAS
        fields = ["perusahaan", "jenis_pas", "tanggal_mulai", "keperluan", "area_akses"]
        widgets = {
            "tanggal_mulai": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "keperluan": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "perusahaan": forms.Select(attrs={"class": "form-select"}),
            "jenis_pas": forms.Select(attrs={"class": "form-select"}),
            "area_akses": forms.SelectMultiple(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jenis_pas"].queryset = self.fields["jenis_pas"].queryset.filter(
            status_aktif=True
        )
        self.fields["area_akses"].queryset = self.fields["area_akses"].queryset.filter(
            status_aktif=True
        )


class DokumenUploadForm(forms.ModelForm):
    class Meta:
        model = DokumenPengajuan
        fields = ["file", "nomor_dokumen"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "nomor_dokumen": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, persyaratan=None, **kwargs):
        super().__init__(*args, **kwargs)
        if persyaratan:
            allowed = [
                e.strip().lower()
                for e in persyaratan.format_file.split(",")
                if e.strip()
            ]
            if allowed:
                self.fields["file"].validators = [FileExtensionValidator(allowed)]
