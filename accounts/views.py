from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LoginForm, PemohonRegistrationForm
from .models import User


def home(request):
    return redirect("accounts:login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = LoginForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect("dashboard:home")
    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = PemohonRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Registrasi berhasil. Selamat datang di Portal PAS Bandara.")
        return redirect("dashboard:home")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profil_view(request):
    return render(request, "accounts/profil.html")


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("accounts:login")
    return redirect("dashboard:home")
