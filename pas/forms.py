from django import forms

from .models import Pengajuan


class PengajuanForm(forms.ModelForm):
    class Meta:
        model = Pengajuan
        fields = [
            "layanan",
            "tanggal_pelaksanaan",
            "waktu_kedatangan",
            "nomor_penerbangan",
            "asal_penerbangan",
            "tujuan",
            "jumlah_tamu",
            "jumlah_pendamping",
            "pemohon_nama",
            "pemohon_instansi",
            "pemohon_no_hp",
            "pemohon_email",
            "pic_nama",
            "pic_jabatan",
            "pic_nomor_identitas",
            "pic_no_hp",
            "pic_email",
            "keterangan",
        ]
        widgets = {
            "pemohon_nama": forms.TextInput(attrs={"class": "form-control"}),
            "pemohon_instansi": forms.TextInput(attrs={"class": "form-control"}),
            "pemohon_no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "pemohon_email": forms.EmailInput(attrs={"class": "form-control"}),
            "layanan": forms.Select(attrs={"class": "form-select"}),
            "tanggal_pelaksanaan": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "waktu_kedatangan": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "nomor_penerbangan": forms.TextInput(attrs={"class": "form-control"}),
            "asal_penerbangan": forms.TextInput(attrs={"class": "form-control"}),
            "tujuan": forms.TextInput(attrs={"class": "form-control"}),
            "jumlah_tamu": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "jumlah_pendamping": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "id": "id_jumlah_pendamping"}
            ),
            "pic_nama": forms.TextInput(attrs={"class": "form-control"}),
            "pic_jabatan": forms.TextInput(attrs={"class": "form-control"}),
            "pic_nomor_identitas": forms.TextInput(attrs={"class": "form-control"}),
            "pic_no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "pic_email": forms.EmailInput(attrs={"class": "form-control"}),
            "keterangan": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        if user is not None and user.is_authenticated:
            initial = kwargs.setdefault("initial", {})
            initial.setdefault("pemohon_nama", user.nama_lengkap)
            initial.setdefault("pemohon_instansi", user.instansi)
            initial.setdefault("pemohon_no_hp", user.phone)
            initial.setdefault("pemohon_email", user.email)
        super().__init__(*args, **kwargs)
        self.fields["layanan"].queryset = self.fields["layanan"].queryset.filter(aktif=True)
        self.fields["layanan"].empty_label = "-- Pilih Layanan --"
        self.fields["jumlah_pendamping"].initial = 0
        self.fields["jumlah_tamu"].initial = 0
        self.fields["pic_nama"].required = True
        self.fields["pic_no_hp"].required = True
        self.fields["pemohon_nama"].required = True
        self.fields["pemohon_no_hp"].required = True
        self.fields["pemohon_email"].required = True

    def clean(self):
        cleaned = super().clean()
        layanan = cleaned.get("layanan")
        jumlah_pendamping = cleaned.get("jumlah_pendamping") or 0
        if layanan:
            if jumlah_pendamping < layanan.minimal_pendamping:
                self.add_error(
                    "jumlah_pendamping",
                    f"Minimal pendamping untuk layanan ini adalah {layanan.minimal_pendamping}.",
                )
            if layanan.maksimal_pendamping and jumlah_pendamping > layanan.maksimal_pendamping:
                self.add_error(
                    "jumlah_pendamping",
                    f"Maksimal pendamping untuk layanan ini adalah {layanan.maksimal_pendamping}.",
                )
        return cleaned
