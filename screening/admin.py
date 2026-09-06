from django.contrib import admin

from .models import ScreeningBooking, ScreeningResult, ScreeningSchedule


@admin.register(ScreeningSchedule)
class ScreeningScheduleAdmin(admin.ModelAdmin):
    list_display = ("tanggal", "jam_mulai", "jam_selesai", "lokasi", "kuota", "terisi", "sisa", "status")
    list_filter = ("status", "tanggal")
    search_fields = ("lokasi",)
    list_editable = ("kuota", "status")


@admin.register(ScreeningBooking)
class ScreeningBookingAdmin(admin.ModelAdmin):
    list_display = ("nomor_booking", "pengajuan", "jadwal", "nomor_antrian", "status", "waktu_booking")
    list_filter = ("status", "jadwal")
    search_fields = ("nomor_booking", "pengajuan__nomor_pengajuan")


@admin.register(ScreeningResult)
class ScreeningResultAdmin(admin.ModelAdmin):
    list_display = ("booking", "petugas", "hasil", "waktu_screening")
    list_filter = ("hasil",)
    search_fields = ("booking__nomor_booking",)
