from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def daftar(request):
    notifikasi = Notification.objects.filter(user=request.user)
    return render(request, "notifikasi/daftar.html", {"notifikasi": notifikasi})


@login_required
def tandai_baca(request, pk):
    notifikasi = get_object_or_404(Notification, pk=pk, user=request.user)
    notifikasi.is_read = True
    notifikasi.save(update_fields=["is_read"])
    if notifikasi.url:
        return redirect(notifikasi.url)
    return redirect("notifikasi:daftar")


@login_required
def tandai_semua(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifikasi:daftar")
