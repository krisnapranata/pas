from django.conf import settings
from django.db import models
from django.utils import timezone


class Layanan(models.Model):
    """Master Layanan (§8)."""

    class JenisTarif(models.TextChoices):
        FIXED = "FIXED", "Harga Tetap"
        PER_PENDAMPING = "PER_PENDAMPING", "Per Pendamping"
        PER_HARI = "PER_HARI", "Per Hari"
        PER_PENDAMPING_PER_HARI = "PER_PENDAMPING_PER_HARI", "Per Pendamping / Hari"
        BY_REQUEST = "BY_REQUEST", "By Request"

    kode_layanan = models.CharField(max_length=50, unique=True)
    nama_layanan = models.CharField(max_length=255)
    deskripsi = models.TextField(blank=True)
    minimal_pendamping = models.PositiveIntegerField(default=0)
    maksimal_pendamping = models.PositiveIntegerField(
        default=0, help_text="0 berarti tidak terbatas"
    )
    jenis_tarif = models.CharField(
        max_length=30, choices=JenisTarif.choices, default=JenisTarif.PER_PENDAMPING_PER_HARI
    )
    harga = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    satuan = models.CharField(max_length=50, blank=True)
    aktif = models.BooleanField(default=True)
    tanggal_mulai_berlaku = models.DateField(null=True, blank=True)
    tanggal_akhir_berlaku = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nama_layanan"]
        verbose_name = "Layanan"
        verbose_name_plural = "Layanan"

    def __str__(self):
        return self.nama_layanan

    def hitung_total(self, jumlah_pendamping, jumlah_hari=1):
        """Hitung total tarif berdasarkan jenis tarif (§7, §27)."""
        jumlah_pendamping = int(jumlah_pendamping or 0)
        if self.jenis_tarif == self.JenisTarif.FIXED:
            return self.harga
        if self.jenis_tarif == self.JenisTarif.PER_HARI:
            return self.harga * jumlah_hari
        if self.jenis_tarif == self.JenisTarif.BY_REQUEST:
            return 0
        # PER_PENDAMPING & PER_PENDAMPING_PER_HARI
        return self.harga * jumlah_pendamping


