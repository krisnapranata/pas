from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audit.models import log_action

from .forms import DokumenUploadForm, PengajuanForm
from .models import (
    DokumenPengajuan,
    JenisPAS,
    PASCard,
    PengajuanPAS,
    Persyaratan,
    StatusRiwayat,
)
from .qr_utils import qr_png_data


def _is_staff(user):
    return user.is_authenticated and (user.is_staff or user.role != "PEMOHON")


def _set_status(pengajuan, status, user, catatan=""):
    pengajuan.status = status
    pengajuan.save(update_fields=["status", "updated_at"])
    StatusRiwayat.objects.create(
        pengajuan=pengajuan, status=status, catatan=catatan, oleh=user
    )


@login_required
def daftar_pengajuan(request):
    query = PengajuanPAS.objects.all()
    if not (request.user.is_staff or getattr(request.user, "role", "") != "PEMOHON"):
        query = query.filter(pemohon=request.user)
    pengajuan = query.select_related("jenis_pas", "perusahaan", "pemohon")
    return render(request, "pas/daftar_pengajuan.html", {"pengajuan": pengajuan})


@login_required
def buat_pengajuan(request):
    if request.method == "POST":
        form = PengajuanForm(request.POST)
        if form.is_valid():
            pengajuan = form.save(commit=False)
            pengajuan.pemohon = request.user
            pengajuan.status = PengajuanPAS.Status.DRAFT
            pengajuan.save()
            form.save_m2m()
            pengajuan.nomor_pengajuan = pengajuan._generate_nomor()
            pengajuan.save(update_fields=["nomor_pengajuan"])
            log_action(request, "CREATE_PENGAJUAN", "PengajuanPAS", pengajuan.pk)
            return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
    else:
        form = PengajuanForm()
    return render(request, "pas/buat_pengajuan.html", {"form": form})


@login_required
def detail_pengajuan(request, pk):
    pengajuan = get_object_or_404(
        PengajuanPAS.objects.select_related("jenis_pas", "perusahaan", "pemohon"),
        pk=pk,
    )
    if not (request.user.is_staff or pengajuan.pemohon == request.user):
        return redirect("pas:daftar_pengajuan")
    persyaratan = Persyaratan.objects.filter(jenis_pas=pengajuan.jenis_pas, aktif=True)
    # Peta dokumen berdasarkan persyaratan (pakai dict pk -> dokumen terakhir)
    dokumen = {d.persyaratan_id: d for d in pengajuan.dokumen.all()}
    syarat_data = [
        {
            "persyaratan": p,
            "dokumen": dokumen.get(p.id),
        }
        for p in persyaratan
    ]
    return render(
        request,
        "pas/detail_pengajuan.html",
        {"pengajuan": pengajuan, "syarat_data": syarat_data},
    )


@login_required
def submit_pengajuan(request, pk):
    pengajuan = get_object_or_404(PengajuanPAS, pk=pk, pemohon=request.user)
    if pengajuan.status == PengajuanPAS.Status.DRAFT:
        _set_status(pengajuan, PengajuanPAS.Status.SUBMITTED, request.user)
        log_action(request, "SUBMIT_PENGAJUAN", "PengajuanPAS", pk)
        messages.success(request, "Pengajuan berhasil diajukan.")
    return redirect("pas:detail_pengajuan", pk=pk)


@login_required
def upload_dokumen(request, pk, persyaratan_id):
    pengajuan = get_object_or_404(PengajuanPAS, pk=pk, pemohon=request.user)
    persyaratan = get_object_or_404(
        Persyaratan, pk=persyaratan_id, jenis_pas=pengajuan.jenis_pas
    )
    existing = pengajuan.dokumen.filter(persyaratan=persyaratan).first()
    if request.method == "POST":
        form = DokumenUploadForm(request.POST, request.FILES, persyaratan=persyaratan, instance=existing)
        if form.is_valid():
            dok = form.save(commit=False)
            dok.pengajuan = pengajuan
            dok.persyaratan = persyaratan
            dok.status_verifikasi = DokumenPengajuan.Status.UPLOADED
            dok.save()
            log_action(request, "UPLOAD_DOKUMEN", "DokumenPengajuan", dok.pk)
            messages.success(request, f"Dokumen {persyaratan.nama} berhasil diunggah.")
            return redirect("pas:detail_pengajuan", pk=pk)
    else:
        form = DokumenUploadForm(persyaratan=persyaratan, instance=existing)
    return render(
        request,
        "pas/upload_dokumen.html",
        {"form": form, "pengajuan": pengajuan, "persyaratan": persyaratan},
    )


