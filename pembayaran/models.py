from django.conf import settings
from django.db import models
from django.utils import timezone

from pas.models import PengajuanPAS


class PaymentMethod(models.Model):
    """Master data metode pembayaran, tidak hard-code (§14.11)."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=30,
        choices=[
            ("QRIS", "QRIS"),
            ("VIRTUAL_ACCOUNT", "Virtual Account"),
            ("BANK_TRANSFER", "Transfer Bank"),
            ("E_WALLET", "E-Wallet"),
            ("CARD", "Kartu"),
            ("OTC", "Convenience Store / OTC"),
            ("MANUAL_TRANSFER", "Transfer Manual"),
            ("CASH", "Tunai"),
            ("OTHER", "Lainnya"),
        ],
    )
    provider = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "code"]
        verbose_name = "Metode Pembayaran"
        verbose_name_plural = "Metode Pembayaran"

    def __str__(self):
        return self.name


class Invoice(models.Model):
    """Invoice pembayaran PAS (§14.3)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        UNPAID = "UNPAID", "Belum Dibayar"
        PENDING = "PENDING", "Menunggu"
        PAID = "PAID", "Lunas"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Dibayar Sebagian"
        EXPIRED = "EXPIRED", "Kedaluwarsa"
        CANCELLED = "CANCELLED", "Dibatalkan"
        REFUNDED = "REFUNDED", "Direfund"

    nomor_invoice = models.CharField(max_length=30, unique=True, blank=True)
    pengajuan = models.OneToOneField(
        PengajuanPAS, on_delete=models.CASCADE, related_name="invoice"
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    biaya_admin = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="IDR")
    tanggal_terbit = models.DateTimeField(auto_now_add=True)
    tanggal_jatuh_tempo = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoice"

    def __str__(self):
        return self.nomor_invoice or f"Invoice #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.nomor_invoice and self.pk:
            self.nomor_invoice = self._generate_nomor()
        if not self.tanggal_jatuh_tempo:
            self.tanggal_jatuh_tempo = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def _generate_nomor(self):
        year = timezone.now().year
        prefix = f"INV-{year}-"
        last = (
            Invoice.objects.filter(nomor_invoice__startswith=prefix)
            .order_by("-nomor_invoice")
            .first()
        )
        seq = int(last.nomor_invoice.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{seq:06d}"

    def hitung_total(self):
        self.total = self.subtotal + self.biaya_admin + self.tax - self.discount
        return self.total


class PaymentTransaction(models.Model):
    """Transaksi pembayaran per attempt (§14.4)."""

    class Status(models.TextChoices):
        CREATED = "CREATED", "Dibuat"
        PENDING = "PENDING", "Menunggu"
        PAID = "PAID", "Lunas"
        FAILED = "FAILED", "Gagal"
        EXPIRED = "EXPIRED", "Kedaluwarsa"
        CANCELLED = "CANCELLED", "Dibatalkan"
        REFUNDED = "REFUNDED", "Direfund"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Refund Sebagian"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="transaksi")
    provider = models.CharField(max_length=100, blank=True)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="transaksi"
    )
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    merchant_reference = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="IDR")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.CREATED)
    payment_url = models.URLField(blank=True)
    qr_string = models.TextField(blank=True)
    va_number = models.CharField(max_length=100, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaksi Pembayaran"
        verbose_name_plural = "Transaksi Pembayaran"

    def __str__(self):
        return f"{self.merchant_reference or self.pk} ({self.status})"


class WebhookLog(models.Model):
    """Log webhook masuk, idempotent & audit (§14.5)."""

    webhook_event_id = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=100, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    signature = models.TextField(blank=True)
    transaction = models.ForeignKey(
        PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="webhook_logs"
    )
    processing_status = models.CharField(
        max_length=30,
        default="RECEIVED",
        choices=[
            ("RECEIVED", "Diterima"),
            ("PROCESSED", "Diproses"),
            ("DUPLICATE", "Duplikat"),
            ("FAILED", "Gagal"),
        ],
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Log Webhook"
        verbose_name_plural = "Log Webhook"

    def __str__(self):
        return f"{self.provider} - {self.webhook_event_id or self.pk}"


class Refund(models.Model):
    """Refund dengan approval & audit trail (§14.9)."""

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Diminta"
        APPROVED = "APPROVED", "Disetujui"
        PROCESSED = "PROCESSED", "Diproses"
        REFUNDED = "REFUNDED", "Direfund"
        REJECTED = "REJECTED", "Ditolak"

    transaksi = models.ForeignKey(
        PaymentTransaction, on_delete=models.CASCADE, related_name="refunds"
    )
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="refunds_requested"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="refunds_approved"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    provider_refund_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Refund"
        verbose_name_plural = "Refund"

    def __str__(self):
        return f"Refund {self.refund_amount} - {self.status}"


class PembayaranManual(models.Model):
    """Bukti pembayaran manual (transfer/tunai) untuk verifikasi petugas (§14.1)."""

    transaksi = models.OneToOneField(
        PaymentTransaction, on_delete=models.CASCADE, related_name="manual"
    )
    bukti = models.FileField(upload_to="pembayaran/bukti/")
    catatan = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pembayaran_verified"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pembayaran Manual"
        verbose_name_plural = "Pembayaran Manual"

    def __str__(self):
        return f"Manual - {self.transaksi}"
