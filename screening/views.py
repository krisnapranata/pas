from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from audit.models import log_action
from pas.models import PengajuanPAS

from .forms import ScreeningScheduleForm
from .models import ScreeningBooking, ScreeningResult, ScreeningSchedule


def _is_petugas(user):
    return user.is_authenticated and (
        user.is_staff or getattr(user, "role", "") in ("PETUGAS_SCREENING", "ADMIN_PAS", "SECURITY")
    )


DISPLAY_STATUS_SHOWN = ("BOOKED", "CHECKED_IN", "PROCESS", "COMPLETED", "NO_SHOW")


@login_required
def jadwal_list(request):
    jadwal = ScreeningSchedule.objects.all()
    # auto refresh status kuota
    for j in jadwal:
        j.refresh_status()
    jadwal = ScreeningSchedule.objects.all()
    if request.user.role == "PEMOHON":
        open_only = jadwal.filter(status__in=["OPEN", "FULL"])
        return render(request, "screening/jadwal_pemohon.html", {"jadwal": open_only})
    return render(request, "screening/jadwal_admin.html", {"jadwal": jadwal})


@login_required
def jadwal_info(request, pk):
    """HTMX fragment: detail jadwal (kuota terisi/sisa)."""
    jadwal = get_object_or_404(ScreeningSchedule, pk=pk)
    jadwal.refresh_status()
    return render(request, "screening/partial_jadwal.html", {"jadwal": jadwal})


@login_required
def book(request, pk):
    jadwal = get_object_or_404(ScreeningSchedule, pk=pk)
    pengajuan = PengajuanPAS.objects.filter(pemohon=request.user, status__in=["ADMIN_APPROVED", "WAITING_SCREENING"]).first()
    if not pengajuan:
        messages.error(request, "Anda belum punya pengajuan yang disetujui admin untuk dijadwalkan screening.")
        return redirect("screening:jadwal_list")
    if jadwal.sisa <= 0:
        messages.error(request, "Kuota jadwal ini sudah penuh.")
        return redirect("screening:jadwal_list")
    existing = ScreeningBooking.objects.filter(pengajuan=pengajuan, status__in=["BOOKED", "CHECKED_IN", "PROCESS"]).exists()
    if existing:
        messages.warning(request, "Pengajuan ini sudah memiliki booking aktif.")
        return redirect("screening:jadwal_list")
    with transaction.atomic():
        jadwal = ScreeningSchedule.objects.select_for_update().get(pk=pk)
        if jadwal.sisa <= 0:
            messages.error(request, "Kuota jadwal ini sudah penuh.")
            return redirect("screening:jadwal_list")
        booking = ScreeningBooking.objects.create(pengajuan=pengajuan, jadwal=jadwal)
        booking.nomor_booking = booking._generate_nomor()
        booking.save(update_fields=["nomor_booking"])
        pengajuan.status = PengajuanPAS.Status.SCREENING_SCHEDULED
        pengajuan.save(update_fields=["status", "updated_at"])
        jadwal.refresh_status()
    log_action(request, "BOOKING_SCREENING", "ScreeningBooking", booking.pk)
    messages.success(request, f"Booking berhasil. Nomor booking {booking.nomor_booking}, antrian {booking.nomor_antrian}.")
    return redirect("screening:booking_saya")


@login_required
def booking_saya(request):
    bookings = ScreeningBooking.objects.filter(pengajuan__pemohon=request.user).select_related("jadwal", "pengajuan__jenis_pas")
    return render(request, "screening/booking_saya.html", {"bookings": bookings})


@user_passes_test(_is_petugas)
def daftar_peserta(request, pk):
    jadwal = get_object_or_404(ScreeningSchedule, pk=pk)
    bookings = jadwal.bookings.select_related("pengajuan__pemohon", "pengajuan__jenis_pas")
    return render(request, "screening/daftar_peserta.html", {"jadwal": jadwal, "bookings": bookings})


