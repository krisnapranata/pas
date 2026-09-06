from django import forms

from .models import ScreeningSchedule


class ScreeningScheduleForm(forms.ModelForm):
    class Meta:
        model = ScreeningSchedule
        fields = ["tanggal", "jam_mulai", "jam_selesai", "lokasi", "kuota"]
        widgets = {
            "tanggal": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "jam_mulai": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "jam_selesai": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "lokasi": forms.TextInput(attrs={"class": "form-control"}),
            "kuota": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }
