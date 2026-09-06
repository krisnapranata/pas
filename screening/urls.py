from django.urls import path

from . import views

app_name = "screening"

urlpatterns = [
    path("jadwal/", views.jadwal_list, name="jadwal_list"),
    path("jadwal/<int:pk>/", views.jadwal_info, name="jadwal_info"),
    path("book/<int:pk>/", views.book, name="book"),
    path("booking-saya/", views.booking_saya, name="booking_saya"),
    path("peserta/<int:pk>/", views.daftar_peserta, name="daftar_peserta"),
    path("checkin/<int:pk>/", views.checkin, name="checkin"),
    path("hasil/<int:pk>/", views.input_hasil, name="input_hasil"),
]
