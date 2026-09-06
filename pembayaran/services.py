"""Payment abstraction layer (§14.2).

Provider dipilih lewat environment variable PAYMENT_PROVIDER.
Modul PAS tidak bergantung langsung pada satu payment gateway.
"""

import hashlib
import hmac
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class BasePaymentProvider:
    """Interface dasar payment provider."""

    name = "base"

    def create_qris(self, transaction):
        raise NotImplementedError

    def create_virtual_account(self, transaction):
        raise NotImplementedError

    def create_ewallet(self, transaction):
        raise NotImplementedError

    def create_card_payment(self, transaction):
        raise NotImplementedError

    def verify_payment(self, transaction):
        raise NotImplementedError

    def cancel_payment(self, transaction):
        raise NotImplementedError

    def refund_payment(self, transaction, amount):
        raise NotImplementedError

    def validate_webhook_signature(self, payload, signature):
        return False


class ManualProvider(BasePaymentProvider):
    """Provider manual (fallback). Tidak membuat charge provider nyata."""

    name = "manual"

    def create_qris(self, transaction):
        transaction.qr_string = f"MANUAL-QRIS-{transaction.pk}"
        transaction.status = "PENDING"
        transaction.expired_at = transaction.invoice.tanggal_jatuh_tempo
        transaction.save()
        return transaction

    def create_virtual_account(self, transaction):
        transaction.va_number = f"9910{transaction.pk:08d}"
        transaction.status = "PENDING"
        transaction.expired_at = transaction.invoice.tanggal_jatuh_tempo
        transaction.save()
        return transaction

    def verify_payment(self, transaction):
        # Manual: hanya verifikasi status DB, bukan callback provider
        return transaction.status == "PAID"


class PaymentService:
    """Fasade untuk seluruh operasi pembayaran."""

    def __init__(self, provider_name=None):
        provider_name = provider_name or getattr(settings, "PAYMENT_PROVIDER", "manual")
        self.provider = self._resolve_provider(provider_name)

    def _resolve_provider(self, name):
        mapping = {
            "manual": ManualProvider,
        }
        if name in mapping:
            return mapping[name]()
        # Fallback: coba import provider dinamis dari pembayaran.providers
        try:
            from pembayaran import providers
            cls = getattr(providers, name.title() + "Provider", None)
            if cls:
                return cls()
        except (ImportError, AttributeError):
            pass
        logger.warning("Provider '%s' tidak ditemukan, pakai manual.", name)
        return ManualProvider()

    # ---- delegasi ----
    def create_qris(self, transaction):
        return self.provider.create_qris(transaction)

    def create_virtual_account(self, transaction):
        return self.provider.create_virtual_account(transaction)

    def create_ewallet(self, transaction):
        return self.provider.create_ewallet(transaction)

    def create_card_payment(self, transaction):
        return self.provider.create_card_payment(transaction)

    def verify_payment(self, transaction):
        return self.provider.verify_payment(transaction)

    def cancel_payment(self, transaction):
        return self.provider.cancel_payment(transaction)

    def refund_payment(self, transaction, amount):
        return self.provider.refund_payment(transaction, amount)

    def validate_webhook_signature(self, payload, signature):
        return self.provider.validate_webhook_signature(payload, signature)
