from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.templatetags.rupiah import format_rupiah
from audit.models import log_action
from notifikasi.services import notify, notify_role
from pembayaran.views import get_or_create_invoice

from .forms import PengajuanForm
from .models import (
    DaftarHitam,
    DokumenPendamping,
    Pengajuan,
    StatusRiwayat,
)

TIMELINE = [
    ("DRAFT", "Draft"),
    ("DIAJUKAN", "Diajukan"),
    ("VERIFIKASI_KOMERSIL", "Verifikasi Komersil"),
    ("DISETUJUI_KOMERSIL", "Disetujui Komersil"),
    ("MENUNGGU_OPERASI", "Menunggu Operasi"),
    ("MENUNGGU_PEMBAYARAN", "Menunggu Pembayaran"),
    ("DIBAYAR", "Sudah Dibayar"),
    ("PAS_TERBIT", "PAS Diterbitkan"),
]


def _has_role(user, *roles):
    return user.is_authenticated and (user.is_staff or user.role in roles)


def _is_komersil(user):
    return _has_role(user, "KOMERSIL")


def _is_operasi(user):
    return _has_role(user, "OPERASI")


def _is_aoch(user):
    return _has_role(user, "AOCH")


def _is_petugas(user):
    return _has_role(user, "KOMERSIL", "OPERASI", "AOCH")


def _set_status(pengajuan, status, user, catatan=""):
    pengajuan.status = status
    pengajuan.save(update_fields=["status", "updated_at"])
    StatusRiwayat.objects.create(
        pengajuan=pengajuan, status=status, catatan=catatan, oleh=user
    )


def _blacklist_hit(pemohon):
    nama = (pemohon.nama_lengkap or "").strip()
    if nama:
        hit = DaftarHitam.objects.filter(
            aktif=True, tipe=DaftarHitam.Tipe.ORANG, nama__iexact=nama
        ).first()
        if hit:
            return hit
    if pemohon.instansi:
        return DaftarHitam.objects.filter(
            aktif=True, tipe=DaftarHitam.Tipe.PERUSAHAAN, nama__iexact=pemohon.instansi.strip()
        ).first()
    return None


def _simpan_pendamping(pengajuan, jumlah_pendamping, post, files):
    """Simpan dokumen identitas pendamping. Return daftar error."""
    pengajuan.pendamping.all().delete()
    errors = []
    for i in range(1, jumlah_pendamping + 1):
        nama = (post.get(f"pendamping_nama_{i}") or "").strip()
        file = files.get(f"pendamping_file_{i}")
        if not nama or not file:
            errors.append(f"Pendamping {i}: nama dan dokumen identitas wajib diisi.")
            continue
        DokumenPendamping.objects.create(
            pengajuan=pengajuan, urutan=i, nama=nama, file=file
        )
    return errors


def _build_timeline(current_status):
    items = []
    reached = True
    for code, label in TIMELINE:
        if current_status == code:
            state = "current"
            reached = False
        elif reached:
            state = "done"
        else:
            state = "todo"
        items.append({"code": code, "label": label, "state": state})
    return items


# ---------- Pemohon ----------

@login_required
def daftar_pengajuan(request):
    query = Pengajuan.objects.select_related("layanan", "pemohon")
    if not _is_petugas(request.user):
        query = query.filter(pemohon=request.user)
    return render(request, "pas/daftar_pengajuan.html", {"pengajuan": query})


@login_required
def buat_pengajuan(request):
    if request.method == "POST":
        form = PengajuanForm(request.POST)
        if form.is_valid():
            pengajuan = form.save(commit=False)
            pengajuan.pemohon = request.user
            pengajuan.status = Pengajuan.Status.DRAFT
            pengajuan.simpan_snapshot_tarif()
            pengajuan.save()
            errors = _simpan_pendamping(
                pengajuan, pengajuan.jumlah_pendamping, request.POST, request.FILES
            )
            if errors:
                pengajuan.delete()
                for e in errors:
                    messages.error(request, e)
            else:
                pengajuan.nomor_pengajuan = pengajuan._generate_nomor()
                pengajuan.save(update_fields=["nomor_pengajuan"])
                log_action(request, "BUAT_PENGAJUAN", "Pengajuan", pengajuan.pk)
                messages.success(
                    request,
                    "Draft pengajuan dibuat. Silakan ajukan untuk diproses.",
                )
                return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
    else:
        form = PengajuanForm(
            initial={
                "pic_nama": request.user.nama_lengkap,
                "pic_jabatan": request.user.jabatan,
                "pic_nomor_identitas": request.user.nomor_identitas,
                "pic_no_hp": request.user.phone,
                "pic_email": request.user.email,
            }
        )
    return render(
        request,
        "pas/buat_pengajuan.html",
        {"form": form, "pendamping_names": []},
    )


