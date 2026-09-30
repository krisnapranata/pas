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

from accounts.templatetags.rupiah import format_rupiah
from audit.models import log_action
from notifikasi.services import notify_pemohon, notify_role
from pas.models import Pengajuan

from .forms import PaymentMethodForm
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


def _bisa_akses_pengajuan(request, pengajuan):
    """Pemilik akun, petugas, atau sesi lacak pemohon tanpa akun."""
    if _is_petugas_pembayaran(request.user):
        return True
    if request.user.is_authenticated and pengajuan.pemohon_id == request.user.id:
        return True
    return pengajuan.pk in request.session.get("lacak_pengajuan", [])


def _redirect_tak_berhak(request):
    if request.user.is_authenticated:
        return redirect("pembayaran:invoice_saya")
    messages.info(
        request,
        "Silakan lacak pengajuan dengan nomor pengajuan dan kontak untuk mengakses pembayaran.",
    )
    return redirect("pas:lacak_pengajuan")


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


def _tahap_pembayaran(status):
    """Status yang masih boleh mengakses menu bayar / upload bukti."""
    return status in (
        Pengajuan.Status.MENUNGGU_PEMBAYARAN,
        Pengajuan.Status.BUKTI_TERUNGGAH,
    )


def _arahkan_pembayaran(request, pengajuan):
    """Bawa pemohon dari nomor pengajuan ke halaman bayar / upload bukti."""
    invoice = Invoice.objects.filter(pengajuan=pengajuan).first()
    if invoice is None:
        if not _tahap_pembayaran(pengajuan.status):
            messages.info(
                request,
                "Pengajuan belum masuk tahap pembayaran. Silakan lihat status lengkapnya.",
            )
            return redirect("pas:lacak_detail", pk=pengajuan.pk)
        invoice = get_or_create_invoice(pengajuan)
    if invoice.transaksi_menunggu_verifikasi:
        # Bukti sudah diunggah -> detail transaksi (menunggu verifikasi petugas)
        return redirect(
            "pembayaran:detail_transaksi", pk=invoice.transaksi_menunggu_verifikasi.pk
        )
    menunggu_bukti = invoice.transaksi_menunggu_bukti
    if menunggu_bukti:
        return redirect("pembayaran:upload_bukti", pk=menunggu_bukti.pk)
    if invoice.status == Invoice.Status.PAID:
        messages.info(request, "Pembayaran sudah lunas, bukti tidak perlu diunggah lagi.")
        return redirect("pas:lacak_detail", pk=pengajuan.pk)
    return redirect("pembayaran:bayar", invoice_id=invoice.pk)


def cari_bukti(request):
    """Cari pengajuan dengan nomor + kontak (tanpa login) lalu lanjut bayar/upload.

    Dipakai dari halaman muka ketika pemohon membuka kembali situs di tab baru
    dan tidak ingat lagi harus membuka halaman pembayaran yang mana.
    """
    # Diimpor di dalam fungsi karena `pas.views` juga mengimpor modul ini.
    from pas.views import _kontak_cocok

    error = ""
    nomor = ""
    if request.method == "POST":
        nomor = (request.POST.get("nomor_pengajuan") or "").strip()
        kontak = (request.POST.get("kontak") or "").strip()
        pengajuan = Pengajuan.objects.filter(nomor_pengajuan__iexact=nomor).first()
        if pengajuan and _kontak_cocok(pengajuan, kontak):
            ids = request.session.get("lacak_pengajuan", [])
            if pengajuan.pk not in ids:
                ids.append(pengajuan.pk)
            request.session["lacak_pengajuan"] = ids[-20:]
            return _arahkan_pembayaran(request, pengajuan)
        error = "Nomor pengajuan dan kontak tidak cocok. Periksa kembali data Anda."
    return render(request, "pembayaran/cari_bukti.html", {"error": error, "nomor": nomor})


@login_required
def invoice_saya(request):
    invoices = Invoice.objects.filter(pengajuan__pemohon=request.user).select_related("pengajuan__layanan")
    return render(request, "pembayaran/invoice_saya.html", {"invoices": invoices})


