import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from pas.models import Layanan, Pengajuan
from pembayaran.models import Invoice, PaymentTransaction


@login_required
def home(request):
    user = request.user
    role = user.role
    if user.is_staff or role == "ADMINISTRATOR":
        return _home_admin(request)
    if role == "KOMERSIL":
        return _home_komersil(request)
    if role == "OPERASI":
        return _home_operasi(request)
    if role == "AOCH":
        return _home_aoch(request)
    return _home_pemohon(request)


def _home_pemohon(request):
    qs = Pengajuan.objects.filter(pemohon=request.user)
    konteks = {
        "total_pengajuan": qs.count(),
        "menunggu_verifikasi": qs.filter(
            status__in=["DIAJUKAN", "VERIFIKASI_KOMERSIL"]
        ).count(),
        "menunggu_operasi": qs.filter(
            status__in=["DISETUJUI_KOMERSIL", "MENUNGGU_OPERASI"]
        ).count(),
        "menunggu_pembayaran": qs.filter(status="MENUNGGU_PEMBAYARAN").count(),
        "sudah_dibayar": qs.filter(status="DIBAYAR").count(),
        "pas_terbit": qs.filter(status="PAS_TERBIT").count(),
        "ditolak": qs.filter(status="DITOLAK_OPERASI").count(),
        "pengajuan": qs.select_related("layanan").order_by("-created_at")[:10],
    }
    return render(request, "dashboard/home_pemohon.html", konteks)


def _home_komersil(request):
    today = timezone.now().date()
    bukti_bayar = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PENDING,
        manual__isnull=False,
    ).select_related("invoice__pengajuan__pemohon", "payment_method")
    konteks = {
        "pengajuan_baru": Pengajuan.objects.filter(status="DIAJUKAN").count(),
        "perlu_revisi": Pengajuan.objects.filter(status="REVISI_PEMOHON").count(),
        "disetujui_hari_ini": Pengajuan.objects.filter(
            status="DISETUJUI_KOMERSIL", updated_at__date=today
        ).count(),
        "menunggu_operasi": Pengajuan.objects.filter(status="MENUNGGU_OPERASI").count(),
        "menunggu_verifikasi_bayar": bukti_bayar.count(),
        "bukti_bayar": bukti_bayar.order_by("-created_at")[:10],
        "pengajuan": Pengajuan.objects.filter(
            status__in=["DIAJUKAN", "VERIFIKASI_KOMERSIL"]
        )
        .select_related("layanan", "pemohon")
        .order_by("-created_at")[:10],
    }
    return render(request, "dashboard/home_komersil.html", konteks)


def _home_operasi(request):
    konteks = {
        "menunggu_persetujuan": Pengajuan.objects.filter(status="MENUNGGU_OPERASI").count(),
        "disetujui": Pengajuan.objects.filter(status="MENUNGGU_PEMBAYARAN").count(),
        "ditolak": Pengajuan.objects.filter(status="DITOLAK_OPERASI").count(),
        "menunggu_pembayaran": Pengajuan.objects.filter(status="MENUNGGU_PEMBAYARAN").count(),
        "sudah_dibayar": Pengajuan.objects.filter(status="DIBAYAR").count(),
        "siap_terbit": Pengajuan.objects.filter(
            status__in=["DIBAYAR", "ACKNOWLEDGED_AOCH"]
        ).count(),
        "pas_terbit": Pengajuan.objects.filter(status="PAS_TERBIT").count(),
        "pengajuan": Pengajuan.objects.filter(
            status__in=[
                "MENUNGGU_OPERASI",
                "MENUNGGU_PEMBAYARAN",
                "DIBAYAR",
                "ACKNOWLEDGED_AOCH",
                "PAS_TERBIT",
            ]
        )
        .select_related("layanan", "pemohon")
        .order_by("-created_at")[:10],
    }
    return render(request, "dashboard/home_operasi.html", konteks)


