from datetime import timedelta

import csv

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from pas.models import JenisPAS, PASCard, PengajuanPAS
from pembayaran.models import Invoice
from screening.models import ScreeningBooking, ScreeningResult, ScreeningSchedule


@login_required
def home(request):
    user = request.user
    is_staff = user.is_staff or getattr(user, "role", "") != "PEMOHON"

    pengajuan_qs = PengajuanPAS.objects.all()
    if not is_staff:
        pengajuan_qs = pengajuan_qs.filter(pemohon=user)

    konteks = {
        "is_staff": is_staff,
        "pengajuan_aktif": pengajuan_qs.filter(
            status__in=["SUBMITTED", "DOCUMENT_REVIEW", "WAITING_SCREENING", "SCREENING_SCHEDULED", "SCREENING_PROCESS", "WAITING_PAYMENT", "WAITING_APPROVAL", "ADMIN_APPROVED", "SCREENING_PASSED"]
        ).count(),
        "pas_aktif": PASCard.objects.filter(status="ACTIVE").count() if is_staff else PASCard.objects.filter(pengajuan__pemohon=user, status="ACTIVE").count(),
        "tagihan": Invoice.objects.filter(status__in=["UNPAID", "PENDING"]).count() if is_staff else Invoice.objects.filter(pengajuan__pemohon=user, status__in=["UNPAID", "PENDING"]).count(),
    }
    return render(request, "dashboard/home.html", konteks)


@user_passes_test(lambda u: u.is_staff or getattr(u, "role", "") in ("ADMIN_PAS", "MANAGEMENT", "APPROVER"))
def statistik(request):
    """Dashboard management (§4): statistik pengajuan/screening/pembayaran/PAS."""
    now = timezone.now()

    total_pengajuan = PengajuanPAS.objects.count()
    status_count = dict(
        PengajuanPAS.objects.values_list("status").annotate(c=Count("id")).values_list("status", "c")
    )

    total_screening = ScreeningBooking.objects.count()
    screening_hasil = dict(
        ScreeningResult.objects.values_list("hasil").annotate(c=Count("id")).values_list("hasil", "c")
    )

    total_pemasukan = Invoice.objects.filter(status="PAID").aggregate(s=Sum("total"))["s"] or 0
    total_invoice = Invoice.objects.count()
    invoice_paid = Invoice.objects.filter(status="PAID").count()

    pas_aktif = PASCard.objects.filter(status="ACTIVE").count()
    pas_akan_expired = PASCard.objects.filter(
        status="ACTIVE",
        tanggal_expired__lte=now.date() + timedelta(days=30),
        tanggal_expired__gte=now.date(),
    ).count()
    pas_expired = PASCard.objects.filter(status="EXPIRED").count() + PASCard.objects.filter(
        status="ACTIVE", tanggal_expired__lt=now.date()
    ).count()

    # per jenis PAS
    per_jenis = list(
        PengajuanPAS.objects.values("jenis_pas__nama").annotate(c=Count("id")).order_by("-c")
    )

    konteks = {
        "total_pengajuan": total_pengajuan,
        "status_count": status_count,
        "status_rows": [
            (PengajuanPAS.Status[v].label, status_count.get(v, 0))
            for v, _ in PengajuanPAS.Status.choices
            if status_count.get(v, 0)
        ],
        "total_screening": total_screening,
        "screening_lulus": screening_hasil.get("PASSED", 0),
        "screening_gagal": screening_hasil.get("FAILED", 0),
        "total_pemasukan": total_pemasukan,
        "total_invoice": total_invoice,
        "invoice_paid": invoice_paid,
        "pas_aktif": pas_aktif,
        "pas_akan_expired": pas_akan_expired,
        "pas_expired": pas_expired,
        "per_jenis": per_jenis,
    }
    return render(request, "dashboard/statistik.html", konteks)


@user_passes_test(lambda u: u.is_staff or getattr(u, "role", "") in ("ADMIN_PAS", "MANAGEMENT"))
def laporan(request):
    """Halaman laporan dengan pilihan export CSV (§27)."""
    jenis = request.GET.get("jenis", "")
    status = request.GET.get("status", "")
    qs = PengajuanPAS.objects.select_related("jenis_pas", "pemohon", "perusahaan")
    if jenis:
        qs = qs.filter(jenis_pas_id=jenis)
    if status:
        qs = qs.filter(status=status)

    pas_cards = PASCard.objects.select_related("jenis_pas", "pengajuan__pemohon")

    return render(
        request,
        "dashboard/laporan.html",
        {
            "pengajuan": qs,
            "pas_cards": pas_cards,
            "jenis_list": JenisPAS.objects.filter(status_aktif=True),
            "status_list": PengajuanPAS.Status.choices,
            "filter_jenis": jenis,
            "filter_status": status,
        },
    )


@user_passes_test(lambda u: u.is_staff or getattr(u, "role", "") in ("ADMIN_PAS", "MANAGEMENT"))
def export_pengajuan_csv(request):
    """Export pengajuan ke CSV (§27)."""
    qs = PengajuanPAS.objects.select_related("jenis_pas", "pemohon", "perusahaan").order_by("-created_at")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pengajuan_pas.csv"'
    writer = csv.writer(response)
    writer.writerow(["Nomor", "Pemohon", "Perusahaan", "Jenis PAS", "Tanggal", "Status", "Keperluan"])
    for p in qs:
        writer.writerow([
            p.nomor_pengajuan,
            p.pemohon.get_full_name() or p.pemohon.username,
            p.perusahaan.nama if p.perusahaan else "",
            p.jenis_pas.nama,
            p.tanggal_pengajuan,
            p.get_status_display(),
            p.keperluan,
        ])
    return response


@user_passes_test(lambda u: u.is_staff or getattr(u, "role", "") in ("ADMIN_PAS", "MANAGEMENT"))
def export_pas_csv(request):
    """Export PAS terbit ke CSV."""
    qs = PASCard.objects.select_related("jenis_pas", "pengajuan__pemohon", "pengajuan__perusahaan").order_by("-tanggal_terbit")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pas_terbit.csv"'
    writer = csv.writer(response)
    writer.writerow(["Nomor PAS", "Pemohon", "Perusahaan", "Jenis", "Berlaku", "Expired", "Status"])
    for c in qs:
        writer.writerow([
            c.nomor_pas,
            c.pengajuan.pemohon.get_full_name() or c.pengajuan.pemohon.username,
            c.pengajuan.perusahaan.nama if c.pengajuan.perusahaan else "",
            c.jenis_pas.nama,
            c.tanggal_berlaku,
            c.tanggal_expired,
            c.get_status_display(),
        ])
    return response
