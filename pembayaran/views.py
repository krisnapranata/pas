import base64
import io
import json
import logging

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from audit.models import log_action
from notifikasi.services import notify_role
from pas.models import Pengajuan

from .models import (
    Invoice,
    PaymentMethod,
    PaymentTransaction,
    PembayaranManual,
    Refund,
    WebhookLog,
)
from .services import PaymentService

logger = logging.getLogger(__name__)


def _is_petugas_pembayaran(user):
    return user.is_authenticated and (
        user.is_staff or getattr(user, "role", "") in ("ADMINISTRATOR", "KOMERSIL")
    )


def get_or_create_invoice(pengajuan):
    """Buat invoice dari snapshot total pengajuan jika belum ada."""
    invoice, created = Invoice.objects.get_or_create(pengajuan=pengajuan)
    if created:
        invoice.subtotal = pengajuan.total
        invoice.biaya_admin = 0
        invoice.discount = 0
        invoice.tax = 0
        invoice.hitung_total()
        invoice.status = Invoice.Status.UNPAID
        invoice.nomor_invoice = invoice._generate_nomor()
        invoice.save()
    return invoice


@login_required
def invoice_saya(request):
    invoices = Invoice.objects.filter(pengajuan__pemohon=request.user).select_related("pengajuan__layanan")
    return render(request, "pembayaran/invoice_saya.html", {"invoices": invoices})


@login_required
def buat_invoice(request, pengajuan_id):
    pengajuan = get_object_or_404(Pengajuan, pk=pengajuan_id, pemohon=request.user)
    # Hanya bisa buat invoice setelah Operasi menyetujui (link pembayaran aktif)
    if pengajuan.status != Pengajuan.Status.MENUNGGU_PEMBAYARAN:
        messages.error(request, "Link pembayaran belum aktif (menunggu persetujuan Operasi).")
        return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
    invoice = get_or_create_invoice(pengajuan)
    log_action(request, "BUAT_INVOICE", "Invoice", invoice.pk)
    return redirect("pembayaran:bayar", invoice_id=invoice.pk)


@login_required
def bayar(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id, pengajuan__pemohon=request.user)
    methods = PaymentMethod.objects.filter(active=True)
    return render(request, "pembayaran/bayar.html", {"invoice": invoice, "methods": methods})


@login_required
@require_POST
def buat_transaksi(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id, pengajuan__pemohon=request.user)
    method_id = request.POST.get("method")
    method = get_object_or_404(PaymentMethod, pk=method_id, active=True)

    if invoice.status == Invoice.Status.PAID:
        messages.info(request, "Invoice sudah lunas.")
        return redirect("pembayaran:invoice_saya")

    # expired invoice -> batalkan & minta ulang (jangan gandakan invoice)
    if invoice.status == Invoice.Status.EXPIRED:
        invoice.status = Invoice.Status.UNPAID
        invoice.tanggal_jatuh_tempo = timezone.now() + timezone.timedelta(hours=24)
        invoice.save()

    # Sudah ada bukti diunggah & menunggu verifikasi -> jangan buat transaksi baru
    existing = (
        PaymentTransaction.objects.filter(
            invoice=invoice,
            status=PaymentTransaction.Status.PENDING,
            manual__isnull=False,
        )
        .order_by("-created_at")
        .first()
    )
    if existing:
        messages.info(request, "Bukti pembayaran sudah diunggah dan menunggu verifikasi petugas.")
        return redirect("pembayaran:detail_transaksi", pk=existing.pk)

    # Nonaktifkan transaksi lama yang masih menunggu
    PaymentTransaction.objects.filter(
        invoice=invoice, status__in=["CREATED", "PENDING"]
    ).update(status=PaymentTransaction.Status.CANCELLED)

    transaksi = PaymentTransaction.objects.create(
        invoice=invoice,
        provider=method.provider,
        payment_method=method,
        amount=invoice.total,
        currency=invoice.currency,
        merchant_reference=f"{invoice.nomor_invoice}-{timezone.now().strftime('%H%M%S')}",
        expired_at=invoice.tanggal_jatuh_tempo,
    )

    service = PaymentService()
    if method.type == "QRIS":
        service.create_qris(transaksi)
    elif method.type == "VIRTUAL_ACCOUNT":
        service.create_virtual_account(transaksi)
    elif method.type in ("MANUAL_TRANSFER", "CASH"):
        transaksi.status = PaymentTransaction.Status.PENDING
        transaksi.save(update_fields=["status"])
    # E-wallet/card/OTC -> tetap pending tanpa charge nyata saat ini

    invoice.status = Invoice.Status.PENDING
    invoice.save(update_fields=["status", "updated_at"])
    log_action(request, "BUAT_TRANSAKSI", "PaymentTransaction", transaksi.pk, new_value=method.code)

    next_page = "pembayaran:detail_transaksi"
    if method.type in ("MANUAL_TRANSFER", "CASH"):
        next_page = "pembayaran:upload_bukti"
    return redirect(next_page, pk=transaksi.pk)


