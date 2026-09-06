from django.urls import path

from . import views

app_name = "perusahaan"

urlpatterns = [
    path("", views.daftar_perusahaan, name="daftar_perusahaan"),
    path("buat/", views.buat_perusahaan, name="buat_perusahaan"),
    path("<int:pk>/edit/", views.edit_perusahaan, name="edit_perusahaan"),
]