@login_required
def edit_pengajuan(request, pk):
    pengajuan = get_object_or_404(Pengajuan, pk=pk, pemohon=request.user)
    if pengajuan.status not in (Pengajuan.Status.DRAFT, Pengajuan.Status.REVISI_PEMOHON):
        messages.error(request, "Pengajuan tidak dapat diubah pada status ini.")
        return redirect("pas:detail_pengajuan", pk=pk)
    if request.method == "POST":
        form = PengajuanForm(request.POST, instance=pengajuan)
        if form.is_valid():
            pengajuan = form.save(commit=False)
            pengajuan.simpan_snapshot_tarif()
            pengajuan.save()
            errors = _simpan_pendamping(
                pengajuan, pengajuan.jumlah_pendamping, request.POST, request.FILES
            )
            if errors:
                for e in errors:
                    messages.error(request, e)
            else:
                log_action(request, "EDIT_PENGAJUAN", "Pengajuan", pengajuan.pk)
                messages.success(request, "Pengajuan diperbarui.")
                return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
    else:
        form = PengajuanForm(instance=pengajuan)
    return render(
        request,
        "pas/buat_pengajuan.html",
        {
            "form": form,
            "pengajuan": pengajuan,
            "pendamping_names": list(pengajuan.pendamping.values_list("nama", flat=True)),
        },
    )


@login_required
def detail_pengajuan(request, pk):
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    if not (_is_petugas(request.user) or pengajuan.pemohon == request.user):
        return redirect("pas:daftar_pengajuan")

    pendamping = pengajuan.pendamping.all()
    timeline = _build_timeline(pengajuan.status)

    return render(
        request,
        "pas/detail_pengajuan.html",
        {
            "pengajuan": pengajuan,
            "pendamping": pendamping,
            "timeline": timeline,
            "is_komersil": _is_komersil(request.user),
            "is_operasi": _is_operasi(request.user),
            "is_aoch": _is_aoch(request.user),
            "is_petugas": _is_petugas(request.user),
        },
    )


@login_required
def submit_pengajuan(request, pk):
    pengajuan = get_object_or_404(Pengajuan, pk=pk, pemohon=request.user)
    if pengajuan.status not in (Pengajuan.Status.DRAFT, Pengajuan.Status.REVISI_PEMOHON):
        return redirect("pas:detail_pengajuan", pk=pk)

    if pengajuan.pendamping.count() < pengajuan.jumlah_pendamping:
        messages.error(
            request,
            f"Lengkapi dokumen identitas {pengajuan.jumlah_pendamping} pendamping sebelum mengajukan.",
        )
        return redirect("pas:edit_pengajuan", pk=pk)

    hit = _blacklist_hit(request.user)
    if hit:
        alasan = f"Terdaftar dalam daftar hitam: {hit.nama}. {hit.alasan}".strip()
        _set_status(pengajuan, Pengajuan.Status.DITOLAK_OPERASI, request.user, catatan=alasan)
        notify(
            request.user,
            "Pengajuan ditolak",
            alasan,
            url=f"/pas/pengajuan/{pk}/",
            pengajuan=pengajuan,
        )
        log_action(request, "TOLAK_BLACKLIST", "Pengajuan", pk, new_value=hit.nama)
        messages.error(request, "Pengajuan ditolak karena terdaftar dalam daftar hitam.")
        return redirect("pas:detail_pengajuan", pk=pk)

    _set_status(pengajuan, Pengajuan.Status.DIAJUKAN, request.user)
    notify_role(
        "KOMERSIL",
        "Pengajuan baru",
        f"Pengajuan {pengajuan.nomor_pengajuan} menunggu verifikasi.",
        url=f"/pas/verifikasi/{pk}/",
        pengajuan=pengajuan,
    )
    log_action(request, "SUBMIT_PENGAJUAN", "Pengajuan", pk)
    messages.success(request, "Pengajuan berhasil diajukan.")
    return redirect("pas:detail_pengajuan", pk=pk)


# ---------- Komersil ----------

@login_required
def verifikasi_list(request):
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    query = Pengajuan.objects.filter(
        status__in=[
            Pengajuan.Status.DIAJUKAN,
            Pengajuan.Status.VERIFIKASI_KOMERSIL,
        ]
    ).select_related("layanan", "pemohon")
    return render(request, "pas/verifikasi_list.html", {"pengajuan": query})


