from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Super Admin"
        ADMIN_PAS = "ADMIN_PAS", "Admin PAS"
        VERIFIKATOR = "VERIFIKATOR", "Verifikator"
        PETUGAS_SCREENING = "PETUGAS_SCREENING", "Petugas Screening"
        PETUGAS_PEMBAYARAN = "PETUGAS_PEMBAYARAN", "Petugas Pembayaran"
        APPROVER = "APPROVER", "Approver"
        SECURITY = "SECURITY", "Security"
        MANAGEMENT = "MANAGEMENT", "Management"
        PEMOHON = "PEMOHON", "Pemohon"

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.PEMOHON)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.get_full_name() or self.username