def buat_invoice(request, pengajuan_id):
    pengajuan = get_object_or_404(Pengajuan, pk=pengajuan_id)
    if not _bisa_akses_pengajuan(request, pengajuan):
        return _redirect_tak_berhak(request)
    # Pembayaran dibuat sejak pengajuan lolos pengecekan NIK daftar hitam
    if not _tahap_pembayaran(pengajuan.status):
        messages.error(request, "Link pembayaran belum aktif (belum lolos pengecekan identitas).")
        if request.user.is_authenticated:
            return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
        return redirect("pas:lacak_detail", pk=pengajuan.pk)
    invoice = get_or_create_invoice(pengajuan)
    log_action(request, "BUAT_INVOICE", "Invoice", invoice.pk)
    return redirect("pembayaran:bayar", invoice_id=invoice.pk)


def bayar(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("pengajuan__layanan"), pk=invoice_id
    )
    if not _bisa_akses_pengajuan(request, invoice.pengajuan):
        return _redirect_tak_berhak(request)
    # Pemohon yang sudah menekan "Buat Transaksi" (misal tab-nya tertutup)
    # selalu diarahkan ke menu upload bukti. `?pilih_lain=1` dipakai bila
    # pemohon memang ingin memilih metode pembayaran lain.
    # Bukti sudah terunggah -> menuju detail transaksi (menunggu verifikasi),
    # jangan sampai disuruh membuat transaksi kedua.
    menunggu_verifikasi = invoice.transaksi_menunggu_verifikasi
    if menunggu_verifikasi and request.GET.get("pilih_lain") != "1":
        return redirect("pembayaran:detail_transaksi", pk=menunggu_verifikasi.pk)
    menunggu_bukti = invoice.transaksi_menunggu_bukti
    if menunggu_bukti and request.GET.get("pilih_lain") != "1":
        return redirect("pembayaran:upload_bukti", pk=menunggu_bukti.pk)
    # Termasuk jenis nonaktif supaya bisa ditampilkan sebagai pilihan yang
    # dinonaktifkan (disable) di menu pembayaran pemohon.
    methods = PaymentMethod.objects.all()
    return render(request, "pembayaran/bayar.html", {"invoice": invoice, "methods": methods})


@require_POST
def buat_transaksi(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("pengajuan"), pk=invoice_id
    )
    if not _bisa_akses_pengajuan(request, invoice.pengajuan):
        return _redirect_tak_berhak(request)
    method_id = request.POST.get("method")
    method = get_object_or_404(PaymentMethod, pk=method_id, active=True)

    if invoice.status == Invoice.Status.PAID:
        messages.info(request, "Invoice sudah lunas.")
        if request.user.is_authenticated:
            return redirect("pembayaran:invoice_saya")
        return redirect("pas:lacak_detail", pk=invoice.pengajuan_id)

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

    # Langsung ke menu upload bukti agar pemohon tahu langkah berikutnya;
    # bila tab ditutup, ia akan diarahkan ke halaman yang sama saat kembali.
    return redirect("pembayaran:upload_bukti", pk=transaksi.pk)


def detail_transaksi(request, pk):
    transaksi = get_object_or_404(
        PaymentTransaction.objects.select_related("invoice", "payment_method", "manual"), pk=pk
    )
    if not _bisa_akses_pengajuan(request, transaksi.invoice.pengajuan):
        return _redirect_tak_berhak(request)

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


