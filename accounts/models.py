from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMINISTRATOR = "ADMINISTRATOR", "Administrator"
        KOMERSIL = "KOMERSIL", "Komersil"
        OPERASI = "OPERASI", "Operasi"
        AOCH = "AOCH", "AOCH"
        PEMOHON = "PEMOHON", "Pemohon"

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.PEMOHON)
    phone = models.CharField("Nomor HP", max_length=20, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=20, blank=True)
    nomor_identitas = models.CharField("Nomor Identitas", max_length=50, blank=True)
    instansi = models.CharField("Instansi/Perusahaan", max_length=255, blank=True)
    alamat = models.TextField(blank=True)
    jabatan = models.CharField(max_length=100, blank=True)
    email_verified = models.BooleanField(default=False)

    @property
    def nama_lengkap(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.nama_lengkap

    def is_role(self, *roles):
        return self.role in roles or (self.is_staff and "ADMINISTRATOR" in roles)
