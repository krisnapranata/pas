from django.contrib import admin

from .models import (
    DaftarHitam,
    DokumenPendamping,
    Layanan,
    Pengajuan,
    SerahTerimaPAS,
    StatusRiwayat,
)


@admin.register(Layanan)
class LayananAdmin(admin.ModelAdmin):
    list_display = (
        "nama_layanan",
        "kode_layanan",
        "lokasi",
        "jenis_tarif",
        "harga",
        "satuan",
        "minimal_pendamping",
        "maksimal_pendamping",
        "aktif",
    )
    list_filter = ("aktif", "lokasi", "jenis_tarif")
    search_fields = ("nama_layanan", "kode_layanan")
    list_editable = ("harga", "satuan", "aktif")


@admin.register(DaftarHitam)
class DaftarHitamAdmin(admin.ModelAdmin):
    list_display = ("tipe", "nik", "nama", "alasan", "aktif")
    list_filter = ("tipe", "aktif")
    list_editable = ("aktif",)
    search_fields = ("nama", "nik")


@admin.register(Pengajuan)
class PengajuanAdmin(admin.ModelAdmin):
    list_display = (
        "nomor_pengajuan",
        "pemohon",
        "pic_nama",
        "layanan",
        "jumlah_pendamping",
        "total",
        "status",
        "created_at",
    )
    list_filter = ("status", "layanan")
    search_fields = ("nomor_pengajuan", "pemohon__username", "pic_nama")
    readonly_fields = ("nomor_pengajuan", "created_at", "updated_at")


@admin.register(DokumenPendamping)
class DokumenPendampingAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "urutan", "nama", "nik", "nomor_pas", "status_verifikasi")
    list_filter = ("status_verifikasi",)
    search_fields = ("pengajuan__nomor_pengajuan", "nama", "nik", "nomor_pas")


@admin.register(StatusRiwayat)
class StatusRiwayatAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "status", "oleh", "created_at")
    list_filter = ("status",)
    readonly_fields = [f.name for f in StatusRiwayat._meta.fields]


@admin.register(SerahTerimaPAS)
class SerahTerimaPASAdmin(admin.ModelAdmin):
    list_display = (
        "pengajuan",
        "status",
        "penerima_nama",
        "tanggal_penyerahan",
        "tanggal_pengembalian",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("pengajuan__nomor_pengajuan", "penerima_nama", "penerima_nik")
