"""Logic approval berjenjang & configurable (§15)."""

from django.utils import timezone

from pas.models import PengajuanPAS

from .models import Approval, ApprovalStep, ApprovalWorkflow


def get_workflow_for_pengajuan(pengajuan):
    """Ambil workflow sesuai jenis PAS, fallback ke default."""
    wf = ApprovalWorkflow.objects.filter(
        jenis_pas=pengajuan.jenis_pas, aktif=True
    ).first()
    if not wf:
        wf = ApprovalWorkflow.objects.filter(is_default=True, aktif=True).first()
    return wf


def initiate_approvals(pengajuan, user=None):
    """Buat instance Approval untuk tiap step aktif di workflow."""
    wf = get_workflow_for_pengajuan(pengajuan)
    if not wf:
        return []
    created = []
    for step in wf.steps.filter(aktif=True).order_by("level"):
        approval, _ = Approval.objects.get_or_create(
            pengajuan=pengajuan,
            level=step.level,
            defaults={"step": step, "role": step.role},
        )
        created.append(approval)
    return created


def submit_for_approval(pengajuan, user=None):
    """Pindahkan pengajuan ke WAITING_APPROVAL dan buat chain approval."""
    approvals = initiate_approvals(pengajuan, user)
    pengajuan.status = PengajuanPAS.Status.WAITING_APPROVAL
    pengajuan.save(update_fields=["status", "updated_at"])
    return approvals


def has_role(user, role):
    return user.is_authenticated and (user.is_staff or getattr(user, "role", "") == role)


def can_approve(user, approval):
    return has_role(user, approval.role)


def approve(approval, user, catatan=""):
    approval.status = Approval.Status.APPROVED
    approval.approver = user
    approval.catatan = catatan
    approval.approved_at = timezone.now()
    approval.save()
    _advance(approval.pengajuan, user)


def reject(approval, user, catatan=""):
    approval.status = Approval.Status.REJECTED
    approval.approver = user
    approval.catatan = catatan
    approval.approved_at = timezone.now()
    approval.save()
    pengajuan = approval.pengajuan
    pengajuan.status = PengajuanPAS.Status.REJECTED
    pengajuan.catatan = catatan or pengajuan.catatan
    pengajuan.save(update_fields=["status", "catatan", "updated_at"])
    # Tandai level lain yang masih pending sebagai tidak diproses (ditolak)
    pengajuan.approvals.filter(status=Approval.Status.PENDING).update(
        status=Approval.Status.REJECTED, approver=user, approved_at=timezone.now()
    )


def _advance(pengajuan, user):
    """Jika semua level disetujui, pengajuan -> APPROVED."""
    pending = pengajuan.approvals.filter(status=Approval.Status.PENDING).exists()
    rejected = pengajuan.approvals.filter(status=Approval.Status.REJECTED).exists()
    if rejected:
        return
    if not pending:
        pengajuan.status = PengajuanPAS.Status.APPROVED
        pengajuan.save(update_fields=["status", "updated_at"])


def current_level(pengajuan):
    """Level berikutnya yang masih pending."""
    return pengajuan.approvals.filter(status=Approval.Status.PENDING).order_by("level").first()
