from django.conf import settings
from django.db import models


class Perusahaan(models.Model):
    nama = models.CharField(max_length=255)
    nib = models.CharField("NIB", max_length=50, blank=True)
    npwp = models.CharField("NPWP", max_length=50, blank=True)
    alamat = models.TextField(blank=True)
    telepon = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    pic = models.CharField("PIC / Penanggung Jawab", max_length=255, blank=True)
    dokumen_legalitas = models.FileField(
        upload_to="perusahaan/legalitas/", blank=True, null=True
    )
    status_aktif = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perusahaan_dibuat",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nama"]
        verbose_name = "Perusahaan"
        verbose_name_plural = "Perusahaan"

    def __str__(self):
        return self.nama


class Pemohon(models.Model):
    """Profil pemohon terkait data pribadi (§6)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pemohon"
    )
    nik = models.CharField("NIK", max_length=20, blank=True)
    nama_lengkap = models.CharField(max_length=255, blank=True)
    tempat_lahir = models.CharField(max_length=100, blank=True)
    tanggal_lahir = models.DateField(null=True, blank=True)
    JENIS_KELAMIN = (
        ("L", "Laki-laki"),
        ("P", "Perempuan"),
    )
    jenis_kelamin = models.CharField(max_length=1, choices=JENIS_KELAMIN, blank=True)
    alamat = models.TextField(blank=True)
    nomor_hp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    jabatan = models.CharField(max_length=100, blank=True)
    perusahaan = models.ForeignKey(
        Perusahaan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pemohon",
    )
    foto = models.ImageField(upload_to="pemohon/foto/", blank=True, null=True)
    status_aktif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nama_lengkap"]
        verbose_name = "Pemohon"
        verbose_name_plural = "Pemohon"

    def __str__(self):
        return self.nama_lengkap or self.user.username
