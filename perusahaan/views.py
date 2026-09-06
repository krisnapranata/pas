from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from audit.models import log_action

from .forms import PerusahaanForm
from .models import Perusahaan


@login_required
def daftar_perusahaan(request):
    """Pemohon melihat perusahaan miliknya + semua perusahaan aktif."""
    if request.user.is_staff or getattr(request.user, "role", "") != "PEMOHON":
        perusahaan = Perusahaan.objects.all()
    else:
        perusahaan = Perusahaan.objects.filter(status_aktif=True)
    return render(request, "perusahaan/daftar_perusahaan.html", {"perusahaan": perusahaan})


@login_required
def buat_perusahaan(request):
    if request.method == "POST":
        form = PerusahaanForm(request.POST, request.FILES)
        if form.is_valid():
            perusahaan = form.save(commit=False)
            perusahaan.created_by = request.user
            perusahaan.save()
            log_action(request, "BUAT_PERUSAHAAN", "Perusahaan", perusahaan.pk)
            messages.success(request, f"Perusahaan '{perusahaan.nama}' berhasil didaftarkan.")
            return redirect("perusahaan:daftar_perusahaan")
    else:
        form = PerusahaanForm()
    return render(request, "perusahaan/buat_perusahaan.html", {"form": form})


@login_required
def edit_perusahaan(request, pk):
    perusahaan = get_object_or_404(Perusahaan, pk=pk)
    if not (request.user.is_staff or perusahaan.created_by == request.user):
        messages.error(request, "Anda tidak punya akses mengubah perusahaan ini.")
        return redirect("perusahaan:daftar_perusahaan")
    if request.method == "POST":
        form = PerusahaanForm(request.POST, request.FILES, instance=perusahaan)
        if form.is_valid():
            form.save()
            messages.success(request, "Data perusahaan diperbarui.")
            return redirect("perusahaan:daftar_perusahaan")
    else:
        form = PerusahaanForm(instance=perusahaan)
    return render(request, "perusahaan/buat_perusahaan.html", {"form": form, "perusahaan": perusahaan})
