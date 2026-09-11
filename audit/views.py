from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import AuditLog


@login_required
def daftar(request):
    if not (request.user.is_staff or request.user.role == "ADMINISTRATOR"):
        return render(request, "audit/daftar.html", {"logs": AuditLog.objects.none()})
    qs = AuditLog.objects.select_related("user").all()[:500]
    return render(request, "audit/daftar.html", {"logs": qs})
