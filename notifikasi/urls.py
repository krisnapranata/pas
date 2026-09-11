from django.urls import path

from . import views

app_name = "notifikasi"

urlpatterns = [
    path("", views.daftar, name="daftar"),
    path("baca/<int:pk>/", views.tandai_baca, name="baca"),
    path("baca-semua/", views.tandai_semua, name="baca_semua"),
]