@login_required
def verifikasi_dokumen(request, pk):
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    pendamping = pengajuan.pendamping.all()

    if request.method == "POST":
        aksi = request.POST.get("aksi")
        for pd in pendamping:
            f_status = f"pd_status_{pd.pk}"
            if f_status in request.POST:
                pd.status_verifikasi = request.POST[f_status]
                pd.verified_by = request.user
                pd.verified_at = timezone.now()
                pd.save()

        catatan = request.POST.get("catatan", "")
        if aksi == "revisi":
            _set_status(pengajuan, Pengajuan.Status.REVISI_PEMOHON, request.user, catatan=catatan)
            notify(
                pengajuan.pemohon,
                "Pengajuan perlu revisi",
                catatan or "Data/dokumen perlu diperbaiki.",
                url=f"/pas/pengajuan/{pk}/",
                pengajuan=pengajuan,
            )
            log_action(request, "MINTA_REVISI", "Pengajuan", pk, new_value=catatan)
            messages.warning(request, "Pemohon diminta melakukan revisi.")
        elif aksi == "setujui":
            _set_status(pengajuan, Pengajuan.Status.DISETUJUI_KOMERSIL, request.user, catatan=catatan)
            _set_status(pengajuan, Pengajuan.Status.MENUNGGU_OPERASI, request.user, catatan=catatan)
            notify(
                pengajuan.pemohon,
                "Data lengkap",
                "Data pengajuan Anda dinyatakan lengkap oleh Komersil dan menunggu persetujuan Operasi.",
                url=f"/pas/pengajuan/{pk}/",
                pengajuan=pengajuan,
            )
            notify_role(
                "OPERASI",
                "Pengajuan menunggu keputusan",
                f"Pengajuan {pengajuan.nomor_pengajuan} siap diputuskan Operasi.",
                url=f"/pas/operasi/{pk}/",
                pengajuan=pengajuan,
            )
            log_action(request, "SETUJUI_KOMERSIL", "Pengajuan", pk)
            messages.success(request, "Pengajuan disetujui dan diteruskan ke Operasi.")
        return redirect("pas:verifikasi_dokumen", pk=pk)

    return render(
        request,
        "pas/verifikasi_dokumen.html",
        {"pengajuan": pengajuan, "pendamping": pendamping},
    )


# ---------- Operasi ----------

@login_required
def operasi_list(request):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    query = Pengajuan.objects.filter(
        status__in=[
            Pengajuan.Status.MENUNGGU_OPERASI,
            Pengajuan.Status.MENUNGGU_PEMBAYARAN,
            Pengajuan.Status.DIBAYAR,
            Pengajuan.Status.PAS_TERBIT,
            Pengajuan.Status.ACKNOWLEDGED_AOCH,
            Pengajuan.Status.DILAKSANAKAN,
        ]
    ).select_related("layanan", "pemohon")
    return render(request, "pas/operasi_list.html", {"pengajuan": query})


@login_required
def operasi_proses(request, pk):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    pendamping = pengajuan.pendamping.all()
    if request.method == "POST":
        aksi = request.POST.get("aksi")
        alasan = request.POST.get("alasan", "")
        if aksi == "TOLAK":
            if not alasan.strip():
                messages.error(request, "Alasan penolakan wajib diisi.")
                return redirect("pas:operasi_proses", pk=pk)
            _set_status(pengajuan, Pengajuan.Status.DITOLAK_OPERASI, request.user, catatan=alasan)
            notify(
                pengajuan.pemohon,
                "Pengajuan ditolak Operasi",
                f"Alasan: {alasan}",
                url=f"/pas/pengajuan/{pk}/",
                pengajuan=pengajuan,
            )
            log_action(request, "TOLAK_OPERASI", "Pengajuan", pk, new_value=alasan)
            messages.warning(request, "Pengajuan ditolak.")
        elif aksi == "SETUJUI":
            hit = _blacklist_hit(pengajuan.pemohon)
            if hit:
                alasan = f"Terdaftar dalam daftar hitam: {hit.nama}. {hit.alasan}".strip()
                _set_status(pengajuan, Pengajuan.Status.DITOLAK_OPERASI, request.user, catatan=alasan)
                notify(
                    pengajuan.pemohon,
                    "Pengajuan ditolak",
                    alasan,
                    url=f"/pas/pengajuan/{pk}/",
                    pengajuan=pengajuan,
                )
                log_action(request, "TOLAK_BLACKLIST", "Pengajuan", pk, new_value=hit.nama)
                messages.error(request, "Pengajuan ditolak karena daftar hitam.")
            else:
                _set_status(pengajuan, Pengajuan.Status.DISETUJUI_OPERASI, request.user)
                _set_status(pengajuan, Pengajuan.Status.MENUNGGU_PEMBAYARAN, request.user)
                get_or_create_invoice(pengajuan)
                notify(
                    pengajuan.pemohon,
                    "Pengajuan disetujui Operasi",
                    f"Total pembayaran: Rp{format_rupiah(pengajuan.total)}. Silakan lakukan pembayaran.",
                    url=f"/pas/pengajuan/{pk}/",
                    pengajuan=pengajuan,
                )
                notify_role(
                    "AOCH",
                    "Pengajuan disetujui",
                    f"Pengajuan {pengajuan.nomor_pengajuan} disetujui Operasi.",
                    url=f"/pas/pengajuan/{pk}/",
                    pengajuan=pengajuan,
                )
                log_action(request, "SETUJUI_OPERASI", "Pengajuan", pk)
                messages.success(request, "Pengajuan disetujui. Link pembayaran aktif.")
        return redirect("pas:operasi_proses", pk=pk)
    return render(
        request,
        "pas/operasi_proses.html",
        {"pengajuan": pengajuan, "pendamping": pendamping},
    )


