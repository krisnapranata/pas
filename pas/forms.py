from django import forms
from django.utils import timezone

from .models import DaftarHitam, Layanan, Pengajuan
from .services import normalisasi_nik


class PengajuanForm(forms.ModelForm):
    class Meta:
        model = Pengajuan
        fields = [
            "layanan",
            "tanggal_pelaksanaan",
            "waktu_kedatangan",
            "nomor_penerbangan",
            "asal_penerbangan",
            "jumlah_tamu",
            "jumlah_pendamping",
            "pic_nama",
            "pic_jabatan",
            "pic_nomor_identitas",
            "pic_no_hp",
            "pic_email",
            "keterangan",
        ]
        widgets = {
            "layanan": forms.RadioSelect(attrs={"class": "layanan-radio"}),
            "tanggal_pelaksanaan": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "waktu_kedatangan": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "nomor_penerbangan": forms.TextInput(attrs={"class": "form-control"}),
            "asal_penerbangan": forms.TextInput(attrs={"class": "form-control"}),
            "jumlah_tamu": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "jumlah_pendamping": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "id": "id_jumlah_pendamping"}
            ),
            "pic_nama": forms.TextInput(attrs={"class": "form-control"}),
            "pic_jabatan": forms.TextInput(attrs={"class": "form-control"}),
            "pic_nomor_identitas": forms.TextInput(
                attrs={"class": "form-control", "inputmode": "numeric"}
            ),
            "pic_no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "pic_email": forms.EmailInput(attrs={"class": "form-control"}),
            "keterangan": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["layanan"].queryset = self.fields["layanan"].queryset.filter(
            aktif=True
        )
        self.fields["layanan"].empty_label = None
        self.fields["layanan"].label = "Pilih Layanan"
        self.fields["jumlah_pendamping"].initial = 0
        self.fields["jumlah_tamu"].initial = 0
        self.fields["pic_nama"].required = True
        self.fields["pic_no_hp"].required = True
        self.fields["tanggal_pelaksanaan"].widget.attrs["min"] = timezone.localdate().isoformat()
        self.fields["pic_email"].required = False
        # PIC penanggung jawab adalah pengganti "Data Pemohon" lama
        if user is not None and user.is_authenticated and not self.is_bound:
            self.initial.setdefault("pic_nomor_identitas", user.nomor_identitas)

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


class LayananForm(forms.ModelForm):
    class Meta:
        model = Layanan
        fields = [
            "kode_layanan",
            "nama_layanan",
            "lokasi",
            "deskripsi",
            "minimal_pendamping",
            "maksimal_pendamping",
            "jenis_tarif",
            "harga",
            "satuan",
            "aktif",
        ]
        widgets = {
            "kode_layanan": forms.TextInput(attrs={"class": "form-control"}),
            "nama_layanan": forms.TextInput(attrs={"class": "form-control"}),
            "lokasi": forms.Select(attrs={"class": "form-select"}),
            "deskripsi": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "minimal_pendamping": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "maksimal_pendamping": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "jenis_tarif": forms.Select(attrs={"class": "form-select"}),
            "harga": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": "0.01"}
            ),
            "satuan": forms.TextInput(attrs={"class": "form-control"}),
            "aktif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class DaftarHitamForm(forms.ModelForm):
    class Meta:
        model = DaftarHitam
        fields = ["tipe", "nik", "nama", "alasan", "aktif"]
        widgets = {
            "tipe": forms.Select(attrs={"class": "form-select"}),
            "nik": forms.TextInput(
                attrs={"class": "form-control", "inputmode": "numeric", "maxlength": 50}
            ),
            "nama": forms.TextInput(attrs={"class": "form-control"}),
            "alasan": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "aktif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_nik(self):
        nik = normalisasi_nik(self.cleaned_data.get("nik"))
        if nik and len(nik) < 5:
            raise forms.ValidationError("NIK tidak valid (minimal 5 digit).")
        return nik