@login_required
def detail_transaksi(request, pk):
    transaksi = get_object_or_404(
        PaymentTransaction.objects.select_related("invoice", "payment_method", "manual"), pk=pk
    )
    if not (transaksi.invoice.pengajuan.pemohon == request.user or _is_petugas_pembayaran(request.user)):
        return redirect("pembayaran:invoice_saya")

    qr_data_url = None
    if transaksi.qr_string:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(transaksi.qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    config = transaksi.payment_method.configuration or {}
    return render(
        request,
        "pembayaran/detail_transaksi.html",
        {"transaksi": transaksi, "qr_data_url": qr_data_url, "config": config},
    )


@login_required
def upload_bukti(request, pk):
    transaksi = get_object_or_404(PaymentTransaction, pk=pk)
    invoice = transaksi.invoice
    if request.user.role == "PEMOHON" and invoice.pengajuan.pemohon != request.user:
        return redirect("pembayaran:invoice_saya")
    if request.method == "POST" and "bukti" in request.FILES:
        manual, _ = PembayaranManual.objects.get_or_create(transaksi=transaksi)
        if manual.bukti:
            manual.bukti.delete(save=False)
        manual.bukti = request.FILES["bukti"]
        manual.catatan = request.POST.get("catatan", "")
        manual.save()
        transaksi.status = PaymentTransaction.Status.PENDING
        transaksi.save(update_fields=["status"])
        log_action(request, "UPLOAD_BUKTI_BAYAR", "PaymentTransaction", transaksi.pk)
        notify_role(
            "KOMERSIL",
            "Bukti pembayaran diunggah",
            f"{invoice.pengajuan.pemohon.nama_lengkap} mengunggah bukti pembayaran untuk "
            f"{invoice.nomor_invoice} (Rp {transaksi.amount:,.0f}). Menunggu verifikasi.",
            url=f"/pembayaran/verifikasi/{transaksi.pk}/",
            pengajuan=invoice.pengajuan,
        )
        messages.success(request, "Bukti pembayaran diunggah. Menunggu verifikasi petugas.")
        return redirect("pembayaran:detail_transaksi", pk=transaksi.pk)
    return render(request, "pembayaran/upload_bukti.html", {"transaksi": transaksi})


@user_passes_test(_is_petugas_pembayaran)
def verifikasi_manual(request, pk):
    """Verifikasi bukti manual oleh petugas. Hanya setelah verifikasi -> PAID."""
    transaksi = get_object_or_404(
        PaymentTransaction.objects.select_related("invoice", "manual", "payment_method"), pk=pk
    )
    if request.method == "POST":
        keputusan = request.POST.get("keputusan")  # VALID / INVALID
        if keputusan == "VALID":
            return tandai_lunas(request, transaksi)
        elif keputusan == "INVALID":
            transaksi.status = PaymentTransaction.Status.FAILED
            transaksi.save(update_fields=["status"])
            log_action(request, "VERIFIKASI_BAYAR_INVALID", "PaymentTransaction", transaksi.pk)
            messages.warning(request, "Bukti ditandai tidak valid.")
        return redirect("pembayaran:verifikasi_manual", pk=pk)
    return render(request, "pembayaran/verifikasi_manual.html", {"transaksi": transaksi})


def tandai_lunas(request, transaksi):
    """Tandai transaksi PAID (dari verifikasi petugas). Mengembalikan response."""
    if transaksi.status == "PAID":
        return redirect("pembayaran:verifikasi_manual", pk=transaksi.pk)
    transaksi.status = PaymentTransaction.Status.PAID
    transaksi.paid_at = timezone.now()
    transaksi.save(update_fields=["status", "paid_at"])
    if hasattr(transaksi, "manual"):
        transaksi.manual.verified_by = request.user
        transaksi.manual.verified_at = timezone.now()
        transaksi.manual.save()
    invoice = transaksi.invoice
    invoice.status = Invoice.Status.PAID
    invoice.save(update_fields=["status", "updated_at"])
    pengajuan = invoice.pengajuan
    pengajuan.status = Pengajuan.Status.DIBAYAR
    pengajuan.save(update_fields=["status", "updated_at"])
    log_action(request, "PAYMENT_PAID", "PaymentTransaction", transaksi.pk)
    messages.success(request, "Pembayaran diverifikasi lunas.")
    return redirect("pembayaran:verifikasi_manual", pk=transaksi.pk)


# ---------- Webhook ----------

@csrf_exempt
@require_POST
def webhook(request, provider):
    """Endpoint webhook provider (§14.5), idempotent."""
    raw_body = request.body
    signature = request.headers.get("X-Signature", "")
    secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "")

    # Validate signature
    service = PaymentService()
    if secret and not service.validate_webhook_signature(raw_body.decode("utf-8", "ignore"), signature):
        return HttpResponse("invalid signature", status=400)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return HttpResponse("invalid json", status=400)

    event_id = payload.get("event_id") or payload.get("id", "")
    merchant_ref = payload.get("merchant_reference") or payload.get("order_id", "")

    if event_id and WebhookLog.objects.filter(webhook_event_id=event_id, provider=provider).exists():
        return JsonResponse({"status": "duplicate"}, status=200)

    transaksi = (
        PaymentTransaction.objects.filter(merchant_reference=merchant_ref).first()
        or PaymentTransaction.objects.filter(provider_transaction_id=event_id).first()
    )
    if not transaksi:
        WebhookLog.objects.create(
            webhook_event_id=event_id, provider=provider, payload=payload,
            signature=signature, processing_status="FAILED",
        )
        return HttpResponse("transaction not found", status=404)

    # Validasi nominal & currency
    amount = payload.get("amount")
    if amount and str(amount) != str(transaksi.amount):
        return HttpResponse("amount mismatch", status=400)

    status_map = {
        "PAID": PaymentTransaction.Status.PAID,
        "paid": PaymentTransaction.Status.PAID,
        "EXPIRED": PaymentTransaction.Status.EXPIRED,
        "FAILED": PaymentTransaction.Status.FAILED,
    }
    new_status = status_map.get(payload.get("status", ""))
    if not new_status:
        return HttpResponse("unknown status", status=400)

    transaksi.provider_transaction_id = payload.get("transaction_id", event_id)
    transaksi.status = new_status
    if new_status == PaymentTransaction.Status.PAID:
        transaksi.paid_at = timezone.now()
        _finalize_paid(transaksi)
    transaksi.save()

    WebhookLog.objects.create(
        webhook_event_id=event_id, provider=provider, payload=payload,
        signature=signature, transaction=transaksi, processing_status="PROCESSED",
    )
    log_action(request, "WEBHOOK_PAYMENT", "PaymentTransaction", transaksi.pk, new_value=new_status)
    return JsonResponse({"status": "ok"})


