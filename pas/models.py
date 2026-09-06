from datetime import timedelta
from secrets import token_urlsafe

from django.conf import settings
from django.db import models
from django.utils import timezone


class JenisPAS(models.Model):
    nama = models.CharField(max_length=100)
    kode = models.CharField(max_length=30, unique=True)
    deskripsi = models.TextField(blank=True)
    masa_berlaku_hari = models.PositiveIntegerField(default=30, help_text="Masa berlaku dalam hari")
    biaya = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    butuh_screening = models.BooleanField(default=True)
    butuh_approval = models.BooleanField(default=True)
    status_aktif = models.BooleanField(default=True)
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["urutan", "nama"]
        verbose_name = "Jenis PAS"
        verbose_name_plural = "Jenis PAS"

    def __str__(self):
        return self.nama


class Persyaratan(models.Model):
    jenis_pas = models.ForeignKey(
        JenisPAS, on_delete=models.CASCADE, related_name="persyaratan"
    )
    nama = models.CharField(max_length=255)
    kode = models.CharField(max_length=50)
    deskripsi = models.TextField(blank=True)
    wajib = models.BooleanField(default=True)
    format_file = models.CharField(
        max_length=100, blank=True, help_text="Ekstensi yang diizinkan, pisahkan koma (jpg,png,pdf)"
    )
    max_size = models.PositiveIntegerField(
        default=2, help_text="Ukuran maksimal file (MB)"
    )
    aktif = models.BooleanField(default=True)
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["jenis_pas", "urutan"]
        verbose_name = "Persyaratan"
        verbose_name_plural = "Persyaratan"

    def __str__(self):
        return f"{self.jenis_pas.kode} - {self.nama}"


