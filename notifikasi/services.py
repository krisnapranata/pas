import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def notify(user, title, message="", url="", pengajuan=None, email=True):
    """Buat notifikasi in-app + kirim email (opsional)."""
    Notification.objects.create(
        user=user, title=title, message=message, url=url, pengajuan=pengajuan
    )
    if email and getattr(user, "email", ""):
        try:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@pas.bandara.local"
            send_mail(
                f"[PAS Bandara] {title}",
                message or title,
                from_email,
                [user.email],
                fail_silently=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal kirim email ke %s: %s", user.email, exc)


def notify_role(role, title, message="", url="", pengajuan=None, email=True):
    """Kirim notifikasi ke semua user dengan role tertentu."""
    from accounts.models import User

    for user in User.objects.filter(role=role):
        notify(user, title, message, url, pengajuan, email=email)