def _home_aoch(request):
    konteks = {
        "belum_acknowledged": Pengajuan.objects.filter(status="DIBAYAR").count(),
        "acknowledged": Pengajuan.objects.filter(status="ACKNOWLEDGED_AOCH").count(),
        "pas_terbit": Pengajuan.objects.filter(status="PAS_TERBIT").count(),
        "pengajuan": Pengajuan.objects.filter(
            status__in=[
                "DIBAYAR",
                "ACKNOWLEDGED_AOCH",
                "PAS_TERBIT",
                "DILAKSANAKAN",
                "SELESAI",
            ]
        )
        .select_related("layanan", "pemohon")
        .order_by("-created_at")[:10],
    }
    return render(request, "dashboard/home_aoch.html", konteks)


def _home_admin(request):
    total_pemasukan = Invoice.objects.filter(status="PAID").aggregate(s=Sum("total"))["s"] or 0
    konteks = {
        "total_pengajuan": Pengajuan.objects.count(),
        "menunggu_verifikasi": Pengajuan.objects.filter(
            status__in=["DIAJUKAN", "VERIFIKASI_KOMERSIL"]
        ).count(),
        "menunggu_operasi": Pengajuan.objects.filter(status="MENUNGGU_OPERASI").count(),
        "menunggu_pembayaran": Pengajuan.objects.filter(status="MENUNGGU_PEMBAYARAN").count(),
        "selesai": Pengajuan.objects.filter(status="SELESAI").count(),
        "total_pemasukan": total_pemasukan,
        "layanan": Layanan.objects.filter(aktif=True).count(),
    }
    return render(request, "dashboard/home_admin.html", konteks)


@login_required
def statistik(request):
    if not (request.user.is_staff or request.user.role in ("ADMINISTRATOR", "KOMERSIL", "OPERASI", "AOCH")):
        return redirect("dashboard:home")

    status_count = dict(
        Pengajuan.objects.values_list("status").annotate(c=Count("id")).values_list("status", "c")
    )
    total_pemasukan = Invoice.objects.filter(status="PAID").aggregate(s=Sum("total"))["s"] or 0
    per_layanan = list(
        Pengajuan.objects.values("layanan__nama_layanan").annotate(c=Count("id")).order_by("-c")
    )
    konteks = {
        "total_pengajuan": Pengajuan.objects.count(),
        "status_rows": [
            (Pengajuan.Status[v].label, status_count.get(v, 0))
            for v, _ in Pengajuan.Status.choices
            if status_count.get(v, 0)
        ],
        "total_pemasukan": total_pemasukan,
        "invoice_paid": Invoice.objects.filter(status="PAID").count(),
        "per_layanan": per_layanan,
    }
    return render(request, "dashboard/statistik.html", konteks)


@login_required
def laporan(request):
    if not (request.user.is_staff or request.user.role in ("ADMINISTRATOR", "KOMERSIL", "OPERASI", "AOCH")):
        return redirect("dashboard:home")
    jenis = request.GET.get("jenis", "")
    status = request.GET.get("status", "")
    qs = Pengajuan.objects.select_related("layanan", "pemohon")
    if jenis:
        qs = qs.filter(layanan_id=jenis)
    if status:
        qs = qs.filter(status=status)
    return render(
        request,
        "dashboard/laporan.html",
        {
            "pengajuan": qs,
            "layanan_list": Layanan.objects.filter(aktif=True),
            "status_list": Pengajuan.Status.choices,
            "filter_jenis": jenis,
            "filter_status": status,
        },
    )


@login_required
def export_pengajuan_csv(request):
    if not (request.user.is_staff or request.user.role in ("ADMINISTRATOR", "KOMERSIL", "OPERASI", "AOCH")):
        return redirect("dashboard:home")
    qs = Pengajuan.objects.select_related("layanan", "pemohon").order_by("-created_at")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pengajuan_layanan.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Nomor", "Pemohon", "Instansi", "Nama PIC", "Layanan", "Tanggal Pelaksanaan",
         "Pendamping", "Total", "Status"]
    )
    for p in qs:
        writer.writerow(
            [
                p.nomor_pengajuan,
                p.nama_pemohon,
                p.instansi_pemohon,
                p.pic_nama,
                p.layanan.nama_layanan,
                p.tanggal_pelaksanaan,
                p.jumlah_pendamping,
                p.total,
                p.get_status_display(),
            ]
        )
    return response