class PengajuanPAS(models.Model):
    """Pengajuan PAS oleh pemohon (§8)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Diajukan"
        DOCUMENT_REVIEW = "DOCUMENT_REVIEW", "Review Dokumen"
        REVISION_REQUIRED = "REVISION_REQUIRED", "Perlu Revisi"
        ADMIN_APPROVED = "ADMIN_APPROVED", "Disetujui Admin"
        WAITING_SCREENING = "WAITING_SCREENING", "Menunggu Screening"
        SCREENING_SCHEDULED = "SCREENING_SCHEDULED", "Screening Terjadwal"
        SCREENING_PROCESS = "SCREENING_PROCESS", "Proses Screening"
        SCREENING_PASSED = "SCREENING_PASSED", "Lulus Screening"
        SCREENING_FAILED = "SCREENING_FAILED", "Tidak Lulus Screening"
        WAITING_PAYMENT = "WAITING_PAYMENT", "Menunggu Pembayaran"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Pembayaran Pending"
        PAYMENT_PAID = "PAYMENT_PAID", "Pembayaran Lunas"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Pembayaran Gagal"
        WAITING_APPROVAL = "WAITING_APPROVAL", "Menunggu Approval"
        APPROVED = "APPROVED", "Disetujui"
        REJECTED = "REJECTED", "Ditolak"
        PAS_ISSUED = "PAS_ISSUED", "PAS Diterbitkan"
        EXPIRED = "EXPIRED", "Kedaluwarsa"
        CANCELLED = "CANCELLED", "Dibatalkan"

    nomor_pengajuan = models.CharField(max_length=30, unique=True, blank=True)
    pemohon = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pengajuan"
    )
    perusahaan = models.ForeignKey(
        "perusahaan.Perusahaan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan",
    )
    jenis_pas = models.ForeignKey(
        JenisPAS, on_delete=models.PROTECT, related_name="pengajuan"
    )
    tanggal_pengajuan = models.DateField(auto_now_add=True)
    tanggal_mulai = models.DateField(null=True, blank=True)
    tanggal_berakhir = models.DateField(null=True, blank=True)
    keperluan = models.TextField(blank=True)
    area_akses = models.ManyToManyField(
        "AreaAkses", blank=True, related_name="pengajuan"
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.DRAFT
    )
    catatan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pengajuan PAS"
        verbose_name_plural = "Pengajuan PAS"

    def __str__(self):
        return self.nomor_pengajuan or f"Pengajuan #{self.pk}"

    def save(self, *args, **kwargs):
        if self.pk and not self.nomor_pengajuan:
            self.nomor_pengajuan = self._generate_nomor()
        super().save(*args, **kwargs)

    def _generate_nomor(self):
        year = timezone.now().year
        prefix = f"PAS-{year}-"
        last = (
            PengajuanPAS.objects.filter(nomor_pengajuan__startswith=prefix)
            .order_by("-nomor_pengajuan")
            .first()
        )
        if last:
            try:
                seq = int(last.nomor_pengajuan.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:06d}"

    def hitung_tanggal_berakhir(self):
        if self.tanggal_mulai and self.jenis_pas:
            return self.tanggal_mulai + timedelta(days=self.jenis_pas.masa_berlaku_hari)
        return None


class DokumenPengajuan(models.Model):
    """Dokumen persyaratan yang diunggah pemohon (§10)."""

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Diunggah"
        VALID = "VALID", "Valid"
        INVALID = "INVALID", "Tidak Valid"
        REVISION_REQUIRED = "REVISION_REQUIRED", "Perlu Revisi"

    pengajuan = models.ForeignKey(
        PengajuanPAS, on_delete=models.CASCADE, related_name="dokumen"
    )
    persyaratan = models.ForeignKey(
        "Persyaratan", on_delete=models.CASCADE, related_name="dokumen"
    )
    file = models.FileField(upload_to="pengajuan/dokumen/")
    nomor_dokumen = models.CharField(max_length=100, blank=True)
    tanggal_upload = models.DateTimeField(auto_now_add=True)
    status_verifikasi = models.CharField(
        max_length=30, choices=Status.choices, default=Status.UPLOADED
    )
    catatan_verifikator = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dokumen_verified",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["persyaratan__urutan"]
        verbose_name = "Dokumen Pengajuan"
        verbose_name_plural = "Dokumen Pengajuan"

    def __str__(self):
        return f"{self.pengajuan} - {self.persyaratan.nama}"


class StatusRiwayat(models.Model):
    """Riwayat perubahan status pengajuan."""

    pengajuan = models.ForeignKey(
        PengajuanPAS, on_delete=models.CASCADE, related_name="riwayat_status"
    )
    status = models.CharField(max_length=30, choices=PengajuanPAS.Status.choices)
    catatan = models.TextField(blank=True)
    oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Riwayat Status"
        verbose_name_plural = "Riwayat Status"

    def __str__(self):
        return f"{self.pengajuan} -> {self.status}"


class AreaAkses(models.Model):
    nama = models.CharField(max_length=255)
    kode = models.CharField(max_length=50, unique=True)
    deskripsi = models.TextField(blank=True)
    status_aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nama"]
        verbose_name = "Area Akses"
        verbose_name_plural = "Area Akses"

    def __str__(self):
        return self.nama


class Tarif(models.Model):
    """Tarif tambahan / opsional selain biaya dasar JenisPAS."""

    nama = models.CharField(max_length=255)
    kode = models.CharField(max_length=50, unique=True)
    jenis_pas = models.ForeignKey(
        JenisPAS, on_delete=models.CASCADE, related_name="tarif", null=True, blank=True
    )
    nominal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    keterangan = models.TextField(blank=True)
    status_aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nama"]
        verbose_name = "Tarif"
        verbose_name_plural = "Tarif"

    def __str__(self):
        return self.nama


class PASCard(models.Model):
    """Kartu PAS terbit dengan QR token (§16)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktif"
        EXPIRED = "EXPIRED", "Kedaluwarsa"
        REVOKED = "REVOKED", "Dicabut"

    nomor_pas = models.CharField(max_length=30, unique=True, blank=True)
    pengajuan = models.OneToOneField(
        PengajuanPAS, on_delete=models.CASCADE, related_name="pas_card"
    )
    nomor_induk = models.CharField(max_length=100, blank=True)
    jenis_pas = models.ForeignKey(JenisPAS, on_delete=models.PROTECT, related_name="pas_cards")
    tanggal_terbit = models.DateField(auto_now_add=True)
    tanggal_berlaku = models.DateField(null=True, blank=True)
    tanggal_expired = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    qr_token = models.CharField(max_length=80, unique=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-tanggal_terbit"]
        verbose_name = "Kartu PAS"
        verbose_name_plural = "Kartu PAS"

    def __str__(self):
        return self.nomor_pas or f"PASCard #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.nomor_pas:
            self.nomor_pas = self._generate_nomor()
        if not self.qr_token:
            self.qr_token = token_urlsafe(40)
        super().save(*args, **kwargs)

    def _generate_nomor(self):
        year = timezone.now().year
        prefix = f"PAS-{year}-"
        last = (
            PASCard.objects.filter(nomor_pas__startswith=prefix)
            .order_by("-nomor_pas")
            .first()
        )
        seq = int(last.nomor_pas.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{seq:06d}"

    @property
    def is_valid(self):
        if self.status != self.Status.ACTIVE:
            return False
        if self.tanggal_expired and self.tanggal_expired < timezone.now().date():
            return False
        return True




