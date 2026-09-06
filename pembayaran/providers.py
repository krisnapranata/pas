import hashlib
import hmac

from .services import ManualProvider


def compute_webhook_signature(secret, raw_body: str) -> str:
    """Hitung HMAC-SHA256 signature untuk verifikasi webhook."""
    return hmac.new(secret.encode(), raw_body.encode(), hashlib.sha256).hexdigest()


__all__ = ["compute_webhook_signature", "ManualProvider"]
