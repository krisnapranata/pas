from django.contrib import admin

from .models import (
    Invoice,
    PaymentMethod,
    PaymentTransaction,
    PembayaranManual,
    Refund,
    WebhookLog,
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "provider", "active", "sort_order")
    list_filter = ("type", "active")
    list_editable = ("active", "sort_order")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("nomor_invoice", "pengajuan", "subtotal", "total", "status", "tanggal_jatuh_tempo")
    list_filter = ("status",)
    search_fields = ("nomor_invoice", "pengajuan__nomor_pengajuan")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("merchant_reference", "invoice", "payment_method", "amount", "status", "paid_at")
    list_filter = ("status", "payment_method", "provider")
    search_fields = ("merchant_reference", "provider_transaction_id", "va_number")


@admin.register(PembayaranManual)
class PembayaranManualAdmin(admin.ModelAdmin):
    list_display = ("transaksi", "verified_by", "verified_at", "receipt_number")
    list_filter = ("transaksi__status",)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("transaksi", "refund_amount", "status", "requested_by", "approved_by")
    list_filter = ("status",)


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ("received_at", "provider", "webhook_event_id", "processing_status")
    list_filter = ("provider", "processing_status")
    readonly_fields = [f.name for f in WebhookLog._meta.fields]
