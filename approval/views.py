from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from audit.models import log_action
from pas.models import PengajuanPAS

from .models import Approval, ApprovalWorkflow
from .services import (
    approve,
    can_approve,
    current_level,
    has_role,
    reject,
    get_workflow_for_pengajuan,
    initiate_approvals,
    submit_for_approval,
)


def _is_approver(user):
    return user.is_authenticated and (
        user.is_staff
        or getattr(user, "role", "") in ("APPROVER", "ADMIN_PAS", "VERIFIKATOR", "SECURITY", "MANAGEMENT")
    )


@login_required
def approval_list(request):
    """Daftar pengajuan menunggu/waktu approval."""
    pengajuan_qs = PengajuanPAS.objects.filter(
        status__in=[
            "WAITING_APPROVAL",
            "APPROVED",
            "REJECTED",
        ]
    )
    if not _is_approver(request.user):
        pengajuan_qs = pengajuan_qs.filter(pemohon=request.user)
    workflows = ApprovalWorkflow.objects.filter(aktif=True)
    return render(
        request,
        "approval/approval_list.html",
        {"pengajuan": pengajuan_qs.select_related("jenis_pas", "pemohon"), "workflows": workflows},
    )


@login_required
def detail_approval(request, pk):
    pengajuan = get_object_or_404(
        PengajuanPAS.objects.select_related("jenis_pas", "pemohon", "perusahaan"), pk=pk
    )
    approvals = pengajuan.approvals.select_related("step", "approver").order_by("level")
    return render(
        request,
        "approval/detail_approval.html",
        {"pengajuan": pengajuan, "approvals": approvals},
    )


@user_passes_test(_is_approver)
def kirim_approval(request, pk):
    """Kirim pengajuan (sudah PAID) ke proses approval."""
    pengajuan = get_object_or_404(PengajuanPAS, pk=pk)
    if pengajuan.status not in ("PAYMENT_PAID", "WAITING_APPROVAL"):
        messages.error(request, "Pengajuan belum lunas atau tidak valid untuk approval.")
        return redirect("approval:approval_list")
    if not pengajuan.approvals.exists():
        submit_for_approval(pengajuan, request.user)
        log_action(request, "KIRIM_APPROVAL", "PengajuanPAS", pengajuan.pk)
    messages.success(request, "Pengajuan dikirim ke proses approval.")
    return redirect("approval:detail_approval", pk=pk)


@user_passes_test(_is_approver)
def proses_approval(request, approval_id):
    approval = get_object_or_404(
        Approval.objects.select_related("pengajuan__pemohon", "step"), pk=approval_id
    )
    if approval.status != Approval.Status.PENDING:
        messages.warning(request, "Approval level ini sudah diproses.")
        return redirect("approval:detail_approval", pk=approval.pengajuan.pk)
    if not can_approve(request.user, approval):
        messages.error(request, f"Anda tidak punya akses approve level {approval.role}.")
        return redirect("approval:detail_approval", pk=approval.pengajuan.pk)
    if request.method == "POST":
        aksi = request.POST.get("aksi")
        catatan = request.POST.get("catatan", "")
        if aksi == "APPROVE":
            approve(approval, request.user, catatan)
            log_action(request, "APPROVE", "Approval", approval.pk, new_value=catatan)
            pengajuan = approval.pengajuan
            pengajuan.refresh_from_db()
            if pengajuan.status == PengajuanPAS.Status.APPROVED:
                messages.success(request, "Approval lengkap. Pengajuan disetujui.")
            else:
                messages.success(request, f"Level {approval.level} disetujui.")
        elif aksi == "REJECT":
            reject(approval, request.user, catatan)
            log_action(request, "REJECT", "Approval", approval.pk, new_value=catatan)
            messages.warning(request, "Pengajuan ditolak.")
        return redirect("approval:detail_approval", pk=approval.pengajuan.pk)
    return render(request, "approval/proses_approval.html", {"approval": approval})
