import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def _kirim_email(email, title, message):
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@epermit.local"
        send_mail(
            f"[EPermit] {title}",
            message or title,
            from_email,
            [email],
            fail_silently=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gagal kirim email ke %s: %s", email, exc)


def notify(user, title, message="", url="", pengajuan=None, email=True):
    """Buat notifikasi in-app + kirim email (opsional)."""
    if user is None:
        return None
    Notification.objects.create(
        user=user, title=title, message=message, url=url, pengajuan=pengajuan
    )
    if email and getattr(user, "email", ""):
        _kirim_email(user.email, title, message)


def notify_pemohon(pengajuan, title, message="", url="", email=True):
    """Notifikasi ke pemohon: in-app jika punya akun, email jika tanpa akun."""
    if pengajuan.pemohon_id:
        return notify(
            pengajuan.pemohon, title, message, url=url, pengajuan=pengajuan, email=email
        )
    if email and pengajuan.pemohon_email:
        _kirim_email(pengajuan.pemohon_email, title, message)
    return None


def notify_role(role, title, message="", url="", pengajuan=None, email=True):
    """Kirim notifikasi ke semua user dengan role tertentu."""
    from accounts.models import User

    for user in User.objects.filter(role=role):
        notify(user, title, message, url, pengajuan, email=email)
