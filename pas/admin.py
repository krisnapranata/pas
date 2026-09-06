from django.contrib import admin

from .models import AreaAkses, DokumenPengajuan, JenisPAS, PASCard, PengajuanPAS, Persyaratan, StatusRiwayat, Tarif


class PersyaratanInline(admin.TabularInline):
    model = Persyaratan
    extra = 0


class TarifInline(admin.TabularInline):
    model = Tarif
    extra = 0


@admin.register(JenisPAS)
class JenisPASAdmin(admin.ModelAdmin):
    list_display = ("nama", "kode", "masa_berlaku_hari", "biaya", "butuh_screening", "butuh_approval", "status_aktif")
    list_filter = ("status_aktif", "butuh_screening", "butuh_approval")
    search_fields = ("nama", "kode")
    list_editable = ("biaya", "masa_berlaku_hari", "status_aktif")
    inlines = [PersyaratanInline, TarifInline]


@admin.register(Persyaratan)
class PersyaratanAdmin(admin.ModelAdmin):
    list_display = ("jenis_pas", "nama", "kode", "wajib", "format_file", "max_size", "aktif")
    list_filter = ("jenis_pas", "wajib", "aktif")
    search_fields = ("nama", "kode")


@admin.register(AreaAkses)
class AreaAksesAdmin(admin.ModelAdmin):
    list_display = ("nama", "kode", "status_aktif")
    search_fields = ("nama", "kode")
    list_filter = ("status_aktif",)


@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    list_display = ("nama", "kode", "jenis_pas", "nominal", "status_aktif")
    search_fields = ("nama", "kode")
    list_filter = ("status_aktif", "jenis_pas")


@admin.register(PengajuanPAS)
class PengajuanPASAdmin(admin.ModelAdmin):
    list_display = ("nomor_pengajuan", "pemohon", "jenis_pas", "perusahaan", "status", "created_at")
    list_filter = ("status", "jenis_pas")
    search_fields = ("nomor_pengajuan", "pemohon__username", "pemohon__email")
    readonly_fields = ("nomor_pengajuan", "tanggal_pengajuan", "created_at", "updated_at")


@admin.register(DokumenPengajuan)
class DokumenPengajuanAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "persyaratan", "status_verifikasi", "tanggal_upload")
    list_filter = ("status_verifikasi",)
    search_fields = ("pengajuan__nomor_pengajuan", "nomor_dokumen")


@admin.register(StatusRiwayat)
class StatusRiwayatAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "status", "oleh", "created_at")
    list_filter = ("status",)
    readonly_fields = [f.name for f in StatusRiwayat._meta.fields]


@admin.register(PASCard)
class PASCardAdmin(admin.ModelAdmin):
    list_display = ("nomor_pas", "pengajuan", "jenis_pas", "tanggal_berlaku", "tanggal_expired", "status")
    list_filter = ("status", "jenis_pas")
    search_fields = ("nomor_pas", "pengajuan__nomor_pengajuan", "qr_token")
    readonly_fields = ("qr_token", "nomor_pas")
