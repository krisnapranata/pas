from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator


def send_email_confirmation(request, user):
    """Kirim email konfirmasi berisi link verifikasi akun."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = f"register/konfirmasi/{uid}/{token}/"
    domain = getattr(settings, "PAS_BASE_URL", "http://localhost:8000")
    link = f"{domain}/{path}"

    subject = "Konfirmasi Email — PAS Bandara"
    message = (
        f"Halo {user.get_full_name() or user.username},\n\n"
        "Terima kasih telah mendaftar di Portal PAS Bandara.\n"
        "Silakan klik tautan berikut untuk mengaktifkan akun Anda:\n\n"
        f"{link}\n\n"
        "Jika Anda tidak merasa mendaftar, abaikan email ini.\n\n"
        "— Tim PAS Bandara"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@pas.bandara.local"
    send_mail(subject, message, from_email, [user.email], fail_silently=False)