class Pengajuan(models.Model):
    """Pengajuan layanan oleh pemohon (§4, §5)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        DIAJUKAN = "DIAJUKAN", "Diajukan"
        VERIFIKASI_KOMERSIL = "VERIFIKASI_KOMERSIL", "Verifikasi Komersil"
        REVISI_PEMOHON = "REVISI_PEMOHON", "Revisi Pemohon"
        DISETUJUI_KOMERSIL = "DISETUJUI_KOMERSIL", "Disetujui Komersil"
        MENUNGGU_OPERASI = "MENUNGGU_OPERASI", "Menunggu Operasi"
        DITOLAK_OPERASI = "DITOLAK_OPERASI", "Ditolak Operasi"
        DISETUJUI_OPERASI = "DISETUJUI_OPERASI", "Disetujui Operasi"
        MENUNGGU_PEMBAYARAN = "MENUNGGU_PEMBAYARAN", "Menunggu Pembayaran"
        DIBAYAR = "DIBAYAR", "Sudah Dibayar"
        PAS_TERBIT = "PAS_TERBIT", "PAS Diterbitkan"
        SIAP_DILAKSANAKAN = "SIAP_DILAKSANAKAN", "Siap Dilaksanakan"
        DILAKSANAKAN = "DILAKSANAKAN", "Dilaksanakan"
        ACKNOWLEDGED_AOCH = "ACKNOWLEDGED_AOCH", "Acknowledged AOCH"
        SELESAI = "SELESAI", "Selesai"
        DIBATALKAN = "DIBATALKAN", "Dibatalkan"

    nomor_pengajuan = models.CharField(max_length=30, unique=True, blank=True)
    pemohon = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan",
    )
    # Snapshot identitas pemohon (wajib untuk pengajuan tanpa akun)
    pemohon_nama = models.CharField("Nama Pemohon", max_length=255, blank=True)
    pemohon_instansi = models.CharField(
        "Instansi/Perusahaan Pemohon", max_length=255, blank=True
    )
    pemohon_no_hp = models.CharField("No. HP Pemohon", max_length=20, blank=True)
    pemohon_email = models.EmailField("Email Pemohon", blank=True)
    layanan = models.ForeignKey(Layanan, on_delete=models.PROTECT, related_name="pengajuan")
    tanggal_pelaksanaan = models.DateField()
    waktu_kedatangan = models.TimeField(null=True, blank=True)
    nomor_penerbangan = models.CharField(max_length=50, blank=True)
    asal_penerbangan = models.CharField(max_length=100, blank=True)
    tujuan = models.CharField("Tujuan/Instansi", max_length=255, blank=True)
    jumlah_tamu = models.PositiveIntegerField(default=0)
    jumlah_pendamping = models.PositiveIntegerField(default=0)
    keterangan = models.TextField(blank=True)

    # Data PIC (Penanggung Jawab)
    pic_nama = models.CharField("Nama PIC", max_length=255, blank=True)
    pic_jabatan = models.CharField("Jabatan PIC", max_length=100, blank=True)
    pic_nomor_identitas = models.CharField("Nomor Identitas PIC", max_length=50, blank=True)
    pic_no_hp = models.CharField("No. HP PIC", max_length=20, blank=True)
    pic_email = models.EmailField("Email PIC", blank=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    catatan = models.TextField(blank=True)

    # Snapshot tarif (§10) — tidak berubah saat master tarif diubah
    harga_satuan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    jenis_tarif = models.CharField(max_length=30, blank=True)
    satuan = models.CharField(max_length=50, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pengajuan"
        verbose_name_plural = "Pengajuan"

    def __str__(self):
        return self.nomor_pengajuan or f"Pengajuan #{self.pk}"

    @property
    def nama_pemohon(self):
        if self.pemohon_id:
            return self.pemohon.nama_lengkap
        return self.pemohon_nama or "Pemohon"

    @property
    def instansi_pemohon(self):
        if self.pemohon_id:
            return self.pemohon.instansi
        return self.pemohon_instansi

    @property
    def kontak_pemohon(self):
        if self.pemohon_id:
            return self.pemohon.phone or self.pemohon.email
        return self.pemohon_no_hp or self.pemohon_email

    def _generate_nomor(self):
        now = timezone.now()
        prefix = f"REQ-{now:%Y%m%d}-"
        last = (
            Pengajuan.objects.filter(nomor_pengajuan__startswith=prefix)
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
        return f"{prefix}{seq:04d}"

    def simpan_snapshot_tarif(self):
        self.harga_satuan = self.layanan.harga
        self.jenis_tarif = self.layanan.jenis_tarif
        self.satuan = self.layanan.satuan
        self.total = self.layanan.hitung_total(self.jumlah_pendamping)
        return self.total


class DokumenPendamping(models.Model):
    """Dokumen identitas per pendamping (§5.C, jumlah mengikuti jumlah_pendamping)."""

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Diunggah"
        VALID = "VALID", "Valid"
        INVALID = "INVALID", "Tidak Valid"

    pengajuan = models.ForeignKey(Pengajuan, on_delete=models.CASCADE, related_name="pendamping")
    urutan = models.PositiveSmallIntegerField()
    nama = models.CharField("Nama Pendamping", max_length=255)
    file = models.FileField(upload_to="pengajuan/pendamping/")
    status_verifikasi = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendamping_verified",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["urutan"]
        verbose_name = "Dokumen Pendamping"
        verbose_name_plural = "Dokumen Pendamping"
        constraints = [
            models.UniqueConstraint(fields=["pengajuan", "urutan"], name="unique_pendamping_per_pengajuan")
        ]

    def __str__(self):
        return f"{self.pengajuan} - Pendamping {self.urutan} ({self.nama})"

    @property
    def is_image(self):
        name = (self.file.name or "").lower()
        return name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))


class StatusRiwayat(models.Model):
    pengajuan = models.ForeignKey(Pengajuan, on_delete=models.CASCADE, related_name="riwayat_status")
    status = models.CharField(max_length=30, choices=Pengajuan.Status.choices)
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


class DaftarHitam(models.Model):
    """Daftar hitam nama orang/perusahaan yang tidak boleh mendapatkan PAS."""

    class Tipe(models.TextChoices):
        ORANG = "ORANG", "Nama Orang"
        PERUSAHAAN = "PERUSAHAAN", "Nama Perusahaan"

    tipe = models.CharField(max_length=20, choices=Tipe.choices, default=Tipe.PERUSAHAAN)
    nama = models.CharField(max_length=255)
    alasan = models.TextField(blank=True)
    aktif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipe", "nama"]
        verbose_name = "Daftar Hitam"
        verbose_name_plural = "Daftar Hitam"

    def __str__(self):
        return f"[{self.get_tipe_display()}] {self.nama}"

    @classmethod
    def cocok(cls, nama):
        """Cek apakah nama cocok dengan entri aktif (exact, case-insensitive, trim)."""
        if not nama:
            return None
        return cls.objects.filter(aktif=True, nama__iexact=nama.strip()).first()
