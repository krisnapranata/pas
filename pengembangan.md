# Pengembangan Mendatang — Integrasi Pembayaran QRIS & Virtual Account

> Catatan untuk pengembangan selanjutnya. Saat ini aplikasi masih memakai
> `ManualProvider` (dummy), sehingga QRIS dan VA yang tampil belum nyata.

## Status Sekarang

- QRIS & VA menggunakan `ManualProvider` di `pembayaran/services.py`.
- QRIS: hanya menghasilkan string placeholder `MANUAL-QRIS-{pk}` (yang saya render
  sebagai gambar QR di halaman detail transaksi).
- VA: hanya menghasilkan nomor palsu `9910{8 digit}`.
- Webhook sudah ada endpoint-nya (`/pembayaran/webhook/<provider>/`) dan model
  `WebhookLog`, tetapi validasi signature masih stub (`False`).

## Yang Sudah Disiapkan (Arsitektur)

1. **Abstraksi provider** — `BasePaymentProvider` (`pembayaran/services.py`) dengan
   method: `create_qris`, `create_virtual_account`, `create_ewallet`,
   `create_card_payment`, `verify_payment`, `cancel_payment`, `refund_payment`,
   `validate_webhook_signature`.
2. **Fasade** `PaymentService` — memilih provider lewat env `PAYMENT_PROVIDER`.
3. **Endpoint webhook** — `/pembayaran/webhook/<provider>/`, idempotent via
   `webhook_event_id`.
4. **Credential** via environment variable (bukan source code):
   - `PAYMENT_PROVIDER`
   - `PAYMENT_API_KEY`
   - `PAYMENT_SECRET`
   - `PAYMENT_MERCHANT_ID`
   - `PAYMENT_WEBHOOK_SECRET`

## Langkah Integrasi Nyata

1. **Buat kelas provider konkret** (contoh `MidtransProvider`, `XenditProvider`,
   `DuitkuProvider`) yang mengimplementasikan:
   - `create_qris(transaction)` → panggil API penyedia, isi `qr_string`
     (atau `payment_url`).
   - `create_virtual_account(transaction)` → panggil API penyedia, isi `va_number`,
     `payment_url`, `provider_transaction_id`, `expired_at`.
   - `verify_payment(transaction)` → cek status ke penyedia (opsional).
   - `validate_webhook_signature(payload, signature)` → validasi HMAC/token.
2. **Daftarkan provider** di `PaymentService._resolve_provider` (atau biarkan resolusi
   dinamis dari `pembayaran.providers`).
3. **Sambungkan channel VA** (`BCA_VA`, `BNI_VA`, `BRI_VA`, `MANDIRI_VA`) sebagai
   `PaymentMethod` ke channel yang disediakan penyedia.
4. **Mapping status callback** penyedia → `PaymentTransaction.Status`
   (`PAID` / `FAILED` / `EXPIRED`).
5. **Validasi webhook**: cek signature, nominal, currency, dan merchant reference
   (sudah sebagian ada di `pembayaran/views.py:webhook`).
6. **Uji end-to-end** di sandbox penyedia sebelum production.

## Hal Lain yang Perlu Diperhatikan

- Jangan menyimpan nomor kartu lengkap / CVV (data kartu diproses penyedia).
- Webhook harus idempotent (event duplikat tidak boleh membuat pembayaran ganda).
- Simpan `provider_transaction_id` dan `merchant_reference` untuk rekonsiliasi.
- Kandidat penyedia (PSP/PJP) yang umum di Indonesia: Midtrans, Xendit, Duitku,
  DOKU, iPaymu.
