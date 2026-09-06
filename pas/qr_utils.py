import io
import urllib.parse

import qrcode
from django.conf import settings


def build_verify_url(token):
    """URL verifikasi publik berdasar token (§17)."""
    base = getattr(settings, "PAS_BASE_URL", "http://localhost:8000")
    return f"{base}/pas/verify/{token}/"


def qr_png_data(token, box_size=8):
    """Hasilkan QR code PNG (data URL base64) untuk token."""
    url = build_verify_url(token)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    import base64
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
