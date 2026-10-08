import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.templatetags.rupiah import format_rupiah
from audit.models import log_action
from notifikasi.services import notify_pemohon, notify_role
from pembayaran.models import Invoice, PaymentTransaction
from pembayaran.views import get_or_create_invoice

from .forms import DaftarHitamForm, LayananForm, PengajuanForm
from .models import (
    DaftarHitam,
    DokumenPendamping,
    Layanan,
    Pengajuan,
    SerahTerimaPAS,
)
from .services import (
    BATASAN_AREA,
    berkas_pendamping_kadang,
    buang_berkas_pendamping_lama,
    cek_blacklist_form,
    cek_blacklist_nama,
    cek_blacklist_nik,
    daftar_berkas_pendamping,
    kumpulkan_pendamping,
    normalisasi_nik,
    pesan_blacklist,
    set_status,
    simpan_berkas_pendamping,
    simpan_pendamping,
    bersihkan_berkas_pendamping,
)

logger = logging.getLogger(__name__)

# Alur baru: Diajukan → Menunggu Pembayaran → Dibayar → Menunggu Operasi → PAS Terbit
TIMELINE = [
    ("DRAFT", "Draft"),
    ("DIAJUKAN", "Diajukan"),
    ("MENUNGGU_PEMBAYARAN", "Menunggu Pembayaran"),
    ("BUKTI_TERUNGGAH", "Bukti Bayar Sudah Diunggah"),
    ("DIBAYAR", "Sudah Dibayar"),
    ("MENUNGGU_OPERASI", "Menunggu Operasi"),
    ("PAS_TERBIT", "PAS Diterbitkan"),
    ("SELESAI", "Selesai"),
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
    return _has_role(user, "KOMERSIL", "OPERASI", "AOCH", "AVSEC")


def _set_status(pengajuan, status, user, catatan=""):
    """Kompatibel dengan kode lama — delegasi ke services.set_status."""
    return set_status(pengajuan, status, user, catatan)


def _blacklist_hit(nama, instansi):
    return cek_blacklist_nama(nama, instansi)


def _normalisasi_hp(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _kontak_cocok(pengajuan, kontak):
    """Cocokkan kontak yang diisi dengan data pemohon pengajuan."""
    kontak = (kontak or "").strip().lower()
    if not kontak:
        return False
    kandidat = [pengajuan.pemohon_email, pengajuan.pemohon_no_hp]
    if pengajuan.pemohon_id:
        kandidat += [
            pengajuan.pemohon.email,
            pengajuan.pemohon.phone,
            pengajuan.pemohon.username,
        ]
    kandidat = [k for k in kandidat if k]
    if any(str(k).strip().lower() == kontak for k in kandidat):
        return True
    kontak_digit = _normalisasi_hp(kontak)
    if not kontak_digit:
        return False
    return any(kontak_digit == _normalisasi_hp(k) for k in kandidat)


def _ajukan_ke_pembayaran(pengajuan, request):
    """Setelah lolos pengecekan NIK daftar hitam, langsung arahkan ke pembayaran."""
    user = request.user if request.user.is_authenticated else None
    _set_status(pengajuan, Pengajuan.Status.MENUNGGU_PEMBAYARAN, user)
    invoice = get_or_create_invoice(pengajuan)
    notify_pemohon(
        pengajuan,
        "Pengajuan diterima",
        f"Pengajuan {pengajuan.nomor_pengajuan} lolos pengecekan identitas. "
        f"Total pembayaran Rp{format_rupiah(pengajuan.total)}. "
        "Silakan lakukan pembayaran agar pengajuan diproses.",
        url=f"/pembayaran/invoice/{invoice.pk}/",
    )
    log_action(request, "AJUKAN_PENGAJUAN", "Pengajuan", pengajuan.pk)
    return invoice


def _identitas_hitam(pengajuan):
    """Cek ulang NIK seluruh pendamping + NIK PIC terhadap daftar hitam."""
    niks = list(
        pengajuan.pendamping.values_list("nik", flat=True)
    )
    niks.append(pengajuan.pic_nomor_identitas)
    return cek_blacklist_nik(niks)


def _build_timeline(current_status, history=None, label_current=None):
    """Susun daftar langkah proses; `label_current` mengganti judul langkah
    yang sedang berjalan (mis. tahap pembayaran yang sudah ada bukti bayar)."""
    history = set(history or [])
    codes = [code for code, _ in TIMELINE]
    if current_status in codes:
        history.add(current_status)
    last_index = max(
        (codes.index(code) for code in history if code in codes), default=-1
    )
    items = []
    for i, (code, label) in enumerate(TIMELINE):
        if current_status == code:
            state = "current"
            if label_current:
                label = label_current
        elif i <= last_index:
            state = "done"
        else:
            state = "todo"
        items.append({"code": code, "label": label, "state": state})
    if current_status not in codes:
        try:
            label = Pengajuan.Status(current_status).label
        except ValueError:
            label = current_status
        items.append(
            {
                "code": current_status,
                "label": label,
                "state": "rejected"
                if current_status in ("DITOLAK_OPERASI", "DIBATALKAN")
                else "current",
            }
        )
    return items


def _catatan_terakhir(pengajuan):
    """Catatan pada riwayat status terakhir yang diisi (untuk penolakan/revisi)."""
    riwayat = (
        pengajuan.riwayat_status.exclude(catatan="")
        .order_by("-created_at")
        .first()
    )
    return riwayat.catatan if riwayat else ""


# ---------- Pemohon ----------

@login_required
def daftar_pengajuan(request):
    query = Pengajuan.objects.select_related("layanan", "pemohon")
    if not _is_petugas(request.user):
        query = query.filter(pemohon=request.user)
    return render(request, "pas/daftar_pengajuan.html", {"pengajuan": query})


def _jumlah_pendamping(post):
    try:
        return max(int(post.get("jumlah_pendamping") or 0), 0)
    except (TypeError, ValueError):
        return 0


def _konteks_pendamping(request, jumlah=None):
    """Data pendamping dari POST + berkas tersimpan, agar form tidak kosong
    saat dirender ulang (mis. NIK terkena daftar hitam)."""
    post = request.POST or {}
    if jumlah is None:
        jumlah = _jumlah_pendamping(post)
    return {
        "pendamping_names": [
            (post.get(f"pendamping_nama_{i}") or "").strip()
            for i in range(1, jumlah + 1)
        ],
        "pendamping_niks": [
            (post.get(f"pendamping_nik_{i}") or "").strip()
            for i in range(1, jumlah + 1)
        ],
        "pendamping_files": daftar_berkas_pendamping(request),
    }


def _pesan_error_form(form):
    """Pesan kesalahan form + daftar kolom isian yang perlu diperbaiki."""
    pesan = []
    fokus = []
    for field, msgs in form.errors.items():
        label = form[field].label if field in form.fields else ""
        for m in msgs:
            pesan.append(f"{label}: {m}" if label else str(m))
        if field in form.fields:
            fokus.append(field)
    return pesan, fokus


def _isi_form_konteks(form, user, **extra):
    layanan = Layanan.objects.filter(aktif=True).order_by("lokasi", "nama_layanan")
    konteks = {
        "form": form,
        "pendamping_names": extra.get("pendamping_names", []),
        "pendamping_niks": extra.get("pendamping_niks", []),
        "pendamping_files": extra.get("pendamping_files", {}),
        "fokus_field": extra.get("fokus_field", []),
        "publik": user is None,
        "form_errors": extra.get("form_errors", []),
        "layanan_departure": list(layanan.filter(lokasi=Layanan.Lokasi.DEPARTURE)),
        "layanan_arrival": list(layanan.filter(lokasi=Layanan.Lokasi.ARRIVAL)),
    }
    if "pengajuan" in extra:
        konteks["pengajuan"] = extra["pengajuan"]
    return konteks


def buat_pengajuan(request):
    """Form pengajuan publik — Pemohon tidak perlu login.

    Langkah 1: pemberitahuan batasan area PAS visitor (Departure & Arrival).
    Langkah 2: formulir; saat dikirim NIK dicek ke daftar hitam, jika lolos
    langsung diarahkan ke pembayaran.
    """
    user = request.user if request.user.is_authenticated else None

    if request.method == "POST" and request.POST.get("aksi") == "paham-batasan":
        return redirect(reverse("pas:buat_pengajuan") + "?langkah=form")

    if request.method == "POST":
        jumlah = _jumlah_pendamping(request.POST)
        # Simpan unggahan identitas sementara: browser tidak mengirim ulang
        # berkas saat form dirender kembali (mis. NIK kena daftar hitam).
        simpan_berkas_pendamping(request, jumlah)
        form = PengajuanForm(request.POST, user=user)
        if form.is_valid():
            jumlah = form.cleaned_data.get("jumlah_pendamping") or jumlah
            data, errors = kumpulkan_pendamping(
                request.POST,
                request.FILES,
                jumlah,
                berkas_pendamping_kadang(request, jumlah),
            )
            pukul = cek_blacklist_form(request.POST, jumlah)
            fokus_field = []
            if pukul:
                pesan, fokus_field = pesan_blacklist(pukul)
                errors.extend(pesan)
                daftar = ", ".join(sorted({item["nik"] for item in pukul}))
                log_action(
                    request,
                    "TOLAK_BLACKLIST_NIK",
                    "Pengajuan",
                    "",
                    new_value=daftar,
                )
            if errors:
                return render(
                    request,
                    "pas/buat_pengajuan.html",
                    _isi_form_konteks(
                        form,
                        user,
                        form_errors=errors,
                        fokus_field=fokus_field,
                        **_konteks_pendamping(request, jumlah),
                    ),
                )

            pengajuan = form.save(commit=False)
            pengajuan.pemohon = user
            # "Data Pemohon" sudah menjadi PIC penanggung jawab langsung
            pengajuan.pemohon_nama = pengajuan.pic_nama
            pengajuan.pemohon_no_hp = pengajuan.pic_no_hp
            pengajuan.pemohon_email = pengajuan.pic_email or ""
            if user is not None:
                pengajuan.pemohon_instansi = user.instansi or pengajuan.pemohon_instansi
            pengajuan.status = Pengajuan.Status.DRAFT
            pengajuan.simpan_snapshot_tarif()
            errors = []
            try:
                for percobaan in range(5):
                    try:
                        with transaction.atomic():
                            pengajuan.nomor_pengajuan = pengajuan._generate_nomor()
                            pengajuan.save()
                            simpan_pendamping(pengajuan, data)
                        break
                    except IntegrityError:
                        if percobaan == 4:
                            raise
            except OSError:
                logger.exception("Gagal menyimpan dokumen pendamping pengajuan")
                messages.error(
                    request,
                    "Gagal mengunggah dokumen pendamping. Silakan coba lagi.",
                )
            else:
                if errors:
                    for e in errors:
                        messages.error(request, e)
                else:
                    bersihkan_berkas_pendamping(request)
                    invoice = _ajukan_ke_pembayaran(pengajuan, request)
                    request.session["sukses_pengajuan"] = pengajuan.pk
                    ids = request.session.get("lacak_pengajuan", [])
                    if pengajuan.pk not in ids:
                        ids.append(pengajuan.pk)
                    request.session["lacak_pengajuan"] = ids[-20:]
                    messages.success(
                        request,
                        "Pengajuan lolos pengecekan identitas. Silakan lakukan pembayaran.",
                    )
                    return redirect("pembayaran:bayar", invoice_id=invoice.pk)
        else:
            pesan, fokus_field = _pesan_error_form(form)
            return render(
                request,
                "pas/buat_pengajuan.html",
                _isi_form_konteks(
                    form,
                    user,
                    form_errors=pesan,
                    fokus_field=fokus_field,
                    **_konteks_pendamping(request, jumlah),
                ),
            )
    else:
        if request.GET.get("langkah") != "form":
            return render(
                request,
                "pas/batasan_area.html",
                {"batasan_area": BATASAN_AREA, "publik": user is None},
            )
        buang_berkas_pendamping_lama()
        initial = {}
        if user is not None:
            initial = {
                "pic_nama": user.nama_lengkap,
                "pic_jabatan": user.jabatan,
                "pic_nomor_identitas": user.nomor_identitas,
                "pic_no_hp": user.phone,
                "pic_email": user.email,
            }
        if not initial.get("layanan"):
            initial["layanan"] = (
                Layanan.objects.filter(aktif=True)
                .order_by("lokasi", "nama_layanan")
                .values_list("pk", flat=True)
                .first()
            )
        form = PengajuanForm(user=user, initial=initial)

    return render(
        request,
        "pas/buat_pengajuan.html",
        _isi_form_konteks(form, user, **_konteks_pendamping(request)),
    )


@login_required
def edit_pengajuan(request, pk):
    pengajuan = get_object_or_404(Pengajuan, pk=pk, pemohon=request.user)
    if pengajuan.status not in (Pengajuan.Status.DRAFT, Pengajuan.Status.REVISI_PEMOHON):
        messages.error(request, "Pengajuan tidak dapat diubah pada status ini.")
        return redirect("pas:detail_pengajuan", pk=pk)
    if request.method == "POST":
        jumlah = _jumlah_pendamping(request.POST)
        simpan_berkas_pendamping(request, jumlah)
        form = PengajuanForm(request.POST, instance=pengajuan, user=request.user)
        if form.is_valid():
            jumlah = form.cleaned_data.get("jumlah_pendamping") or jumlah
            data, errors = kumpulkan_pendamping(
                request.POST,
                request.FILES,
                jumlah,
                berkas_pendamping_kadang(request, jumlah),
            )
            pukul = cek_blacklist_form(request.POST, jumlah)
            fokus_field = []
            if pukul:
                pesan, fokus_field = pesan_blacklist(pukul)
                errors.extend(pesan)
            if errors:
                return render(
                    request,
                    "pas/buat_pengajuan.html",
                    _isi_form_konteks(
                        form,
                        request.user,
                        pengajuan=pengajuan,
                        form_errors=errors,
                        fokus_field=fokus_field,
                        **_konteks_pendamping(request, jumlah),
                    ),
                )
            pengajuan = form.save(commit=False)
            pengajuan.pemohon_nama = pengajuan.pic_nama
            pengajuan.pemohon_no_hp = pengajuan.pic_no_hp
            pengajuan.pemohon_email = pengajuan.pic_email or ""
            pengajuan.simpan_snapshot_tarif()
            pengajuan.save()
            simpan_pendamping(pengajuan, data)
            bersihkan_berkas_pendamping(request)
            log_action(request, "EDIT_PENGAJUAN", "Pengajuan", pengajuan.pk)
            messages.success(request, "Pengajuan diperbarui.")
            return redirect("pas:detail_pengajuan", pk=pengajuan.pk)
        else:
            pesan, fokus_field = _pesan_error_form(form)
            return render(
                request,
                "pas/buat_pengajuan.html",
                _isi_form_konteks(
                    form,
                    request.user,
                    pengajuan=pengajuan,
                    form_errors=pesan,
                    fokus_field=fokus_field,
                    **_konteks_pendamping(request, jumlah),
                ),
            )
    else:
        form = PengajuanForm(instance=pengajuan, user=request.user)
    konteks = {
        "pendamping_names": list(pengajuan.pendamping.values_list("nama", flat=True)),
        "pendamping_niks": list(pengajuan.pendamping.values_list("nik", flat=True)),
        "pendamping_files": daftar_berkas_pendamping(request),
    }
    if request.method == "POST":
        konteks = _konteks_pendamping(request)
    return render(
        request,
        "pas/buat_pengajuan.html",
        _isi_form_konteks(
            form,
            request.user,
            pengajuan=pengajuan,
            **konteks,
        ),
    )


@login_required
def detail_pengajuan(request, pk):
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    boleh_akses = _is_petugas(request.user) or (
        request.user.is_authenticated and pengajuan.pemohon_id == request.user.id
    )
    if not boleh_akses:
        if pk in request.session.get("lacak_pengajuan", []):
            return redirect("pas:lacak_detail", pk=pk)
        if not request.user.is_authenticated:
            messages.info(
                request,
                "Masukkan NIK PIC atau nomor pengajuan untuk melihat status pengajuan.",
            )
            return redirect("pas:lacak_pengajuan")
        return redirect("pas:daftar_pengajuan")

    pendamping = pengajuan.pendamping.all()
    invoice = Invoice.objects.filter(pengajuan=pengajuan).first()
    # Bukti sudah diunggah pemohon, tinggal menunggu keputusan Komersil
    bukti_terunggah = invoice.transaksi_menunggu_verifikasi if invoice else None
    # Transaksi sudah dibuat tetapi bukti belum diunggah
    belum_bukti = invoice.transaksi_menunggu_bukti if invoice else None
    timeline = _build_timeline(
        pengajuan.status,
        pengajuan.riwayat_status.values_list("status", flat=True),
        label_current="Bukti Bayar Sudah Diunggah" if bukti_terunggah else None,
    )

    return render(
        request,
        "pas/detail_pengajuan.html",
        {
            "pengajuan": pengajuan,
            "pendamping": pendamping,
            "timeline": timeline,
            "invoice": invoice,
            "bukti_terunggah": bukti_terunggah,
            "belum_bukti": belum_bukti,
            "catatan_terakhir": _catatan_terakhir(pengajuan),
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
            f"Lengkapi nama, NIK & dokumen identitas {pengajuan.jumlah_pendamping} "
            "pendamping sebelum mengajukan.",
        )
        return redirect("pas:edit_pengajuan", pk=pk)

    hits = _identitas_hitam(pengajuan)
    nama_hit = _blacklist_hit(pengajuan.nama_pemohon, pengajuan.instansi_pemohon)
    if nama_hit:
        hits.append(nama_hit)
    if hits:
        daftar = ", ".join(
            sorted({normalisasi_nik(h.nik) or h.nama for h in hits})
        )
        messages.error(
            request,
            f"Ada identitas yang terdaftar dalam daftar hitam ({daftar}). "
            "Pengajuan tidak dapat dikirim.",
        )
        log_action(request, "TOLAK_BLACKLIST_NIK", "Pengajuan", pk, new_value=daftar)
        return redirect("pas:edit_pengajuan", pk=pk)

    invoice = _ajukan_ke_pembayaran(pengajuan, request)
    ids = request.session.get("lacak_pengajuan", [])
    if pengajuan.pk not in ids:
        ids.append(pengajuan.pk)
    request.session["lacak_pengajuan"] = ids[-20:]
    messages.success(
        request, "Pengajuan lolos pengecekan identitas. Silakan lakukan pembayaran."
    )
    return redirect("pembayaran:bayar", invoice_id=invoice.pk)


def pengajuan_sukses(request):
    """Halaman sukses setelah pemohon publik mengirim pengajuan."""
    pk = request.session.get("sukses_pengajuan")
    pengajuan = Pengajuan.objects.select_related("layanan").filter(pk=pk).first() if pk else None
    return render(request, "pas/pengajuan_sukses.html", {"pengajuan": pengajuan})


def lacak_pengajuan(request):
    """Lacak status pengajuan tanpa akun.

    Pencarian memakai satu isian tunggal: NIK KTP pemohon/PIC, NPWP PIC,
    nomor request pengajuan, atau No HP pemohon. Hanya menampilkan pengajuan
    yang tanggal pelaksanaannya belum lampau, supaya daftar hasil tidak rancu.
    """
    hasil = []
    dicari = False
    kata_kunci = ""
    error = ""
    if request.method == "POST":
        kata_kunci = (request.POST.get("kata_kunci") or "").strip()
        if not kata_kunci:
            error = "Isi NIK KTP, NPWP, No Req, atau No HP pemohon terlebih dahulu."
        else:
            dicari = True
            dk = "".join(c for c in kata_kunci if c.isdigit())
            query = (
                Q(nomor_pengajuan__iexact=kata_kunci)
                | Q(pic_nomor_identitas__iexact=kata_kunci)
                | Q(pic_npwp__iexact=kata_kunci)
                | Q(pemohon_no_hp__iexact=kata_kunci)
                | Q(pic_no_hp__iexact=kata_kunci)
            )
            if dk:
                query |= (
                    Q(nomor_pengajuan__icontains=dk)
                    | Q(pemohon_no_hp__icontains=dk)
                    | Q(pic_no_hp__icontains=dk)
                    | Q(pic_nomor_identitas__icontains=dk)
                    | Q(pic_npwp__icontains=dk)
                )
            hasil = list(
                Pengajuan.objects.select_related("layanan")
                .filter(tanggal_pelaksanaan__gte=timezone.localdate())
                .filter(query)
                .order_by("tanggal_pelaksanaan", "-created_at")
            )
            ids = request.session.get("lacak_pengajuan", [])
            for p in hasil:
                if p.pk not in ids:
                    ids.append(p.pk)
            request.session["lacak_pengajuan"] = ids[-20:]
    return render(
        request,
        "pas/lacak.html",
        {
            "hasil": hasil,
            "dicari": dicari,
            "kata_kunci": kata_kunci,
            "error": error,
        },
    )


def lacak_detail(request, pk):
    if pk not in request.session.get("lacak_pengajuan", []):
        messages.info(request, "Masukkan NIK KTP, NPWP, No Req, atau No HP pemohon untuk melihat status.")
        return redirect("pas:lacak_pengajuan")
    pengajuan = get_object_or_404(Pengajuan.objects.select_related("layanan"), pk=pk)
    invoice = Invoice.objects.filter(pengajuan=pengajuan).first()
    menunggu_verifikasi = invoice.transaksi_menunggu_verifikasi if invoice else None
    return render(
        request,
        "pas/lacak_detail.html",
        {
            "pengajuan": pengajuan,
            "timeline": _build_timeline(
                pengajuan.status,
                pengajuan.riwayat_status.values_list("status", flat=True),
                label_current=(
                    "Bukti Bayar Sudah Diunggah" if menunggu_verifikasi else None
                ),
            ),
            "catatan_terakhir": _catatan_terakhir(pengajuan),
            "invoice": invoice,
            "menunggu_bukti": invoice.transaksi_menunggu_bukti if invoice else None,
            "menunggu_verifikasi": menunggu_verifikasi,
        },
    )


# ---------- Komersil ----------

@login_required
def verifikasi_list(request):
    """Antrean Komersil: validasi bukti bayar & penerusan ke Operasi."""
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    query = Pengajuan.objects.filter(
        status__in=[
            Pengajuan.Status.DIBAYAR,
            Pengajuan.Status.MENUNGGU_OPERASI,
        ]
    ).select_related("layanan", "pemohon").prefetch_related("pendamping")
    bukti_bayar = (
        PaymentTransaction.objects.filter(
            status=PaymentTransaction.Status.PENDING,
            manual__isnull=False,
        )
        .select_related("invoice__pengajuan__pemohon", "payment_method")
        .order_by("-created_at")
    )
    return render(
        request,
        "pas/verifikasi_list.html",
        {"pengajuan": query, "bukti_bayar": bukti_bayar},
    )


@login_required
@require_POST
def lanjutkan_operasi(request, pk):
    """Komersil: bukti bayar sudah valid -> teruskan pengajuan ke Operasi."""
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    if pengajuan.status != Pengajuan.Status.DIBAYAR:
        messages.error(request, "Hanya pengajuan berstatus Sudah Dibayar yang bisa diteruskan.")
        return redirect("pas:verifikasi_list")

    invoice = Invoice.objects.filter(pengajuan=pengajuan).first()
    lunas = invoice is not None and invoice.status == Invoice.Status.PAID
    if not lunas:
        transaksi_bayar = PaymentTransaction.objects.filter(
            invoice__pengajuan=pengajuan, status=PaymentTransaction.Status.PAID
        ).exists()
        lunas = transaksi_bayar
    if not lunas:
        messages.error(
            request,
            "Pembayaran belum tervalidasi. Validasi bukti bayar terlebih dahulu "
            "sebelum diteruskan ke Operasi.",
        )
        return redirect("pas:verifikasi_list")

    _set_status(pengajuan, Pengajuan.Status.MENUNGGU_OPERASI, request.user)
    notify_pemohon(
        pengajuan,
        "Pembayaran terverifikasi",
        f"Pembayaran pengajuan {pengajuan.nomor_pengajuan} terverifikasi dan "
        "telah diteruskan ke Operasi untuk penerbitan PAS.",
        url=f"/pas/lacak/{pk}/",
    )
    notify_role(
        "OPERASI",
        "Siap terbitkan PAS",
        f"Pengajuan {pengajuan.nomor_pengajuan} sudah dibayar & menunggu "
        "pengecekan ulang daftar hitam serta penerbitan PAS.",
        url=f"/pas/operasi/{pk}/",
        pengajuan=pengajuan,
    )
    log_action(request, "LANJUT_KE_OPERASI", "Pengajuan", pk)
    messages.success(request, "Pengajuan diteruskan ke Operasi.")
    return redirect("pas:verifikasi_list")


@login_required
def verifikasi_dokumen(request, pk):
    """Review dokumen identitas pendamping (tidak mengubah alur pembayaran)."""
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    pendamping = pengajuan.pendamping.all()

    if request.method == "POST":
        for pd in pendamping:
            f_status = f"pd_status_{pd.pk}"
            if f_status in request.POST:
                pd.status_verifikasi = request.POST[f_status]
                pd.verified_by = request.user
                pd.verified_at = timezone.now()
                pd.save()
        log_action(request, "VERIFIKASI_DOKUMEN", "Pengajuan", pk)
        messages.success(request, "Status dokumen pendamping diperbarui.")
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
            Pengajuan.Status.BUKTI_TERUNGGAH,
            Pengajuan.Status.DIBAYAR,
            Pengajuan.Status.PAS_TERBIT,
            Pengajuan.Status.ACKNOWLEDGED_AOCH,
            Pengajuan.Status.DILAKSANAKAN,
        ]
    ).select_related("layanan", "pemohon").prefetch_related("pendamping")
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
            notify_pemohon(
                pengajuan,
                "Pengajuan ditolak Operasi",
                f"Alasan: {alasan}",
                url=f"/pas/lacak/{pk}/",
            )
            log_action(request, "TOLAK_OPERASI", "Pengajuan", pk, new_value=alasan)
            messages.warning(request, "Pengajuan ditolak.")
            return redirect("pas:operasi_list")
        return redirect("pas:operasi_proses", pk=pk)

    # Pengecekan ulang NIK & nama terhadap daftar hitam (notif dari Komersil)
    hitam = _identitas_hitam(pengajuan)
    nama_hit = _blacklist_hit(pengajuan.nama_pemohon, pengajuan.instansi_pemohon)
    if nama_hit and nama_hit not in hitam:
        hitam.append(nama_hit)
    invoice = Invoice.objects.filter(pengajuan=pengajuan).first()
    return render(
        request,
        "pas/operasi_proses.html",
        {
            "pengajuan": pengajuan,
            "pendamping": pendamping,
            "hitam": hitam,
            "invoice": invoice,
            "catatan_terakhir": _catatan_terakhir(pengajuan),
        },
    )


@login_required
def terbitkan_pas(request, pk):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    if request.method == "POST" and pengajuan.status in (
        Pengajuan.Status.MENUNGGU_OPERASI,
        Pengajuan.Status.DIBAYAR,
        Pengajuan.Status.ACKNOWLEDGED_AOCH,
    ):
        # Cek ulang NIK & nama sebelum PAS diterbitkan
        hitam = _identitas_hitam(pengajuan)
        nama_hit = _blacklist_hit(pengajuan.nama_pemohon, pengajuan.instansi_pemohon)
        if nama_hit and nama_hit not in hitam:
            hitam.append(nama_hit)
        if hitam:
            alasan = "; ".join(
                f"{normalisasi_nik(h.nik) or h.nama} — {h.nama}: {h.alasan}".strip()
                for h in hitam
            )
            _set_status(
                pengajuan,
                Pengajuan.Status.DITOLAK_OPERASI,
                request.user,
                catatan=alasan,
            )
            notify_pemohon(
                pengajuan,
                "PAS tidak diterbitkan",
                f"Identitas terdaftar dalam daftar hitam: {alasan}",
                url=f"/pas/lacak/{pk}/",
            )
            log_action(
                request,
                "TOLAK_BLACKLIST",
                "Pengajuan",
                pk,
                new_value=", ".join(normalisasi_nik(h.nik) or h.nama for h in hitam),
            )
            messages.error(
                request,
                "PAS tidak diterbitkan — ada identitas dalam daftar hitam. "
                "Hubungi Operasi bila data perlu dikoreksi.",
            )
            return redirect("pas:operasi_proses", pk=pk)

        pengajuan.tanggal_berlaku_pas = pengajuan.tanggal_pelaksanaan
        pengajuan.save(update_fields=["tanggal_berlaku_pas", "updated_at"])
        _set_status(pengajuan, Pengajuan.Status.PAS_TERBIT, request.user)
        notify_pemohon(
            pengajuan,
            "PAS diterbitkan",
            f"PAS untuk pengajuan {pengajuan.nomor_pengajuan} telah diterbitkan dan "
            f"berlaku pada {pengajuan.tanggal_berlaku_pas:%d-%m-%Y} (satu hari). "
            "Penyerahan fisiknya dicatat oleh petugas AOCH.",
            url=f"/pas/lacak/{pk}/",
        )
        notify_role(
            "AOCH",
            "PAS diterbitkan — siap diserahkan",
            f"PAS untuk pengajuan {pengajuan.nomor_pengajuan} telah diterbitkan oleh "
            "Operasi. Silakan input nomor PAS visitor dan catat penyerahan fisiknya.",
            url=f"/pas/aoch/{pk}/proses/",
            pengajuan=pengajuan,
        )
        notify_role(
            "KOMERSIL",
            "PAS diterbitkan",
            f"PAS pengajuan {pengajuan.nomor_pengajuan} terbit, berlaku satu hari "
            f"pada {pengajuan.tanggal_berlaku_pas:%d-%m-%Y}.",
            url=f"/pas/pengajuan/{pk}/",
            pengajuan=pengajuan,
        )
        notify_role(
            "OPERASI",
            "PAS diterbitkan",
            f"PAS pengajuan {pengajuan.nomor_pengajuan} terbit, berlaku satu hari "
            f"pada {pengajuan.tanggal_berlaku_pas:%d-%m-%Y}.",
            url=f"/pas/pengajuan/{pk}/",
            pengajuan=pengajuan,
        )
        log_action(request, "TERBITKAN_PAS", "Pengajuan", pk)
        messages.success(
            request,
            f"PAS diterbitkan, berlaku {pengajuan.tanggal_berlaku_pas:%d-%m-%Y} "
            "(satu hari). AOCH diinformasikan untuk input nomor PAS dan mencatat "
            "penyerahan fisik.",
        )
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
            notify_pemohon(
                pengajuan,
                "Layanan selesai",
                f"Layanan {pengajuan.layanan.nama_layanan} telah selesai dilaksanakan.",
                url=f"/pas/lacak/{pk}/",
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
            Pengajuan.Status.MENUNGGU_OPERASI,
            Pengajuan.Status.DIBAYAR,
            Pengajuan.Status.ACKNOWLEDGED_AOCH,
            Pengajuan.Status.PAS_TERBIT,
            Pengajuan.Status.SIAP_DILAKSANAKAN,
            Pengajuan.Status.DILAKSANAKAN,
            Pengajuan.Status.SELESAI,
        ]
    ).select_related("layanan", "pemohon").prefetch_related(
        "pendamping", "serah_terima"
    )
    return render(request, "pas/aoch_list.html", {"pengajuan": query})


