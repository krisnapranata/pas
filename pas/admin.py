from django.contrib import admin

from .models import (
    DaftarHitam,
    DokumenPendamping,
    Layanan,
    Pengajuan,
    StatusRiwayat,
)


@admin.register(Layanan)
class LayananAdmin(admin.ModelAdmin):
    list_display = (
        "nama_layanan",
        "kode_layanan",
        "jenis_tarif",
        "harga",
        "satuan",
        "minimal_pendamping",
        "maksimal_pendamping",
        "aktif",
    )
    list_filter = ("aktif", "jenis_tarif")
    search_fields = ("nama_layanan", "kode_layanan")
    list_editable = ("harga", "satuan", "aktif")


@admin.register(DaftarHitam)
class DaftarHitamAdmin(admin.ModelAdmin):
    list_display = ("tipe", "nama", "alasan", "aktif")
    list_filter = ("tipe", "aktif")
    list_editable = ("aktif",)
    search_fields = ("nama",)


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
    list_display = ("pengajuan", "urutan", "nama", "status_verifikasi")
    list_filter = ("status_verifikasi",)
    search_fields = ("pengajuan__nomor_pengajuan", "nama")


@admin.register(StatusRiwayat)
class StatusRiwayatAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "status", "oleh", "created_at")
    list_filter = ("status",)
    readonly_fields = [f.name for f in StatusRiwayat._meta.fields]
