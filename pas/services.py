"""Helper bisnis proses PAS — dipakai oleh views, pembayaran, dan dashboard.

Modul ini sengaja hanya bergantung ke `pas.models` + `notifikasi` + `audit`
agar aman di-import dari aplikasi lain tanpa circular import.
"""

import os
import re

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .models import DaftarHitam, DokumenPendamping, Pengajuan, SerahTerimaPAS, StatusRiwayat

# Batasan area PAS visitor (ditampilkan sebelum formulir pengajuan)
BATASAN_AREA = {
    "DEPARTURE": [
        "Area Check-in Counter (domestic & international)",
        "Area Security Check (Avsec) / pemeriksaan barang bawaan",
        "Ruang tunggu penumpang / Boarding Lounge",
        "Area Garbarata / Aerobridge sampai pintu pesawat",
    ],
    "ARRIVAL": [
        "Area kedatangan / pendaratan pesawat",
        "Area imigrasi & bea cukai (untuk penerbangan internasional)",
        "Area pengambilan bagasi (Baggage Claim)",
        "Area Arrival Hall sampai pintu keluar (Meeting Point)",
    ],
}


def set_status(pengajuan, status, user=None, catatan=""):
    """Satu-satunya pintu perubahan status agar riwayat selalu tercatat."""
    pengajuan.status = status
    pengajuan.save(update_fields=["status", "updated_at"])
    StatusRiwayat.objects.create(
        pengajuan=pengajuan, status=status, catatan=catatan, oleh=user
    )
    return pengajuan