def _data_url_ke_file(data_url, prefix):
    """Ubah data URL (gambar PNG/JPEG) menjadi ContentFile untuk disimpan."""
    import base64 as _base64

    from django.core.files.base import ContentFile

    if not data_url or "base64," not in data_url:
        return None
    try:
        meta, encoded = data_url.split("base64,", 1)
        raw = _base64.b64decode(encoded)
    except (ValueError, TypeError):
        return None
    ext = "png" if "png" in meta else "jpg"
    return ContentFile(raw, name=f"{prefix}_{timezone.now():%Y%m%d%H%M%S}.{ext}")


def _simpan_ttd(data_url):
    """Ubah tanda tangan elektronik (data URL PNG) menjadi file gambar."""
    return _data_url_ke_file(data_url, "ttd")


def _simpan_foto(data_url):
    """Ubah foto kamera (data URL JPEG/PNG) menjadi file gambar."""
    return _data_url_ke_file(data_url, "foto")


@login_required
def aoch_proses(request, pk):
    """AOCH: input nomor PAS visitor, lalu serahkan & terima kembali fisik PAS
    (foto + tanda tangan elektronik)."""
    if not _is_aoch(request.user):
        return redirect("dashboard:home")
    pengajuan = get_object_or_404(
        Pengajuan.objects.select_related("layanan", "pemohon"), pk=pk
    )
    pendamping = list(pengajuan.pendamping.all())
    serah, _ = SerahTerimaPAS.objects.get_or_create(
        pengajuan=pengajuan,
        defaults={
            "penerima_nama": pengajuan.pic_nama,
            "penerima_nik": pengajuan.pic_nomor_identitas,
            "penerima_jabatan": pengajuan.pic_jabatan,
        },
    )

    if request.method == "POST":
        aksi = request.POST.get("aksi")

        # ---------- Input nomor PAS visitor ----------
        if aksi == "simpan_nomor":
            if pengajuan.status not in (
                Pengajuan.Status.PAS_TERBIT,
                Pengajuan.Status.ACKNOWLEDGED_AOCH,
                Pengajuan.Status.SIAP_DILAKSANAKAN,
                Pengajuan.Status.DILAKSANAKAN,
            ):
                messages.error(
                    request,
                    "PAS belum diterbitkan oleh Operasi — nomor PAS belum bisa disimpan.",
                )
                return redirect("pas:aoch_proses", pk=pk)
            kosong = []
            dipakai = []
            for pd in pendamping:
                nomor = (request.POST.get(f"nomor_pas_{pd.pk}") or "").strip()
                if not nomor:
                    kosong.append(pd.nama)
                    continue
                bentrok = (
                    DokumenPendamping.objects.filter(nomor_pas__iexact=nomor)
                    .exclude(pk=pd.pk)
                    .exclude(pengajuan__status__in=["SELESAI", "DIBATALKAN"])
                    .exclude(pengajuan__serah_terima__status="DIKEMBALIKAN")
                    .exists()
                )
                if bentrok:
                    dipakai.append(f"{nomor} ({pd.nama})")
            if kosong:
                messages.error(
                    request,
                    "Nomor PAS wajib diisi untuk: " + ", ".join(kosong) + ".",
                )
            elif dipakai:
                messages.error(
                    request,
                    "Nomor PAS sudah dipakai pada pendamping lain: "
                    + ", ".join(dipakai) + ".",
                )
            else:
                for pd in pendamping:
                    nomor = (request.POST.get(f"nomor_pas_{pd.pk}") or "").strip()
                    if nomor and nomor != pd.nomor_pas:
                        pd.nomor_pas = nomor
                        pd.save(update_fields=["nomor_pas"])
                log_action(request, "INPUT_NOMOR_PAS", "Pengajuan", pk)
                messages.success(request, "Nomor PAS pendamping tersimpan.")
            return redirect("pas:aoch_proses", pk=pk)

        # ---------- Serahkan fisik PAS ----------
        if aksi == "serahkan":
            if timezone.localdate() < pengajuan.tanggal_pelaksanaan:
                messages.error(
                    request,
                    f"PAS belum bisa diserahkan sebelum tanggal pelaksanaan "
                    f"({pengajuan.tanggal_pelaksanaan:%d-%m-%Y}).",
                )
                return redirect("pas:aoch_proses", pk=pk)
            belum = [pd.nama for pd in pendamping if not pd.nomor_pas]
            if belum:
                messages.error(
                    request,
                    "Nomor PAS belum diinput untuk: " + ", ".join(belum) + ".",
                )
                return redirect("pas:aoch_proses", pk=pk)
            foto = request.FILES.get("foto") or _simpan_foto(
                request.POST.get("foto_data", "")
            )
            ttd = _simpan_ttd(request.POST.get("ttd_data", ""))
            penerima = (request.POST.get("penerima_nama") or "").strip()
            if not foto and not serah.foto_penyerahan:
                messages.error(request, "Foto penyerahan wajib diunggah.")
                return redirect("pas:aoch_proses", pk=pk)
            if ttd is None and not serah.ttd_elektronik:
                messages.error(request, "Tanda tangan elektronik wajib dibuat.")
                return redirect("pas:aoch_proses", pk=pk)
            if not penerima:
                messages.error(request, "Nama penerima (PIC/wakil) wajib diisi.")
                return redirect("pas:aoch_proses", pk=pk)
            serah.status = SerahTerimaPAS.Status.DITERIMA
            serah.penerima_nama = penerima
            serah.penerima_nik = (request.POST.get("penerima_nik") or "").strip()
            serah.penerima_jabatan = (request.POST.get("penerima_jabatan") or "").strip()
            serah.penerima_delegasi = (request.POST.get("penerima_delegasi") or "").strip()
            serah.petugas = request.user
            if foto:
                serah.foto_penyerahan = foto
            if ttd is not None:
                serah.ttd_elektronik = ttd
            serah.tanggal_penyerahan = serah.tanggal_penyerahan or timezone.now()
            serah.catatan = (request.POST.get("catatan") or "").strip()
            serah.save()
            if pengajuan.status == Pengajuan.Status.PAS_TERBIT:
                _set_status(pengajuan, Pengajuan.Status.DILAKSANAKAN, request.user)
            notify_pemohon(
                pengajuan,
                "PAS diserahkan",
                f"PAS pengajuan {pengajuan.nomor_pengajuan} diserahkan kepada "
                f"{penerima} pada {serah.tanggal_penyerahan:%d-%m-%Y %H:%M} WIB "
                "oleh petugas AOCH. PAS berlaku satu hari dan wajib dikembalikan "
                "setelah digunakan.",
                url=f"/pas/lacak/{pk}/",
            )
            log_action(
                request,
                "SERAH_PAS",
                "SerahTerimaPAS",
                serah.pk,
                new_value=penerima,
            )
            messages.success(request, "Penyerahan PAS tercatat.")
            return redirect("pas:aoch_proses", pk=pk)

        # ---------- Terima kembali fisik PAS ----------
        if aksi == "kembalikan":
            if serah.status != SerahTerimaPAS.Status.DITERIMA:
                messages.error(request, "PAS belum diserahkan, tidak bisa dikembalikan.")
                return redirect("pas:aoch_proses", pk=pk)
            foto = request.FILES.get("foto") or _simpan_foto(
                request.POST.get("foto_data", "")
            )
            ttd = _simpan_ttd(request.POST.get("ttd_data", ""))
            if not foto and not serah.foto_pengembalian:
                messages.error(request, "Foto pengembalian wajib diambil lewat kamera atau diunggah.")
                return redirect("pas:aoch_proses", pk=pk)
            if ttd is None and not serah.ttd_pengembalian:
                messages.error(request, "Tanda tangan elektronik pengembalian wajib dibuat.")
                return redirect("pas:aoch_proses", pk=pk)
            serah.status = SerahTerimaPAS.Status.DIKEMBALIKAN
            serah.tanggal_pengembalian = timezone.now()
            serah.petugas = request.user
            if foto:
                serah.foto_pengembalian = foto
            if ttd is not None:
                serah.ttd_pengembalian = ttd
            serah.save()
            notify_pemohon(
                pengajuan,
                "PAS dikembalikan",
                f"PAS pengajuan {pengajuan.nomor_pengajuan} diterima kembali oleh "
                f"petugas AOCH pada {serah.tanggal_pengembalian:%d-%m-%Y %H:%M} WIB.",
                url=f"/pas/lacak/{pk}/",
            )
            log_action(request, "KEMBALI_PAS", "SerahTerimaPAS", serah.pk)
            messages.success(request, "Pengembalian PAS tercatat.")
            return redirect("pas:aoch_proses", pk=pk)

        # ---------- Tandai selesai ----------
        if aksi == "selesai":
            if serah.status == SerahTerimaPAS.Status.DIKEMBALIKAN:
                _set_status(pengajuan, Pengajuan.Status.SELESAI, request.user)
                notify_pemohon(
                    pengajuan,
                    "Layanan selesai",
                    f"Pengajuan {pengajuan.nomor_pengajuan} selesai — PAS telah "
                    "dikembalikan.",
                    url=f"/pas/lacak/{pk}/",
                )
                messages.success(request, "Pengajuan ditandai selesai.")
            return redirect("pas:aoch_proses", pk=pk)

        messages.error(
            request,
            "Aksi tidak dikenali. Muat ulang halaman lalu klik tombol yang tersedia.",
        )
        return redirect("pas:aoch_proses", pk=pk)

    boleh_serah = timezone.localdate() >= pengajuan.tanggal_pelaksanaan
    if boleh_serah:
        alasan_serah_tertutup = ""
    else:
        sisa_hari = (pengajuan.tanggal_pelaksanaan - timezone.localdate()).days
        alasan_serah_tertutup = (
            f"Tidak aktif — tanggal pelaksanaan {pengajuan.tanggal_pelaksanaan:%d-%m-%Y}, "
            f"masih {sisa_hari} hari lagi. Tombol terbuka otomatis mulai tanggal tersebut."
        )
    return render(
        request,
        "pas/aoch_proses.html",
        {
            "pengajuan": pengajuan,
            "pendamping": pendamping,
            "serah": serah,
            "boleh_serah": boleh_serah,
            "alasan_serah_tertutup": alasan_serah_tertutup,
        },
    )


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


