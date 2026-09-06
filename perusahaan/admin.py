from django.contrib import admin

from .models import Pemohon, Perusahaan


@admin.register(Perusahaan)
class PerusahaanAdmin(admin.ModelAdmin):
    list_display = ("nama", "nib", "npwp", "pic", "status_aktif")
    search_fields = ("nama", "nib", "npwp", "pic")
    list_filter = ("status_aktif",)


@admin.register(Pemohon)
class PemohonAdmin(admin.ModelAdmin):
    list_display = ("nama_lengkap", "nik", "nomor_hp", "perusahaan", "jabatan")
    search_fields = ("nama_lengkap", "nik", "nomor_hp")
    list_filter = ("perusahaan",)