def _finalize_paid(transaksi):
    invoice = transaksi.invoice
    if invoice.status != Invoice.Status.PAID:
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status", "updated_at"])
    pengajuan = invoice.pengajuan
    if pengajuan.status != Pengajuan.Status.DIBAYAR:
        pengajuan.status = Pengajuan.Status.DIBAYAR
        pengajuan.save(update_fields=["status", "updated_at"])


# ---------- Rekonsiliasi & admin ----------

@user_passes_test(_is_petugas_pembayaran)
def dashboard_pembayaran(request):
    filter_status = request.GET.get("status", "ALL")
    qs = PaymentTransaction.objects.select_related("invoice", "payment_method")
    if filter_status != "ALL":
        qs = qs.filter(status=filter_status)
    return render(
        request,
        "pembayaran/dashboard.html",
        {"transaksi": qs, "filter_status": filter_status},
    )


@user_passes_test(_is_petugas_pembayaran)
def minta_refund(request, pk):
    transaksi = get_object_or_404(PaymentTransaction, pk=pk, status=PaymentTransaction.Status.PAID)
    Refund.objects.get_or_create(
        transaksi=transaksi, status=Refund.Status.REQUESTED,
        defaults={"refund_amount": transaksi.amount, "requested_by": request.user},
    )
    messages.success(request, "Permintaan refund tercatat.")
    return redirect("pembayaran:dashboard_pembayaran")