# ---------- Master Layanan (Komersil) ----------

@login_required
def layanan_list(request):
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    query = Layanan.objects.all().order_by("lokasi", "nama_layanan")
    return render(
        request,
        "pas/layanan_list.html",
        {
            "layanan": query,
            "departure": query.filter(lokasi=Layanan.Lokasi.DEPARTURE),
            "arrival": query.filter(lokasi=Layanan.Lokasi.ARRIVAL),
        },
    )


@login_required
def layanan_form(request, pk=None):
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    instance = None
    if pk is not None:
        instance = get_object_or_404(Layanan, pk=pk)
    if request.method == "POST":
        form = LayananForm(request.POST, instance=instance)
        if form.is_valid():
            layanan = form.save()
            log_action(
                request,
                "SIMPAN_LAYANAN" if instance is None else "EDIT_LAYANAN",
                "Layanan",
                layanan.pk,
                new_value=layanan.nama_layanan,
            )
            messages.success(
                request,
                "Layanan berhasil ditambahkan."
                if instance is None
                else "Layanan berhasil diperbarui.",
            )
            return redirect("pas:layanan_list")
    else:
        form = LayananForm(instance=instance)
    return render(
        request,
        "pas/layanan_form.html",
        {"form": form, "layanan": instance},
    )


@login_required
@require_POST
def layanan_hapus(request, pk):
    if not _is_komersil(request.user):
        return redirect("dashboard:home")
    layanan = get_object_or_404(Layanan, pk=pk)
    try:
        layanan.delete()
        log_action(request, "HAPUS_LAYANAN", "Layanan", pk, old_value=layanan.nama_layanan)
        messages.success(request, f"Layanan {layanan.nama_layanan} dihapus.")
    except ProtectedError:
        layanan.aktif = False
        layanan.save(update_fields=["aktif", "updated_at"])
        log_action(request, "NONAKTIF_LAYANAN", "Layanan", pk, new_value=layanan.nama_layanan)
        messages.warning(
            request,
            f"Layanan {layanan.nama_layanan} masih dipakai pengajuan, "
            "dinonaktifkan sebagai gantinya.",
        )
    return redirect("pas:layanan_list")


