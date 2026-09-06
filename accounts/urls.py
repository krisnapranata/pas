from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("register/sukses/", views.register_sukses, name="register_sukses"),
    path("register/konfirmasi/<uidb64>/<token>/", views.konfirmasi_email, name="konfirmasi_email"),
    path("register/kirim-ulang/", views.kirim_ulang_konfirmasi, name="kirim_ulang_konfirmasi"),
    path("logout/", views.logout_view, name="logout"),
    path("profil/", views.profil_view, name="profil"),
]
