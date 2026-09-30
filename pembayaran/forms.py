from django import forms

from .models import PaymentMethod


class PaymentMethodForm(forms.ModelForm):
    """Form jenis pembayaran — konfigurasi rekening diisi terpisah."""

    bank = forms.CharField(
        label="Nama Bank",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "BCA"}),
    )
    norek = forms.CharField(
        label="Nomor Rekening",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1234567890"}),
    )
    nama = forms.CharField(
        label="Atas Nama",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "PT Bandara Layanan"}),
    )

    class Meta:
        model = PaymentMethod
        fields = ("code", "name", "type", "provider", "sort_order", "active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("code", "name", "type", "provider", "sort_order", "active"):
            if name == "active":
                self.fields[name].widget.attrs.setdefault("class", "form-check-input")
            elif name == "sort_order":
                self.fields[name].widget.attrs.setdefault("class", "form-control")
            elif name == "type":
                self.fields[name].widget.attrs.setdefault("class", "form-select")
            else:
                self.fields[name].widget.attrs.setdefault("class", "form-control")
        self.fields["code"].error_messages = {
            "required": "Kode wajib diisi.",
            "unique": "Kode jenis pembayaran sudah terpakai.",
        }
        self.fields["name"].error_messages = {"required": "Nama wajib diisi."}
        if self.instance and self.instance.pk:
            konfig = self.instance.configuration or {}
            self.fields["bank"].initial = konfig.get("bank", "")
            self.fields["norek"].initial = konfig.get("norek", "")
            self.fields["nama"].initial = konfig.get("nama", "")

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        return code

    def save(self, commit=True):
        obj = super().save(commit=False)
        konfig = dict(obj.configuration or {})
        for key in ("bank", "norek", "nama"):
            nilai = (self.cleaned_data.get(key) or "").strip()
            if nilai:
                konfig[key] = nilai
            else:
                konfig.pop(key, None)
        obj.configuration = konfig
        if commit:
            obj.save()
        return obj