# ---------- Daftar Hitam (Operasi) ----------

@login_required
def hitam_list(request):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    query = DaftarHitam.objects.all()
    return render(request, "pas/hitam_list.html", {"daftar": query})


@login_required
def hitam_form(request, pk=None):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    instance = None
    if pk is not None:
        instance = get_object_or_404(DaftarHitam, pk=pk)
    if request.method == "POST":
        form = DaftarHitamForm(request.POST, instance=instance)
        if form.is_valid():
            entri = form.save()
            log_action(
                request,
                "SIMPAN_DAFTAR_HITAM" if instance is None else "EDIT_DAFTAR_HITAM",
                "DaftarHitam",
                entri.pk,
                new_value=entri.nama,
            )
            messages.success(
                request,
                "Data daftar hitam ditambahkan."
                if instance is None
                else "Data daftar hitam diperbarui.",
            )
            return redirect("pas:hitam_list")
    else:
        form = DaftarHitamForm(instance=instance)
    return render(
        request,
        "pas/hitam_form.html",
        {"form": form, "entri": instance},
    )


@login_required
@require_POST
def hitam_hapus(request, pk):
    if not _is_operasi(request.user):
        return redirect("dashboard:home")
    entri = get_object_or_404(DaftarHitam, pk=pk)
    entri.delete()
    log_action(request, "HAPUS_DAFTAR_HITAM", "DaftarHitam", pk, old_value=entri.nama)
    messages.success(request, f"Entri {entri.nama} dihapus dari daftar hitam.")
    return redirect("pas:hitam_list")