@user_passes_test(_is_staff)
def verifikasi_dokumen(request, pk):
    pengajuan = get_object_or_404(PengajuanPAS, pk=pk)
    dokumen = pengajuan.dokumen.select_related("persyaratan", "verified_by")
    if request.method == "POST":
        for dok in dokumen:
            field_status = f"status_{dok.pk}"
            field_catatan = f"catatan_{dok.pk}"
            if field_status in request.POST:
                dok.status_verifikasi = request.POST[field_status]
                dok.catatan_verifikator = request.POST.get(field_catatan, "")
                dok.verified_by = request.user
                dok.verified_at = timezone.now()
                dok.save()
                log_action(
                    request,
                    "VERIFIKASI_DOKUMEN",
                    "DokumenPengajuan",
                    dok.pk,
                    new_value=dok.status_verifikasi,
                )
        # Tentukan hasil verifikasi dokumen
        statuses = set(dokumen.values_list("status_verifikasi", flat=True))
        if all(s == "VALID" for s in statuses):
            _set_status(pengajuan, PengajuanPAS.Status.ADMIN_APPROVED, request.user)
            messages.success(request, "Semua dokumen valid. Pengajuan disetujui admin.")
        elif "INVALID" in statuses:
            _set_status(pengajuan, PengajuanPAS.Status.REVISION_REQUIRED, request.user)
            messages.warning(request, "Ada dokumen tidak valid. Perlu revisi.")
        return redirect("pas:verifikasi_dokumen", pk=pk)
    return render(request, "pas/verifikasi_dokumen.html", {"pengajuan": pengajuan, "dokumen": dokumen})


@login_required
def detail_jenis_syarat(request, pk):
    jenis = get_object_or_404(JenisPAS, pk=pk)
    persyaratan = Persyaratan.objects.filter(jenis_pas=jenis, aktif=True)
    return render(
        request,
        "pas/jenis_syarat.html",
        {"jenis": jenis, "persyaratan": persyaratan},
    )


# ---------- PAS Card / Penerbitan (§16) ----------

@login_required
def pas_saya(request):
    cards = PASCard.objects.filter(pengajuan__pemohon=request.user).select_related(
        "jenis_pas", "pengajuan"
    )
    return render(request, "pas/pas_saya.html", {"cards": cards})


@login_required
def cetak_pas(request, pk):
    card = get_object_or_404(PASCard, pk=pk)
    if not (request.user.is_staff or card.pengajuan.pemohon == request.user):
        return redirect("pas:pas_saya")
    qr = qr_png_data(card.qr_token)
    return render(request, "pas/cetak_pas.html", {"card": card, "qr": qr})


@user_passes_test(_is_staff)
def terbitkan_pas(request, pengajuan_id):
    pengajuan = get_object_or_404(PengajuanPAS, pk=pengajuan_id)
    if pengajuan.status != PengajuanPAS.Status.APPROVED:
        messages.error(request, "Pengajuan belum disetujui (APPROVED).")
        return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
    card, created = PASCard.objects.get_or_create(
        pengajuan=pengajuan,
        defaults={
            "jenis_pas": pengajuan.jenis_pas,
            "tanggal_berlaku": pengajuan.tanggal_mulai or timezone.now().date(),
        },
    )
    if created:
        card.nomor_pas = card._generate_nomor()
        card.tanggal_expired = card.tanggal_berlaku + timezone.timedelta(
            days=pengajuan.jenis_pas.masa_berlaku_hari
        )
        card.issued_by = request.user
        card.save()
        _set_status(pengajuan, PengajuanPAS.Status.PAS_ISSUED, request.user)
        log_action(request, "TERBITKAN_PAS", "PASCard", card.pk, new_value=card.nomor_pas)
        messages.success(request, f"PAS diterbitkan: {card.nomor_pas}")
    return redirect("pas:detail_pengajuan", pk=pengajuan.pk)


@user_passes_test(_is_staff)
def daftar_pas_terbit(request):
    cards = PASCard.objects.select_related("jenis_pas", "pengajuan__pemohon").all()
    return render(request, "pas/daftar_pas_terbit.html", {"cards": cards})


@user_passes_test(_is_staff)
def cabut_pas(request, pk):
    card = get_object_or_404(PASCard, pk=pk)
    if request.method == "POST":
        card.status = PASCard.Status.REVOKED
        card.save(update_fields=["status"])
        log_action(request, "CABUT_PAS", "PASCard", card.pk)
        messages.success(request, f"PAS {card.nomor_pas} dicabut.")
        return redirect("pas:daftar_pas_terbit")
    return render(request, "pas/cabut_pas.html", {"card": card})


def verifikasi_qr(request, token):
    """Validasi QR publik (§17). Tidak butuh login."""
    card = get_object_or_404(
        PASCard.objects.select_related("jenis_pas", "pengajuan__pemohon", "pengajuan__perusahaan"),
        qr_token=token,
    )
    valid = card.is_valid
    return render(request, "pas/verifikasi_qr.html", {"card": card, "valid": valid})
