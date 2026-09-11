from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("statistik/", views.statistik, name="statistik"),
    path("laporan/", views.laporan, name="laporan"),
    path("laporan/pengajuan.csv", views.export_pengajuan_csv, name="export_pengajuan_csv"),
]