# ---------- Verifikasi PAS (Avsec / dashboard awal) ----------

def verifikasi_pas(request):
    """Menu verifikasi: masukkan nomor request atau nomor PAS visitor
    untuk melihat status Aktif / Kedaluwarsa. Terbuka untuk petugas & publik.
    """
    hasil = None
    query = ""
    if request.method == "POST":
        query = (request.POST.get("nomor") or "").strip()
        pengajuan = Pengajuan.objects.filter(
            Q(nomor_pengajuan__iexact=query)
        ).select_related("layanan").prefetch_related("pendamping", "serah_terima").first()
        if pengajuan is None and query:
            pd = (
                DokumenPendamping.objects.filter(nomor_pas__iexact=query)
                .exclude(pengajuan__status__in=["SELESAI", "DIBATALKAN"])
                .exclude(pengajuan__serah_terima__status="DIKEMBALIKAN")
                .select_related("pengajuan__layanan")
                .prefetch_related("pengajuan__serah_terima")
                .order_by("-pengajuan__tanggal_pelaksanaan", "-pengajuan__id")
                .first()
            )
            if pd is None:
                pd = (
                    DokumenPendamping.objects.filter(nomor_pas__iexact=query)
                    .select_related("pengajuan__layanan")
                    .prefetch_related("pengajuan__serah_terima")
                    .first()
                )
            if pd:
                pengajuan = pd.pengajuan
        if pengajuan:
            try:
                serah = pengajuan.serah_terima
            except SerahTerimaPAS.DoesNotExist:
                serah = None
            hasil = {
                "pengajuan": pengajuan,
                "serah": serah,
                "pendamping": list(pengajuan.pendamping.all()),
                "ditemukan": True,
            }
        else:
            hasil = {"ditemukan": False}
        log_action(request, "VERIFIKASI_PAS", "Pengajuan", pengajuan.pk if pengajuan else "", new_value=query)
    return render(
        request,
        "pas/verifikasi_pas.html",
        {"hasil": hasil, "query": query},
    )

