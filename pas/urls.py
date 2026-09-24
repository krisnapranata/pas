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
    path("verifikasi/", views.verifikasi_list, name="verifikasi_list"),
    path("verifikasi/<int:pk>/", views.verifikasi_dokumen, name="verifikasi_dokumen"),
    path("operasi/", views.operasi_list, name="operasi_list"),
    path("operasi/<int:pk>/", views.operasi_proses, name="operasi_proses"),
    path("operasi/<int:pk>/terbitkan/", views.terbitkan_pas, name="terbitkan_pas"),
    path("pelaksanaan/<int:pk>/", views.tandai_pelaksanaan, name="tandai_pelaksanaan"),
    path("aoch/", views.aoch_list, name="aoch_list"),
    path("aoch/<int:pk>/ack/", views.aoch_acknowledge, name="aoch_acknowledge"),
]
