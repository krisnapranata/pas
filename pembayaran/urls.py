from django.urls import path

from . import views

app_name = "pembayaran"

urlpatterns = [
    path("invoice/", views.invoice_saya, name="invoice_saya"),
    path("upload-bukti/", views.cari_bukti, name="cari_bukti"),
    path("invoice/buat/<int:pengajuan_id>/", views.buat_invoice, name="buat_invoice"),
    path("bayar/<int:invoice_id>/", views.bayar, name="bayar"),
    path("transaksi/buat/<int:invoice_id>/", views.buat_transaksi, name="buat_transaksi"),
    path("transaksi/<int:pk>/", views.detail_transaksi, name="detail_transaksi"),
    path("transaksi/<int:pk>/upload/", views.upload_bukti, name="upload_bukti"),
    path("verifikasi/<int:pk>/", views.verifikasi_manual, name="verifikasi_manual"),
    path("dashboard/", views.dashboard_pembayaran, name="dashboard_pembayaran"),
    path("refund/<int:pk>/", views.minta_refund, name="minta_refund"),
    path("webhook/<str:provider>/", views.webhook, name="webhook"),
    path("jenis/", views.jenis_list, name="jenis_list"),
    path("jenis/tambah/", views.jenis_buat, name="jenis_buat"),
    path("jenis/<int:pk>/ubah/", views.jenis_edit, name="jenis_edit"),
    path("jenis/<int:pk>/hapus/", views.jenis_hapus, name="jenis_hapus"),
    path("jenis/<int:pk>/status/", views.jenis_status, name="jenis_status"),
]