def normalisasi_nik(value):
    """Buang spasi/titik/garis agar NIK bisa dibandingkan konsisten."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def cek_blacklist_nik(nik_list):
    """Return daftar entri DaftarHitam aktif yang NIK-nya cocok."""
    targets = {normalisasi_nik(n) for n in nik_list if normalisasi_nik(n)}
    if not targets:
        return []
    hits = []
    for entry in DaftarHitam.objects.filter(aktif=True).exclude(nik="").iterator():
        if normalisasi_nik(entry.nik) in targets:
            hits.append(entry)
    return hits


def niks_dari_post(post, jumlah):
    """[(field, label, nik)] untuk NIK PIC + seluruh pendamping dari data POST.

    `field` adalah nama input di form (dipakai untuk menyorot kolom isian),
    `label` untuk pesan kesalahan ke pengguna.
    """
    hasil = []
    pic_nik = normalisasi_nik(post.get("pic_nomor_identitas"))
    if pic_nik:
        hasil.append(("pic_nomor_identitas", "NIK PIC", pic_nik))
    for i in range(1, int(jumlah or 0) + 1):
        nik = normalisasi_nik(post.get(f"pendamping_nik_{i}"))
        if nik:
            hasil.append((f"pendamping_nik_{i}", f"NIK Pendamping {i}", nik))
    return hasil


def cek_blacklist_form(post, jumlah):
    """Cek NIK PIC & seluruh pendamping (dari data POST) ke daftar hitam.

    Dicek dari data POST mentah, bukan hasil validasi, agar NIK yang kena
    daftar hitam tetap terdeteksi walau berkas identitas belum lengkap.

    Return daftar {field, label, nik, entri} untuk tiap NIK yang terdeteksi.
    """
    kandidat = niks_dari_post(post, jumlah)
    if not kandidat:
        return []
    peta = {}
    for entri in cek_blacklist_nik([nik for _, _, nik in kandidat]):
        peta.setdefault(normalisasi_nik(entri.nik), []).append(entri)
    hasil = []
    for field, label, nik in kandidat:
        for entri in peta.get(nik, []):
            hasil.append(
                {"field": field, "label": label, "nik": nik, "entri": entri}
            )
    return hasil


def pesan_blacklist(pukul):
    """Pesan penolakan + daftar kolom isian yang harus diperbaiki."""
    pesan = []
    fokus = []
    for item in pukul:
        pesan.append(
            f"{item['label']} {item['nik']} atas nama {item['entri'].nama} "
            f"terdaftar dalam daftar hitam — perbaiki {item['label']} pada "
            f"kolom isian yang ditandai merah."
        )
        if item["field"] not in fokus:
            fokus.append(item["field"])
    return pesan, fokus


def cek_blacklist_nama(nama, instansi=""):
    """Cocokkan nama orang (lalu instansi) dengan daftar hitam aktif."""
    nama = (nama or "").strip()
    if nama:
        hit = DaftarHitam.objects.filter(
            aktif=True, tipe=DaftarHitam.Tipe.ORANG, nama__iexact=nama
        ).first()
        if hit:
            return hit
    if instansi:
        return DaftarHitam.objects.filter(
            aktif=True, tipe=DaftarHitam.Tipe.PERUSAHAAN, nama__iexact=instansi.strip()
        ).first()
    return None


def kumpulkan_pendamping(post, files, jumlah, cadangan=None):
    """Validasi & kumpulkan data identitas pendamping dari request.

    `cadangan` adalah {urutan: berkas} dari penyimpanan sementara, dipakai bila
    unggahan tidak dikirim ulang oleh browser (form dirender ulang).

    Return (data, errors). Setiap item data: {urutan, nama, nik, file}.
    """
    cadangan = cadangan or {}
    data = []
    errors = []
    for i in range(1, int(jumlah or 0) + 1):
        nama = (post.get(f"pendamping_nama_{i}") or "").strip()
        nik = normalisasi_nik(post.get(f"pendamping_nik_{i}"))
        upload = files.get(f"pendamping_file_{i}") or cadangan.get(i)
        if not nama:
            errors.append(f"Pendamping {i}: nama wajib diisi.")
            continue
        if not nik:
            errors.append(f"Pendamping {i}: NIK / nomor identitas wajib diisi.")
            continue
        if not upload:
            errors.append(f"Pendamping {i}: dokumen identitas wajib diunggah.")
            continue
        ekstensi = (upload.name or "").rsplit(".", 1)[-1].lower() if "." in (upload.name or "") else ""
        if ekstensi not in ("jpg", "jpeg", "png", "gif", "webp", "pdf"):
            errors.append(
                f"Pendamping {i}: dokumen identitas harus berupa PDF atau gambar."
            )
            continue
        data.append({"urutan": i, "nama": nama, "nik": nik, "file": upload})
    return data, errors


def simpan_pendamping(pengajuan, data):
    """Timpa seluruh daftar pendamping dengan data tervalidasi."""
    pengajuan.pendamping.all().delete()
    for item in data:
        DokumenPendamping.objects.create(
            pengajuan=pengajuan,
            urutan=item["urutan"],
            nama=item["nama"],
            nik=item["nik"],
            file=item["file"],
        )


# ---------- Berkas identitas pendamping (penyimpanan sementara) ----------
# Browser tidak bisa mengirim ulang berkas saat form dirender kembali (mis. NIK
# terkena daftar hitam). Berkas disimpan sementara per sesi agar pengguna cukup
# memperbaiki NIK tanpa harus mengunggah dokumen identitas dari awal.

_TMP_ROOT = "pas/tmp"
_TMP_UMUR_DETIK = 6 * 60 * 60


def _nama_berkas_bersih(nama):
    dasar = os.path.basename(nama or "berkas")
    dasar = re.sub(r"[^A-Za-z0-9._-]", "_", dasar)
    return dasar[:100] or "berkas"


def _dir_berkas(request):
    token = request.session.get("token_berkas_pendamping")
    if not token:
        token = timezone.now().strftime("%Y%m%d%H%M%S%f")
        request.session["token_berkas_pendamping"] = token
    return f"{_TMP_ROOT}/{token}"


def daftar_berkas_pendamping(request):
    """Return {urutan: nama_berkas} milik sesi ini yang masih tersimpan."""
    hasil = {}
    for kunci, info in (request.session.get("berkas_pendamping") or {}).items():
        try:
            urutan = int(kunci)
        except (TypeError, ValueError):
            continue
        if default_storage.exists(info["path"]):
            hasil[urutan] = info["nama"]
    return hasil


def simpan_berkas_pendamping(request, jumlah):
    """Simpan unggahan identitas pendamping yang baru dikirim (bila ada)."""
    if not request.FILES:
        return daftar_berkas_pendamping(request)
    tersimpan = dict(request.session.get("berkas_pendamping") or {})
    for urutan in range(1, int(jumlah or 0) + 1):
        upload = request.FILES.get(f"pendamping_file_{urutan}")
        if not upload:
            continue
        nama = f"{urutan}_{_nama_berkas_bersih(upload.name)}"
        path = default_storage.save(f"{_dir_berkas(request)}/{nama}", upload)
        tersimpan[str(urutan)] = {"path": path, "nama": upload.name}
    request.session["berkas_pendamping"] = tersimpan
    return daftar_berkas_pendamping(request)


def berkas_pendamping_kadang(request, jumlah):
    """Isi cadangan {urutan: berkas} untuk pendamping yang tidak mengunggah ulang."""
    cadangan = {}
    for urutan in range(1, int(jumlah or 0) + 1):
        if request.FILES.get(f"pendamping_file_{urutan}"):
            continue
        info = (request.session.get("berkas_pendamping") or {}).get(str(urutan))
        if not info or not default_storage.exists(info["path"]):
            continue
        with default_storage.open(info["path"]) as handle:
            cadangan[urutan] = ContentFile(handle.read(), name=info["nama"])
    return cadangan


def bersihkan_berkas_pendamping(request):
    """Hapus berkas sementara — dipanggil setelah pengajuan tersimpan."""
    for info in (request.session.get("berkas_pendamping") or {}).values():
        try:
            if default_storage.exists(info["path"]):
                default_storage.delete(info["path"])
        except OSError:
            continue
    request.session.pop("berkas_pendamping", None)


def buang_berkas_pendamping_lama():
    """Bersihkan berkas sementara sesi yang sudah kadaluarsa (kebersihan media)."""
    try:
        _, tokens = default_storage.listdir(_TMP_ROOT)
    except (OSError, NotImplementedError, ValueError):
        return
    batas = timezone.now().timestamp() - _TMP_UMUR_DETIK
    for token in tokens:
        direktori = f"{_TMP_ROOT}/{token}"
        try:
            _, nama_berkas = default_storage.listdir(direktori)
        except (OSError, NotImplementedError, ValueError):
            continue
        for nama in nama_berkas:
            path = f"{direktori}/{nama}"
            try:
                if default_storage.get_modified_time(path).timestamp() < batas:
                    default_storage.delete(path)
            except (OSError, NotImplementedError, ValueError):
                continue
        try:
            os.rmdir(default_storage.path(direktori))
        except (OSError, NotImplementedError, ValueError):
            continue


def ringkasan_masa_berlaku(limit=6):
    """Ringkasan PAS visitor: sudah diberikan, sedang berlaku, masa berlaku habis."""
    today = timezone.localdate()
    terbit = list(
        Pengajuan.objects.filter(tanggal_berlaku_pas__isnull=False)
        .select_related("layanan", "pemohon")
        .prefetch_related("pendamping", "serah_terima")
        .order_by("-tanggal_berlaku_pas", "-created_at")[:200]
    )
    beri, aktif, habis = [], [], []
    for p in terbit:
        try:
            st = p.serah_terima
        except SerahTerimaPAS.DoesNotExist:
            st = None
        if st and st.sudah_diserahkan:
            beri.append((p, st))
        if p.status_masa_berlaku == "AKTIF":
            aktif.append(p)
        elif p.status_masa_berlaku == "KEDALUWARSA":
            habis.append(p)
    return {
        "today": today,
        "diberikan": beri[:limit],
        "aktif": aktif[:limit],
        "kedaluwarsa": habis[:limit],
        "jumlah_diberikan": len(beri),
        "jumlah_aktif": len(aktif),
        "jumlah_kedaluwarsa": len(habis),
    }
