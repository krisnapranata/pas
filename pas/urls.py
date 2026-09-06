from django.urls import path

from . import views

app_name = "pas"

urlpatterns = [
    path("pengajuan/", views.daftar_pengajuan, name="daftar_pengajuan"),
    path("pengajuan/buat/", views.buat_pengajuan, name="buat_pengajuan"),
    path("pengajuan/<int:pk>/", views.detail_pengajuan, name="detail_pengajuan"),
    path("pengajuan/<int:pk>/submit/", views.submit_pengajuan, name="submit_pengajuan"),
    path(
        "pengajuan/<int:pk>/upload/<int:persyaratan_id>/",
        views.upload_dokumen,
        name="upload_dokumen",
    ),
    path("verifikasi/<int:pk>/", views.verifikasi_dokumen, name="verifikasi_dokumen"),
    path("jenis/<int:pk>/syarat/", views.detail_jenis_syarat, name="jenis_syarat"),
    path("pas-saya/", views.pas_saya, name="pas_saya"),
    path("pas-saya/cetak/<int:pk>/", views.cetak_pas, name="cetak_pas"),
    path("terbitkan/<int:pengajuan_id>/", views.terbitkan_pas, name="terbitkan_pas"),
    path("terbit/", views.daftar_pas_terbit, name="daftar_pas_terbit"),
    path("terbit/cabut/<int:pk>/", views.cabut_pas, name="cabut_pas"),
    path("verify/<str:token>/", views.verifikasi_qr, name="verifikasi_qr"),
]
