from django.urls import path

from . import views

app_name = "pas"

urlpatterns = [
    path("pengajuan/", views.daftar_pengajuan, name="daftar_pengajuan"),
    path("pengajuan/buat/", views.buat_pengajuan, name="buat_pengajuan"),
    path("pengajuan/sukses/", views.pengajuan_sukses, name="pengajuan_sukses"),
    path("pengajuan/<int:pk>/", views.detail_pengajuan, name="detail_pengajuan"),
    path("lacak/", views.lacak_pengajuan, name="lacak_pengajuan"),
    path("lacak/<int:pk>/", views.lacak_detail, name="lacak_detail"),
    path("pengajuan/<int:pk>/edit/", views.edit_pengajuan, name="edit_pengajuan"),
    path("pengajuan/<int:pk>/submit/", views.submit_pengajuan, name="submit_pengajuan"),
    # Verifikasi avsec (dashboard awal) — nomor request / nomor PAS
    path("verifikasi-pas/", views.verifikasi_pas, name="verifikasi_pas"),
    # Komersil
    path("verifikasi/", views.verifikasi_list, name="verifikasi_list"),
    path("verifikasi/<int:pk>/", views.verifikasi_dokumen, name="verifikasi_dokumen"),
    path(
        "verifikasi/<int:pk>/lanjutkan-operasi/",
        views.lanjutkan_operasi,
        name="lanjutkan_operasi",
    ),
    path("layanan/", views.layanan_list, name="layanan_list"),
    path("layanan/buat/", views.layanan_form, name="layanan_buat"),
    path("layanan/<int:pk>/edit/", views.layanan_form, name="layanan_edit"),
    path("layanan/<int:pk>/hapus/", views.layanan_hapus, name="layanan_hapus"),
    # Operasi
    path("operasi/", views.operasi_list, name="operasi_list"),
    path("operasi/<int:pk>/", views.operasi_proses, name="operasi_proses"),
    path("operasi/<int:pk>/terbitkan/", views.terbitkan_pas, name="terbitkan_pas"),
    path("pelaksanaan/<int:pk>/", views.tandai_pelaksanaan, name="tandai_pelaksanaan"),
    path("daftar-hitam/", views.hitam_list, name="hitam_list"),
    path("daftar-hitam/buat/", views.hitam_form, name="hitam_buat"),
    path("daftar-hitam/<int:pk>/edit/", views.hitam_form, name="hitam_edit"),
    path("daftar-hitam/<int:pk>/hapus/", views.hitam_hapus, name="hitam_hapus"),
    # AOCH (input nomor PAS + serah terima fisik PAS)
    path("aoch/", views.aoch_list, name="aoch_list"),
    path("aoch/<int:pk>/proses/", views.aoch_proses, name="aoch_proses"),
    path("aoch/<int:pk>/ack/", views.aoch_acknowledge, name="aoch_acknowledge"),
]
