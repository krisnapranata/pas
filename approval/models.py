from django.conf import settings
from django.db import models

from pas.models import JenisPAS, PengajuanPAS


class ApprovalWorkflow(models.Model):
    """Workflow approval configurable (§15)."""

    nama = models.CharField(max_length=255)
    kode = models.CharField(max_length=50, unique=True)
    jenis_pas = models.ForeignKey(
        JenisPAS, on_delete=models.CASCADE, related_name="workflow_approval", null=True, blank=True
    )
    is_default = models.BooleanField(default=False)
    aktif = models.BooleanField(default=True)
    deskripsi = models.TextField(blank=True)

    class Meta:
        ordering = ["nama"]
        verbose_name = "Workflow Approval"
        verbose_name_plural = "Workflow Approval"

    def __str__(self):
        return self.nama


class ApprovalStep(models.Model):
    """Langkah/level approval dalam workflow."""

    workflow = models.ForeignKey(
        ApprovalWorkflow, on_delete=models.CASCADE, related_name="steps"
    )
    level = models.PositiveIntegerField(default=1)
    role = models.CharField(
        max_length=30,
        choices=[
            ("ADMIN_PAS", "Admin PAS"),
            ("VERIFIKATOR", "Verifikator"),
            ("SECURITY", "Security / AVSEC"),
            ("APPROVER", "Pejabat Berwenang"),
            ("MANAGEMENT", "Management"),
        ],
    )
    nama = models.CharField(max_length=255, blank=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["workflow", "level"]
        verbose_name = "Langkah Approval"
        verbose_name_plural = "Langkah Approval"

    def __str__(self):
        return f"{self.workflow.nama} L{self.level} - {self.get_role_display()}"


class Approval(models.Model):
    """Instance approval per pengajuan per level (§15)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Menunggu"
        APPROVED = "APPROVED", "Disetujui"
        REJECTED = "REJECTED", "Ditolak"

    pengajuan = models.ForeignKey(
        PengajuanPAS, on_delete=models.CASCADE, related_name="approvals"
    )
    step = models.ForeignKey(
        ApprovalStep, on_delete=models.PROTECT, related_name="approvals"
    )
    level = models.PositiveIntegerField(default=1)
    role = models.CharField(max_length=30)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approvals",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    catatan = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pengajuan", "level"]
        verbose_name = "Approval"
        verbose_name_plural = "Approval"

    def __str__(self):
        return f"{self.pengajuan.nomor_pengajuan} L{self.level} - {self.status}"