@login_required
def terbitkan_pas(request, pk):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(Pengajuan, pk=pk)
    if request.method == "POST" and pengajuan.status in (
        Pengajuan.Status.DIBAYAR,
        Pengajuan.Status.ACKNOWLEDGED_AOCH,
    ):
        _set_status(pengajuan, Pengajuan.Status.PAS_TERBIT, request.user)
        notify(
            pengajuan.pemohon,
            "PAS diterbitkan",
            f"PAS untuk pengajuan {pengajuan.nomor_pengajuan} telah diterbitkan. "
            "Silakan diambil di Operasi.",
            url=f"/pas/pengajuan/{pk}/",
            pengajuan=pengajuan,
        )
        notify_role(
            "AOCH",
            "PAS diterbitkan",
            f"PAS untuk pengajuan {pengajuan.nomor_pengajuan} telah diterbitkan oleh Operasi.",
            url=f"/pas/pengajuan/{pk}/",
            pengajuan=pengajuan,
        )
        log_action(request, "TERBITKAN_PAS", "Pengajuan", pk)
        messages.success(request, "PAS diterbitkan. Pemohon diberitahu untuk mengambil PAS di Operasi.")
    return redirect("pas:operasi_proses", pk=pk)


@login_required
def tandai_pelaksanaan(request, pk):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(Pengajuan, pk=pk)
    if request.method == "POST":
        aksi = request.POST.get("aksi")
        if aksi == "DILAKSANAKAN" and pengajuan.status in (
            Pengajuan.Status.ACKNOWLEDGED_AOCH,
            Pengajuan.Status.SIAP_DILAKSANAKAN,
        ):
            _set_status(pengajuan, Pengajuan.Status.DILAKSANAKAN, request.user)
            messages.success(request, "Layanan ditandai dilaksanakan.")
        elif aksi == "SELESAI" and pengajuan.status == Pengajuan.Status.DILAKSANAKAN:
            _set_status(pengajuan, Pengajuan.Status.SELESAI, request.user)
            notify(
                pengajuan.pemohon,
                "Layanan selesai",
                f"Layanan {pengajuan.layanan.nama_layanan} telah selesai dilaksanakan.",
                url=f"/pas/pengajuan/{pk}/",
                pengajuan=pengajuan,
            )
            messages.success(request, "Pengajuan ditandai selesai.")
        return redirect("pas:operasi_proses", pk=pk)
    return redirect("pas:operasi_proses", pk=pk)


# ---------- AOCH ----------

@login_required
def aoch_list(request):
    if not _is_aoch(request.user):
        return redirect("dashboard:home")
    query = Pengajuan.objects.filter(
        status__in=[
            Pengajuan.Status.DIBAYAR,
            Pengajuan.Status.ACKNOWLEDGED_AOCH,
            Pengajuan.Status.PAS_TERBIT,
            Pengajuan.Status.SIAP_DILAKSANAKAN,
            Pengajuan.Status.DILAKSANAKAN,
            Pengajuan.Status.SELESAI,
        ]
    ).select_related("layanan", "pemohon")
    return render(request, "pas/aoch_list.html", {"pengajuan": query})


@login_required
def aoch_acknowledge(request, pk):
    if not _is_aoch(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(Pengajuan, pk=pk)
    if pengajuan.status == Pengajuan.Status.DIBAYAR:
        _set_status(pengajuan, Pengajuan.Status.ACKNOWLEDGED_AOCH, request.user)
        notify_role(
            "OPERASI",
            "AOCH mengakui pengajuan",
            f"Pengajuan {pengajuan.nomor_pengajuan} telah diakui AOCH.",
            url=f"/pas/operasi/{pk}/",
            pengajuan=pengajuan,
        )
        log_action(request, "ACKNOWLEDGE_AOCH", "Pengajuan", pk)
        messages.success(request, "Pengajuan telah diakui (acknowledged).")
    return redirect("pas:aoch_list")
