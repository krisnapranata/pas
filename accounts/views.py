from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .email_utils import send_email_confirmation
from .forms import LoginForm, PemohonRegistrationForm, ProfilForm
from .models import User


def home(request):
    return redirect("accounts:login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = LoginForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_active:
            messages.error(request, "Akun belum aktif. Periksa email Anda untuk konfirmasi pendaftaran.")
            return redirect("accounts:login")
        login(request, user)
        return redirect("dashboard:home")
    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = PemohonRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.role = User.Role.PEMOHON
        user.is_active = False  # aktif setelah konfirmasi email
        user.email_verified = False
        user.save()
        send_email_confirmation(request, user)
        return redirect("accounts:register_sukses")
    return render(request, "accounts/register.html", {"form": form})


def register_sukses(request):
    return render(request, "accounts/register_sukses.html")


@login_required
def kirim_ulang_konfirmasi(request):
    user = request.user
    if user.email_verified:
        messages.info(request, "Email Anda sudah terkonfirmasi.")
        return redirect("dashboard:home")
    send_email_confirmation(request, user)
    messages.success(request, "Email konfirmasi telah dikirim ulang.")
    return redirect("dashboard:home")


def konfirmasi_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.email_verified = True
        user.save()
        messages.success(request, "Email berhasil dikonfirmasi. Akun Anda sekarang aktif. Silakan masuk.")
        return redirect("accounts:login")
    messages.error(request, "Tautan konfirmasi tidak valid atau sudah kedaluwarsa.")
    return redirect("accounts:login")


@login_required
def profil_view(request):
    form = ProfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil berhasil diperbarui.")
        return redirect("accounts:profil")
    return render(request, "accounts/profil.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("accounts:login")
    return redirect("dashboard:home")