@user_passes_test(_is_petugas)
def checkin(request, pk):
    booking = get_object_or_404(ScreeningBooking, pk=pk)
    if booking.status == "BOOKED":
        booking.status = "CHECKED_IN"
        booking.save(update_fields=["status"])
        log_action(request, "CHECKIN_SCREENING", "ScreeningBooking", booking.pk)
        messages.success(request, f"{booking.pengajuan.pemohon} check-in.")
    return redirect("screening:daftar_peserta", pk=booking.jadwal.pk)


@user_passes_test(_is_petugas)
def input_hasil(request, pk):
    booking = get_object_or_404(
        ScreeningBooking.objects.select_related("pengajuan__pemohon", "jadwal"), pk=pk
    )
    if request.method == "POST":
        hasil = request.POST.get("hasil")
        catatan = request.POST.get("catatan", "")
        if hasil not in ("PASSED", "FAILED"):
            messages.error(request, "Pilih hasil screening.")
            return redirect("screening:input_hasil", pk=pk)
        result, _ = ScreeningResult.objects.get_or_create(
            booking=booking,
            defaults={"petugas": request.user, "hasil": hasil, "catatan": catatan},
        )
        if result.hasil != hasil or result.catatan != catatan:
            result.hasil = hasil
            result.catatan = catatan
            if not result.petugas_id:
                result.petugas = request.user
            result.save()
        booking.status = "COMPLETED"
        booking.save(update_fields=["status"])
        pengajuan = booking.pengajuan
        if hasil == "PASSED":
            pengajuan.status = PengajuanPAS.Status.SCREENING_PASSED
        else:
            pengajuan.status = PengajuanPAS.Status.SCREENING_FAILED
        pengajuan.save(update_fields=["status", "updated_at"])
        log_action(request, "INPUT_HASIL_SCREENING", "ScreeningResult", result.pk, new_value=hasil)
        messages.success(request, "Hasil screening tersimpan.")
        return redirect("screening:daftar_peserta", pk=booking.jadwal.pk)
    return render(request, "screening/input_hasil.html", {"booking": booking})


# ---------- Kelola jadwal (petugas/admin) ----------

@user_passes_test(_is_petugas)
def kelola_jadwal(request):
    jadwal = ScreeningSchedule.objects.all()
    for j in jadwal:
        j.refresh_status()
    return render(request, "screening/kelola_jadwal.html", {"jadwal": jadwal})


@user_passes_test(_is_petugas)
def tambah_jadwal(request):
    if request.method == "POST":
        form = ScreeningScheduleForm(request.POST)
        if form.is_valid():
            jadwal = form.save()
            jadwal.refresh_status()
            log_action(request, "BUAT_JADWAL_SCREENING", "ScreeningSchedule", jadwal.pk)
            messages.success(request, f"Jadwal {jadwal.tanggal} ditambahkan.")
            return redirect("screening:kelola_jadwal")
    else:
        form = ScreeningScheduleForm()
    return render(request, "screening/form_jadwal.html", {"form": form, "jadwal": None})


@user_passes_test(_is_petugas)
def edit_jadwal(request, pk):
    jadwal = get_object_or_404(ScreeningSchedule, pk=pk)
    if request.method == "POST":
        form = ScreeningScheduleForm(request.POST, instance=jadwal)
        if form.is_valid():
            jadwal = form.save()
            jadwal.refresh_status()
            log_action(request, "EDIT_JADWAL_SCREENING", "ScreeningSchedule", jadwal.pk)
            messages.success(request, "Jadwal diperbarui.")
            return redirect("screening:kelola_jadwal")
    else:
        form = ScreeningScheduleForm(instance=jadwal)
    return render(request, "screening/form_jadwal.html", {"form": form, "jadwal": jadwal})


@user_passes_test(_is_petugas)
def hapus_jadwal(request, pk):
    jadwal = get_object_or_404(ScreeningSchedule, pk=pk)
    if request.method == "POST":
        log_action(request, "HAPUS_JADWAL_SCREENING", "ScreeningSchedule", jadwal.pk)
        jadwal.delete()
        messages.success(request, "Jadwal dihapus.")
        return redirect("screening:kelola_jadwal")
    return render(request, "screening/hapus_jadwal.html", {"jadwal": jadwal})