def upload_bukti(request, pk):
    transaksi = get_object_or_404(
        PaymentTransaction.objects.select_related("invoice__pengajuan"), pk=pk
    )
    invoice = transaksi.invoice
    if not _bisa_akses_pengajuan(request, invoice.pengajuan):
        return _redirect_tak_berhak(request)
    if request.method == "POST" and "bukti" in request.FILES:
        manual, _ = PembayaranManual.objects.get_or_create(transaksi=transaksi)
        if manual.bukti:
            manual.bukti.delete(save=False)
        manual.bukti = request.FILES["bukti"]
        manual.catatan = request.POST.get("catatan", "")
        manual.save()
        transaksi.status = PaymentTransaction.Status.PENDING
        transaksi.save(update_fields=["status"])
        pengajuan = invoice.pengajuan
        if pengajuan.status == Pengajuan.Status.MENUNGGU_PEMBAYARAN:
            from pas.services import set_status

            set_status(
                pengajuan,
                Pengajuan.Status.BUKTI_TERUNGGAH,
                request.user if request.user.is_authenticated else None,
                catatan="Bukti pembayaran diunggah pemohon.",
            )
        log_action(request, "UPLOAD_BUKTI_BAYAR", "PaymentTransaction", transaksi.pk)
        notify_role(
            "KOMERSIL",
            "Bukti pembayaran diunggah",
            f"{invoice.pengajuan.nama_pemohon} mengunggah bukti pembayaran untuk "
            f"{invoice.nomor_invoice} (Rp {format_rupiah(transaksi.amount)}). Menunggu verifikasi.",
            url=f"/pembayaran/verifikasi/{transaksi.pk}/",
            pengajuan=invoice.pengajuan,
        )
        notify_pemohon(
            invoice.pengajuan,
            "Bukti pembayaran diterima",
            f"Bukti pembayaran untuk {invoice.nomor_invoice} sudah kami terima dan "
            "sedang menunggu verifikasi petugas.",
            url=f"/pas/lacak/{invoice.pengajuan.pk}/",
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
            from pas.services import set_status

            transaksi.status = PaymentTransaction.Status.FAILED
            transaksi.save(update_fields=["status"])
            pengajuan = transaksi.invoice.pengajuan
            if pengajuan.status == Pengajuan.Status.BUKTI_TERUNGGAH:
                set_status(
                    pengajuan,
                    Pengajuan.Status.MENUNGGU_PEMBAYARAN,
                    request.user,
                    catatan="Bukti pembayaran ditandai tidak valid; pemohon mengunggah ulang.",
                )
                notify_pemohon(
                    pengajuan,
                    "Bukti pembayaran ditolak",
                    f"Bukti pembayaran untuk {transaksi.invoice.nomor_invoice} tidak valid. "
                    "Silakan unggah bukti yang benar.",
                    url=f"/pembayaran/bayar/{transaksi.invoice.pk}/",
                )
            log_action(request, "VERIFIKASI_BAYAR_INVALID", "PaymentTransaction", transaksi.pk)
            messages.warning(request, "Bukti ditandai tidak valid.")
        return redirect("pembayaran:verifikasi_manual", pk=pk)
    return render(request, "pembayaran/verifikasi_manual.html", {"transaksi": transaksi})


def tandai_lunas(request, transaksi):
    """Tandai transaksi PAID (dari verifikasi petugas). Mengembalikan response."""
    if transaksi.status == "PAID":
        return redirect("pembayaran:verifikasi_manual", pk=transaksi.pk)
    from pas.services import set_status

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
    if pengajuan.status != Pengajuan.Status.DIBAYAR:
        set_status(pengajuan, Pengajuan.Status.DIBAYAR, request.user)
    log_action(request, "PAYMENT_PAID", "PaymentTransaction", transaksi.pk)
    notify_role(
        "KOMERSIL",
        "Bukti bayar tervalidasi",
        f"Pembayaran {invoice.nomor_invoice} (Rp {format_rupiah(transaksi.amount)}) "
        f"untuk pengajuan {pengajuan.nomor_pengajuan} lunas. Silakan teruskan ke "
        "Operasi untuk penerbitan PAS.",
        url=f"/pas/verifikasi/",
        pengajuan=pengajuan,
    )
    notify_pemohon(
        pengajuan,
        "Pembayaran diterima",
        f"Pembayaran pengajuan {pengajuan.nomor_pengajuan} telah diverifikasi. "
        "Pengajuan diteruskan ke Operasi untuk penerbitan PAS.",
        url=f"/pas/lacak/{pengajuan.pk}/",
    )
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
    from pas.services import set_status

    invoice = transaksi.invoice
    if invoice.status != Invoice.Status.PAID:
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status", "updated_at"])
    pengajuan = invoice.pengajuan
    if pengajuan.status != Pengajuan.Status.DIBAYAR:
        set_status(pengajuan, Pengajuan.Status.DIBAYAR)
        notify_role(
            "KOMERSIL",
            "Pembayaran diterima",
            f"Pengajuan {pengajuan.nomor_pengajuan} sudah dibayar. "
            "Silakan validasi bukti bayar & teruskan ke Operasi.",
            url="/pas/verifikasi/",
            pengajuan=pengajuan,
        )


# ---------- Rekonsiliasi & admin ----------

@user_passes_test(_is_petugas_pembayaran)
def dashboard_pembayaran(request):
    filter_status = request.GET.get("status", "ALL")
    qs = PaymentTransaction.objects.select_related(
        "invoice__pengajuan__pemohon",
        "invoice__pengajuan__layanan",
        "payment_method",
        "manual",
    ).order_by("-created_at")
    if filter_status != "ALL":
        qs = qs.filter(status=filter_status)
    menunggu_bukti = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PENDING, manual__isnull=False
    ).count()
    belum_bukti = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PENDING, manual__isnull=True
    ).count()
    return render(
        request,
        "pembayaran/dashboard.html",
        {
            "transaksi": qs,
            "filter_status": filter_status,
            "menunggu_bukti": menunggu_bukti,
            "belum_bukti": belum_bukti,
        },
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


# ---------- Kelola jenis pembayaran (Komersil / Admin) ----------


@login_required
def jenis_list(request):
    if not _is_petugas_pembayaran(request.user):
        messages.error(request, "Anda tidak berhak mengelola jenis pembayaran.")
        return redirect("dashboard:home")
    return render(
        request,
        "pembayaran/jenis_list.html",
        {"methods": PaymentMethod.objects.all()},
    )


@login_required
def jenis_buat(request):
    if not _is_petugas_pembayaran(request.user):
        messages.error(request, "Anda tidak berhak mengelola jenis pembayaran.")
        return redirect("dashboard:home")
    form = PaymentMethodForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        log_action(request, "BUAT_JENIS_PEMBAYARAN", "PaymentMethod", obj.pk,
                   new_value=obj.code)
        messages.success(request, f"Jenis pembayaran {obj.name} berhasil ditambahkan.")
        return redirect("pembayaran:jenis_list")
    return render(
        request,
        "pembayaran/jenis_form.html",
        {"form": form, "judul": "Tambah Jenis Pembayaran"},
    )


@login_required
def jenis_edit(request, pk):
    if not _is_petugas_pembayaran(request.user):
        messages.error(request, "Anda tidak berhak mengelola jenis pembayaran.")
        return redirect("dashboard:home")
    obj = get_object_or_404(PaymentMethod, pk=pk)
    form = PaymentMethodForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj_lama = PaymentMethod.objects.get(pk=pk)
        form.save()
        log_action(request, "UBAH_JENIS_PEMBAYARAN", "PaymentMethod", pk,
                   old_value=obj_lama.code, new_value=obj.code)
        messages.success(request, f"Jenis pembayaran {obj.name} berhasil diperbarui.")
        return redirect("pembayaran:jenis_list")
    return render(
        request,
        "pembayaran/jenis_form.html",
        {"form": form, "judul": f"Edit Jenis Pembayaran: {obj.name}", "obj": obj},
    )


@login_required
@require_POST
def jenis_hapus(request, pk):
    if not _is_petugas_pembayaran(request.user):
        messages.error(request, "Anda tidak berhak mengelola jenis pembayaran.")
        return redirect("dashboard:home")
    obj = get_object_or_404(PaymentMethod, pk=pk)
    if PaymentTransaction.objects.filter(payment_method=obj).exists():
        messages.error(
            request,
            f"{obj.name} tidak bisa dihapus karena sudah dipakai transaksi. "
            "Gunakan status Nonaktif sebagai gantinya.",
        )
        return redirect("pembayaran:jenis_list")
    log_action(request, "HAPUS_JENIS_PEMBAYARAN", "PaymentMethod", pk, old_value=obj.code)
    nama = obj.name
    obj.delete()
    messages.success(request, f"Jenis pembayaran {nama} dihapus.")
    return redirect("pembayaran:jenis_list")


@login_required
@require_POST
def jenis_status(request, pk):
    """Aktifkan / nonaktifkan jenis pembayaran."""
    if not _is_petugas_pembayaran(request.user):
        messages.error(request, "Anda tidak berhak mengelola jenis pembayaran.")
        return redirect("dashboard:home")
    obj = get_object_or_404(PaymentMethod, pk=pk)
    obj.active = not obj.active
    obj.save(update_fields=["active"])
    log_action(request, "STATUS_JENIS_PEMBAYARAN", "PaymentMethod", pk,
               new_value="Aktif" if obj.active else "Nonaktif")
    messages.success(
        request,
        f"{obj.name} kini {'AKTIF' if obj.active else 'NONAKTIF'} — "
        + (
            "tampil kembali di menu pembayaran pemohon."
            if obj.active
            else "dinonaktifkan (disable) di menu pembayaran pemohon."
        ),
    )
    return redirect("pembayaran:jenis_list")
