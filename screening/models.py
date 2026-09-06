from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils import timezone


class ScreeningSchedule(models.Model):
    """Jadwal screening dengan kuota (§11)."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Buka"
        FULL = "FULL", "Penuh"
        CLOSED = "CLOSED", "Tutup"
        CANCELLED = "CANCELLED", "Dibatalkan"

    tanggal = models.DateField()
    jam_mulai = models.TimeField()
    jam_selesai = models.TimeField()
    lokasi = models.CharField(max_length=255)
    kuota = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tanggal", "jam_mulai"]
        verbose_name = "Jadwal Screening"
        verbose_name_plural = "Jadwal Screening"

    def __str__(self):
        return f"{self.tanggal} {self.jam_mulai}-{self.jam_selesai} ({self.lokasi})"

    @property
    def terisi(self):
        return self.bookings.exclude(status__in=["CANCELLED", "NO_SHOW"]).count()

    @property
    def sisa(self):
        return max(self.kuota - self.terisi, 0)

    def refresh_status(self):
        if self.status == self.Status.CANCELLED:
            return
        self.status = self.Status.FULL if self.sisa <= 0 else self.Status.OPEN
        self.save(update_fields=["status"])


class ScreeningBooking(models.Model):
    """Booking screening oleh pemohon (§12)."""

    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Terbooking"
        CHECKED_IN = "CHECKED_IN", "Check-in"
        PROCESS = "PROCESS", "Proses"
        COMPLETED = "COMPLETED", "Selesai"
        NO_SHOW = "NO_SHOW", "Tidak Hadir"
        CANCELLED = "CANCELLED", "Dibatalkan"

    nomor_booking = models.CharField(max_length=30, unique=True, blank=True)
    pengajuan = models.ForeignKey(
        "pas.PengajuanPAS", on_delete=models.CASCADE, related_name="bookings"
    )
    jadwal = models.ForeignKey(
        ScreeningSchedule, on_delete=models.CASCADE, related_name="bookings"
    )
    nomor_antrian = models.PositiveIntegerField(default=0)
    waktu_booking = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED)

    class Meta:
        ordering = ["jadwal", "nomor_antrian"]
        verbose_name = "Booking Screening"
        verbose_name_plural = "Booking Screening"
        constraints = [
            models.UniqueConstraint(
                fields=["jadwal", "nomor_antrian"], name="unique_antrian_per_jadwal"
            )
        ]

    def __str__(self):
        return self.nomor_booking or f"Booking #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.nomor_antrian:
            last = (
                ScreeningBooking.objects.filter(jadwal=self.jadwal)
                .order_by("-nomor_antrian")
                .first()
            )
            self.nomor_antrian = (last.nomor_antrian + 1) if last else 1
        if self.pk and not self.nomor_booking:
            self.nomor_booking = self._generate_nomor()
        super().save(*args, **kwargs)

    def _generate_nomor(self):
        year = timezone.now().year
        prefix = f"SCR-{year}-"
        last = (
            ScreeningBooking.objects.filter(nomor_booking__startswith=prefix)
            .order_by("-nomor_booking")
            .first()
        )
        if last:
            try:
                seq = int(last.nomor_booking.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:06d}"


class ScreeningResult(models.Model):
    """Hasil screening oleh petugas (§13)."""

    class Hasil(models.TextChoices):
        PASSED = "PASSED", "Lulus"
        FAILED = "FAILED", "Tidak Lulus"

    booking = models.OneToOneField(
        ScreeningBooking, on_delete=models.CASCADE, related_name="hasil"
    )
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hasil_screening",
    )
    waktu_screening = models.DateTimeField(auto_now_add=True)
    hasil = models.CharField(max_length=10, choices=Hasil.choices)
    catatan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hasil Screening"
        verbose_name_plural = "Hasil Screening"

    def __str__(self):
        return f"{self.booking} - {self.hasil}"
