# Sistem Manajemen Permintaan PAS Bandara

## 1. Tujuan

Membangun aplikasi web untuk mengelola proses permintaan PAS bandara secara end-to-end, mulai dari pendaftaran pemohon, pengajuan PAS, verifikasi persyaratan, penjadwalan screening, pelaksanaan screening, pembayaran, approval, penerbitan PAS, sampai perpanjangan dan pencabutan PAS.

Teknologi utama:

- Python
- Django
- Virtual Environment (`venv`)
- Django Templates
- HTMX
- Bootstrap
- MariaDB/MySQL
- Redis (opsional)
- Docker (opsional untuk deployment)

---

## 2. Arsitektur Sistem

```text
                    INTERNET
                       |
                       v
                Nginx / Reverse Proxy
                       |
                       v
                Django Application
                       |
          +------------+-------------+
          |            |             |
          v            v             v
       Database      Redis       File Storage
       MariaDB       Optional      Dokumen
          |
          v
   Sistem Manajemen PAS
```

Aplikasi dibagi menjadi beberapa interface:

1. **Portal Pemohon**
   - Registrasi/login
   - Data pribadi
   - Data perusahaan
   - Pengajuan PAS
   - Upload dokumen
   - Pemilihan jadwal screening
   - Pembayaran
   - Monitoring status
   - Download/cetak PAS

2. **Portal Admin PAS**
   - Verifikasi pengajuan
   - Verifikasi dokumen
   - Pengelolaan persyaratan
   - Pengelolaan jadwal screening
   - Pengelolaan pembayaran
   - Approval
   - Penerbitan PAS

3. **Portal Petugas Screening**
   - Melihat jadwal
   - Daftar peserta screening
   - Scan QR
   - Verifikasi identitas
   - Input hasil screening

4. **Dashboard Management**
   - Statistik pengajuan
   - Statistik screening
   - Statistik pembayaran
   - PAS aktif
   - PAS akan kedaluwarsa
   - Laporan

---

# 3. Workflow Utama

```text
REGISTRASI
    |
    v
DATA PEMOHON & PERUSAHAAN
    |
    v
PENGAJUAN PAS
    |
    v
UPLOAD PERSYARATAN
    |
    v
VERIFIKASI ADMINISTRASI
    |
    +---- DITOLAK / REVISI
    |
    v
LULUS ADMINISTRASI
    |
    v
PENJADWALAN SCREENING
    |
    v
SCREENING
    |
    +---- TIDAK LULUS
    |          |
    |          v
    |     JADWAL ULANG / SELESAI
    |
    v
LULUS SCREENING
    |
    v
PEMBAYARAN
    |
    v
VERIFIKASI PEMBAYARAN
    |
    v
APPROVAL
    |
    v
PAS DITERBITKAN
    |
    v
CETAK / QR CODE
```

> Catatan: Urutan pembayaran terhadap screening harus mengikuti SOP bandara. Sistem dibuat fleksibel agar posisi pembayaran dapat diubah tanpa mengubah struktur utama aplikasi.

---

# 4. Status Pengajuan PAS

Gunakan status terstruktur:

```text
DRAFT
SUBMITTED
DOCUMENT_REVIEW
REVISION_REQUIRED
ADMIN_APPROVED
WAITING_SCREENING
SCREENING_SCHEDULED
SCREENING_PROCESS
SCREENING_PASSED
SCREENING_FAILED
WAITING_PAYMENT
PAYMENT_PENDING
PAYMENT_PAID
PAYMENT_FAILED
WAITING_APPROVAL
APPROVED
REJECTED
PAS_ISSUED
EXPIRED
CANCELLED
```

Setiap perubahan status harus dicatat dalam audit log.

---

# 5. Jenis PAS

Jenis PAS harus configurable melalui database, bukan hard-code.

Contoh:

- PAS Harian
- PAS Sementara
- PAS Bulanan
- PAS Tahunan
- PAS Orang
- PAS Kendaraan
- PAS Visitor

Model `JenisPAS` harus memungkinkan admin menentukan:

- Nama
- Kode
- Deskripsi
- Masa berlaku
- Biaya
- Apakah membutuhkan screening
- Apakah membutuhkan approval
- Status aktif

---

# 6. Data Pemohon

Model `Pemohon`:

- User Django
- NIK
- Nama lengkap
- Tempat lahir
- Tanggal lahir
- Jenis kelamin
- Alamat
- Nomor HP
- Email
- Jabatan
- Perusahaan
- Foto
- Status aktif

Data sensitif harus dilindungi dan akses dibatasi berdasarkan role.

---

# 7. Data Perusahaan

Model `Perusahaan`:

- Nama perusahaan
- NIB
- NPWP
- Alamat
- Telepon
- Email
- PIC
- Status aktif
- Dokumen legalitas

Satu perusahaan dapat memiliki banyak pemohon.

---

# 8. Pengajuan PAS

Model `PengajuanPAS`:

```text
nomor_pengajuan
pemohon
perusahaan
jenis_pas
tanggal_pengajuan
tanggal_mulai
tanggal_berakhir
keperluan
area_akses
status
catatan
created_at
updated_at
```

Nomor pengajuan harus unik.

Contoh:

```text
PAS-2026-000001
```

---

# 9. Persyaratan Dokumen

Persyaratan harus dynamic.

Model:

## Persyaratan

```text
jenis_pas
nama
kode
deskripsi
wajib
format_file
max_size
aktif
urutan
```

Contoh:

```text
PAS Tahunan
|
+-- KTP
+-- Foto
+-- Surat Permohonan
+-- Surat Penugasan
+-- Surat Pernyataan
```

Untuk PAS kendaraan:

```text
PAS Kendaraan
|
+-- STNK
+-- Foto Kendaraan
+-- Surat Permohonan
+-- Dokumen Perusahaan
```

---

# 10. Dokumen Pengajuan

Model `DokumenPengajuan`:

```text
pengajuan
persyaratan
file
nomor_dokumen
tanggal_upload
status_verifikasi
catatan_verifikator
verified_by
verified_at
```

Status:

```text
UPLOADED
VALID
INVALID
REVISION_REQUIRED
```

---

# 11. Jadwal Screening

Screening adalah modul utama.

Model `ScreeningSchedule`:

```text
tanggal
jam_mulai
jam_selesai
lokasi
kuota
status
```

Contoh:

```text
10 September 2026
08:00 - 10:00
Kuota: 20
Terisi: 15
Sisa: 5
```

Status:

```text
OPEN
FULL
CLOSED
CANCELLED
```

---

# 12. Booking Screening

Model `ScreeningBooking`:

```text
nomor_booking
pengajuan
jadwal
nomor_antrian
waktu_booking
status
```

Status:

```text
BOOKED
CHECKED_IN
PROCESS
COMPLETED
NO_SHOW
CANCELLED
```

Contoh:

```text
SCR-2026-001258
```

---

# 13. Hasil Screening

Model `ScreeningResult`:

```text
booking
petugas
waktu_screening
hasil
catatan
created_at
```

Hasil:

```text
PASSED
FAILED
```

Petugas dapat memeriksa:

- Identitas
- Dokumen
- Kesesuaian data
- Pemeriksaan sesuai SOP
- Catatan screening

---

# 14. Modul Pembayaran — Multi Payment

Modul pembayaran dirancang sebagai **payment abstraction layer**, sehingga aplikasi PAS tidak bergantung langsung pada satu bank atau satu payment gateway.

Tujuan:

- Mendukung QRIS.
- Mendukung Virtual Account berbagai bank.
- Mendukung transfer bank.
- Mendukung e-wallet.
- Mendukung kartu debit/kredit jika tersedia dari payment gateway.
- Mendukung convenience store/OTC jika diperlukan.
- Mendukung pembayaran manual sebagai fallback.
- Mendukung webhook/callback otomatis.
- Mendukung rekonsiliasi pembayaran.
- Mendukung transaksi pending, paid, expired, failed, cancelled, dan refund.
- Memisahkan logic bisnis PAS dari provider pembayaran.

## 14.1 Metode Pembayaran

Metode pembayaran yang disiapkan:

```text
QRIS
VIRTUAL_ACCOUNT
BANK_TRANSFER
E_WALLET
CARD
OTC
MANUAL_TRANSFER
CASH
OTHER
```

Ketersediaan channel aktual bergantung pada Payment Service Provider (PSP/PJP) yang digunakan.

### QRIS

Pemohon dapat memilih:

```text
QRIS
  ↓
Generate Dynamic QR
  ↓
Scan dengan aplikasi pembayaran
  ↓
Pembayaran
  ↓
Webhook
  ↓
Invoice PAID
```

QRIS harus menggunakan nominal transaksi yang sesuai dengan invoice.

Data transaksi minimal:

```text
provider
reference_id
qr_string
amount
expired_at
status
```

### Virtual Account

Dukungan VA dirancang agar dapat menggunakan beberapa bank melalui payment gateway.

Contoh:

```text
BCA
BNI
BRI
Mandiri
Permata
CIMB
Bank lain yang tersedia pada provider
```

Flow:

```text
Invoice
   ↓
Create VA
   ↓
Nomor VA diberikan kepada pemohon
   ↓
Pemohon transfer
   ↓
Provider menerima pembayaran
   ↓
Webhook
   ↓
Invoice PAID
```

Nomor VA tidak boleh dibuat hard-code. Simpan data VA pada transaksi.

### Bank Transfer

Dapat digunakan untuk:

- Transfer melalui rekening resmi.
- Transfer yang diproses melalui provider.
- Transfer manual dengan upload bukti pembayaran.

Untuk transfer manual:

```text
PEMOHON
   ↓
Transfer
   ↓
Upload Bukti
   ↓
Admin Verifikasi
   ↓
VALID
   ↓
PAID
```

Jangan mengubah status menjadi `PAID` hanya berdasarkan upload bukti. Status harus berubah menjadi `PAID` setelah verifikasi petugas atau callback resmi provider.

### E-Wallet

Jika tersedia pada payment gateway:

```text
DANA
GOPAY
OVO
SHOPEEPAY
dan channel lain
```

Flow mengikuti mekanisme provider:

```text
Create Transaction
      ↓
Payment URL / Deeplink / QR
      ↓
Customer Payment
      ↓
Webhook
      ↓
Verification
      ↓
PAID
```

### Kartu

Jika payment gateway mendukung:

- Credit Card
- Debit Card
- Visa
- Mastercard
- JCB
- Network lain yang tersedia

Aplikasi PAS **tidak menyimpan nomor kartu lengkap, CVV, atau data autentikasi kartu**. Proses data kartu dilakukan oleh payment provider sesuai mekanisme yang disediakan.

### Convenience Store / OTC

Opsional:

```text
Alfamart
Indomaret
OTC
```

Hanya diaktifkan jika diperlukan dan tersedia pada payment provider.

### Cash

Pembayaran tunai dapat dicatat sebagai transaksi manual.

Contoh:

```text
payment_method = CASH
status = PENDING_VERIFICATION
```

Petugas kemudian melakukan verifikasi dan sistem mencatat:

```text
verified_by
verified_at
receipt_number
```

---

# 14.2 Payment Gateway Abstraction

Jangan membuat aplikasi langsung bergantung pada API satu bank.

Gunakan interface/service:

```text
Django
   |
   v
PaymentService
   |
   +---- create_qris()
   +---- create_virtual_account()
   +---- create_ewallet()
   +---- create_card_payment()
   +---- verify_payment()
   +---- cancel_payment()
   +---- refund_payment()
   |
   v
Payment Provider
```

Contoh provider dapat diganti tanpa mengubah modul PAS.

```text
PaymentProvider
       |
       +-- ProviderA
       +-- ProviderB
       +-- ProviderC
```

Gunakan environment variable:

```env
PAYMENT_PROVIDER=provider_a
PAYMENT_API_KEY=
PAYMENT_SECRET=
PAYMENT_MERCHANT_ID=
PAYMENT_WEBHOOK_SECRET=
```

Jangan menyimpan credential payment gateway di source code.

---

# 14.3 Invoice

Model `Invoice`:

```text
nomor_invoice
pengajuan
subtotal
biaya_admin
discount
tax
total
currency
tanggal_terbit
tanggal_jatuh_tempo
status
created_at
updated_at
```

Contoh:

```text
INV-2026-000001

Subtotal       Rp 250.000
Biaya Admin    Rp   2.500
-------------------------
TOTAL          Rp 252.500
```

Status invoice:

```text
DRAFT
UNPAID
PENDING
PAID
PARTIALLY_PAID
EXPIRED
CANCELLED
REFUNDED
```

---

# 14.4 Payment Transaction

Model `PaymentTransaction`:

```text
invoice
provider
payment_method
provider_transaction_id
merchant_reference
amount
currency
status
payment_url
qr_string
va_number
expired_at
paid_at
created_at
updated_at
```

Status transaksi:

```text
CREATED
PENDING
PAID
FAILED
EXPIRED
CANCELLED
REFUNDED
PARTIALLY_REFUNDED
```

Simpan `provider_transaction_id` dan `merchant_reference` untuk rekonsiliasi.

---

# 14.5 Payment Webhook

Webhook adalah bagian wajib.

Contoh:

```text
Payment Provider
       |
       | POST /api/payment/webhook/
       v
Django
       |
       +-- Validate signature
       +-- Validate provider
       +-- Find transaction
       +-- Check amount
       +-- Check currency
       +-- Check duplicate event
       +-- Update transaction
       +-- Update invoice
       +-- Continue PAS workflow
```

Webhook harus **idempotent**.

Jika provider mengirim callback dua kali, sistem tidak boleh membuat pembayaran menjadi dua kali.

Simpan:

```text
webhook_event_id
received_at
payload
signature
processing_status
```

Jangan mempercayai callback hanya berdasarkan `status=PAID`; signature dan data transaksi harus divalidasi.

---

# 14.6 Payment Verification

Untuk transaksi yang menerima webhook:

```text
WEBHOOK
   ↓
VALIDATE SIGNATURE
   ↓
FIND TRANSACTION
   ↓
CHECK AMOUNT
   ↓
CHECK REFERENCE
   ↓
OPTIONAL API STATUS CHECK
   ↓
PAID
```

Untuk pembayaran manual:

```text
UPLOAD BUKTI
   ↓
PENDING_VERIFICATION
   ↓
PETUGAS
   ↓
VALID / INVALID
```

---

# 14.7 Rekonsiliasi Pembayaran

Sediakan menu:

```text
Pembayaran
|
+-- Semua Transaksi
+-- Pending
+-- Paid
+-- Failed
+-- Expired
+-- Manual Verification
+-- Refund
+-- Rekonsiliasi
```

Contoh dashboard:

```text
Invoice        Metode       Nominal       Status
------------------------------------------------------
INV-0001       QRIS         250.000       PAID
INV-0002       BCA VA       500.000       PAID
INV-0003       Mandiri VA   300.000       PENDING
INV-0004       Transfer     750.000       VERIFIKASI
INV-0005       E-Wallet     125.000       EXPIRED
```

Rekonsiliasi dapat membandingkan:

```text
Invoice
    ↕
Payment Transaction
    ↕
Provider Transaction
```

---

# 14.8 Expired Payment

Setiap payment yang memiliki batas waktu harus mempunyai:

```text
expired_at
```

Contoh:

```text
Invoice dibuat
      ↓
Payment aktif 24 jam
      ↓
Tidak dibayar
      ↓
EXPIRED
```

Setelah expired, pemohon dapat:

```text
[ BAYAR ULANG ]
```

Sistem membuat transaksi pembayaran baru tanpa menggandakan invoice.

---

# 14.9 Refund

Jika diperlukan:

```text
PAID
  ↓
REFUND REQUEST
  ↓
APPROVAL
  ↓
REFUND PROCESS
  ↓
REFUNDED
```

Simpan:

```text
refund_id
refund_amount
reason
requested_by
approved_by
processed_at
provider_refund_id
status
```

Refund harus memiliki audit trail.

---

# 14.10 Pembayaran dan Workflow PAS

Setelah pembayaran berhasil:

```text
PAYMENT_PAID
      ↓
WAITING_APPROVAL
      ↓
APPROVED
      ↓
PAS_ISSUED
```

Jika SOP bandara mensyaratkan pembayaran sebelum screening, workflow dapat menjadi:

```text
ADMIN_APPROVED
      ↓
WAITING_PAYMENT
      ↓
PAYMENT_PAID
      ↓
WAITING_SCREENING
      ↓
SCREENING
```

Jika screening harus dilakukan sebelum pembayaran:

```text
ADMIN_APPROVED
      ↓
WAITING_SCREENING
      ↓
SCREENING_PASSED
      ↓
WAITING_PAYMENT
      ↓
PAYMENT_PAID
```

Urutan harus configurable berdasarkan SOP.

---

# 14.11 Model Payment Method

Gunakan master data agar metode pembayaran tidak hard-code.

Model `PaymentMethod`:

```text
code
name
type
provider
active
sort_order
configuration
```

Contoh:

```text
QRIS
BCA_VA
BNI_VA
BRI_VA
MANDIRI_VA
DANA
GOPAY
OVO
CARD
MANUAL_TRANSFER
CASH
```

---

# 14.12 Keamanan Pembayaran

Wajib:

- HTTPS.
- Validasi signature webhook.
- Idempotency.
- Jangan menyimpan CVV.
- Jangan menyimpan nomor kartu lengkap.
- Credential provider melalui environment variable.
- Audit semua perubahan status.
- Validasi nominal.
- Validasi currency.
- Validasi merchant/reference.
- Mencegah replay webhook.
- Membatasi endpoint webhook.
- Logging tanpa membocorkan secret.
- Rekonsiliasi transaksi.

---

# 14.13 Rekomendasi Arsitektur Pembayaran

```text
                    PEMOHON
                       |
                       v
                Portal PAS Django
                       |
                       v
                 PaymentService
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
      QRIS             VA          E-Wallet
        |              |              |
        +--------------+--------------+
                       |
                       v
                PAYMENT PROVIDER
                       |
                       v
                    WEBHOOK
                       |
                       v
                 Django Backend
                       |
             +---------+---------+
             |                   |
             v                   v
        PaymentTransaction     Invoice
             |                   |
             +---------+---------+
                       |
                       v
                  PAS Workflow
```

---

# 14.14 Prinsip Penting

1. **Satu invoice dapat memiliki beberapa payment attempt**, tetapi hanya transaksi valid yang boleh menjadi pembayaran final.
2. **Webhook harus idempotent.**
3. **Upload bukti transfer bukan bukti otomatis bahwa pembayaran lunas.**
4. **Status pembayaran harus berasal dari verifikasi provider atau petugas berwenang.**
5. **Payment gateway dapat diganti tanpa mengubah modul PAS.**
6. **Semua transaksi harus dapat direkonsiliasi.**
7. **Pembayaran expired harus dapat dibuat ulang.**
8. **Refund harus memiliki approval dan audit trail.**
9. **Credential payment provider tidak boleh masuk Git.**
10. **Data kartu tidak disimpan oleh aplikasi PAS.**

---

# 15. Approval

Model `Approval`:

```text
pengajuan
level
role
approver
status
catatan
approved_at
```

Contoh workflow:

```text
Admin PAS
    |
    v
Verifikator
    |
    v
Security / AVSEC
    |
    v
Pejabat Berwenang
```

Workflow harus configurable.

---

# 16. Penerbitan PAS

Model `PASCard`:

```text
nomor_pas
pengajuan
nomor_induk
jenis_pas
tanggal_terbit
tanggal_berlaku
tanggal_expired
status
qr_token
issued_by
issued_at
```

Contoh:

```text
PAS ID:
PAS-2026-000123

Nama:
Budi Santoso

Perusahaan:
PT ABC

Berlaku:
01-01-2027 s/d 31-12-2027
```

PAS memiliki QR Code untuk validasi.

---

# 17. Verifikasi QR

Petugas dapat scan QR Code.

QR tidak boleh menyimpan seluruh data pribadi.

Gunakan token unik:

```text
https://domain-bandara/pas/verify/<token>
```

Sistem menampilkan:

```text
PAS VALID

Nama: Budi Santoso
Perusahaan: PT ABC
Jenis: PAS Tahunan
Berlaku sampai: 31-12-2027
Status: AKTIF
```

Jika expired:

```text
PAS TIDAK BERLAKU
```

---

# 18. Audit Log

Semua aktivitas penting harus dicatat.

Model `AuditLog`:

```text
user
action
model_name
object_id
old_value
new_value
ip_address
user_agent
created_at
```

Contoh:

```text
ADMIN
APPROVE_APPLICATION
PAS-2026-000123
2026-09-06 10:15
```

Audit log tidak boleh mudah dihapus oleh user biasa.

---

# 19. Role dan Permission

Gunakan Django Authentication + Groups/Permissions.

Role awal:

```text
SUPERADMIN
ADMIN_PAS
VERIFIKATOR
PETUGAS_SCREENING
PETUGAS_PEMBAYARAN
APPROVER
SECURITY
PEMOHON
MANAGEMENT
```

Setiap role hanya melihat fungsi yang diperlukan.

---

# 20. Struktur Project Django

Gunakan virtual environment.

```bash
mkdir pas-bandara
cd pas-bandara

python3 -m venv venv
source venv/bin/activate
```

Windows:

```powershell
python -m venv venv
venv\Scriptsctivate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install Django:

```bash
pip install django
```

Tambahkan kebutuhan awal:

```bash
pip install mysqlclient pillow qrcode
```

Untuk development:

```bash
pip freeze > requirements.txt
```

Buat project:

```bash
django-admin startproject config .
```

Buat aplikasi:

```bash
python manage.py startapp accounts
python manage.py startapp perusahaan
python manage.py startapp pas
python manage.py startapp screening
python manage.py startapp pembayaran
python manage.py startapp approval
python manage.py startapp dashboard
python manage.py startapp audit
```

Struktur:

```text
pas-bandara/
│
├── venv/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
├── perusahaan/
├── pas/
├── screening/
├── pembayaran/
├── approval/
├── dashboard/
├── audit/
│
├── templates/
├── static/
├── media/
│
├── manage.py
├── requirements.txt
└── .gitignore
```

---

# 21. Database

Development dapat dimulai dengan SQLite jika diperlukan.

Untuk production gunakan:

```text
MariaDB / MySQL
```

Contoh konfigurasi:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "pas_bandara",
        "USER": "pas_user",
        "PASSWORD": "password",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    }
}
```

Password database harus menggunakan environment variable.

---

# 22. Environment

Gunakan `.env`.

Contoh:

```env
DEBUG=True
SECRET_KEY=change-this
DB_NAME=pas_bandara
DB_USER=pas_user
DB_PASSWORD=change-this
DB_HOST=127.0.0.1
DB_PORT=3306
```

Jangan commit `.env`.

`.gitignore`:

```text
venv/
.env
__pycache__/
*.pyc
db.sqlite3
media/
staticfiles/
```

---

# 23. HTMX

Gunakan HTMX untuk interaksi SPA ringan tanpa membuat frontend framework besar.

Contoh:

```html
<button
    hx-get="{% url 'screening:jadwal_list' %}"
    hx-target="#workspace"
    hx-swap="innerHTML">
    Jadwal Screening
</button>
```

Target:

```html
<div id="workspace"></div>
```

Gunakan Bootstrap sebagai CSS utama.

---

# 24. Halaman Portal Pemohon

Menu:

```text
Dashboard
|
+-- Profil Saya
+-- Perusahaan
+-- Pengajuan PAS
+-- Dokumen
+-- Jadwal Screening
+-- Pembayaran
+-- PAS Saya
+-- Riwayat
+-- Notifikasi
```

Dashboard menampilkan:

```text
Pengajuan Aktif
Status Dokumen
Jadwal Screening
Tagihan
PAS Aktif
```

---

# 25. Dashboard Admin

Menu:

```text
Dashboard
|
+-- Pengajuan PAS
+-- Verifikasi Dokumen
+-- Jadwal Screening
+-- Hasil Screening
+-- Pembayaran
+-- Approval
+-- PAS Terbit
+-- Master Data
+-- Laporan
+-- Audit Log
```

---

# 26. Notifikasi

Sistem dapat mengirim notifikasi:

- Pengajuan diterima
- Dokumen kurang
- Dokumen disetujui
- Jadwal screening tersedia
- Jadwal screening berubah
- Screening lulus
- Screening gagal
- Invoice dibuat
- Pembayaran diterima
- PAS disetujui
- PAS diterbitkan
- PAS akan kedaluwarsa

Channel:

```text
WhatsApp
Email
Notifikasi dalam aplikasi
```

Integrasi WhatsApp dapat dilakukan melalui API/provider yang tersedia.

---

# 27. Laporan

Laporan minimal:

1. Pengajuan PAS per periode
2. Pengajuan berdasarkan perusahaan
3. Pengajuan berdasarkan jenis PAS
4. Screening per tanggal
5. Screening lulus/gagal
6. Pembayaran
7. PAS aktif
8. PAS expired
9. PAS akan expired
10. Pembatalan PAS
11. Aktivitas petugas

Export:

```text
Excel
PDF
CSV
```

---

# 28. Keamanan

Wajib diterapkan:

- HTTPS
- CSRF protection
- Authentication
- Role-based access control
- Validasi upload
- Pembatasan ukuran file
- Validasi MIME type
- Audit log
- Secure cookie
- Password hashing Django
- Rate limiting untuk endpoint sensitif
- QR token random dan sulit ditebak
- Backup database
- Backup dokumen
- Pembatasan akses dokumen pribadi

Dokumen KTP dan dokumen sensitif tidak boleh tersedia melalui URL publik langsung.

---

# 29. Tahapan Development

## Tahap 1 — Foundation

- Setup Python
- Setup `venv`
- Setup Django
- Database
- Authentication
- User roles
- Base template
- Bootstrap
- HTMX

## Tahap 2 — Master Data

- Perusahaan
- Jenis PAS
- Persyaratan
- Area akses
- Tarif

## Tahap 3 — Pengajuan

- Form pengajuan
- Upload dokumen
- Validasi
- Status pengajuan
- Revisi dokumen

## Tahap 4 — Screening

- Jadwal
- Kuota
- Booking
- Nomor antrian
- Check-in
- Screening
- Hasil screening

## Tahap 5 — Pembayaran

- Invoice
- VA/QRIS
- Payment gateway
- Webhook
- Status pembayaran

## Tahap 6 — Approval

- Workflow approval
- Approval berjenjang
- Rejection
- Audit trail

## Tahap 7 — PAS

- Generate nomor PAS
- Generate QR
- Kartu PAS
- PDF
- Validasi QR

## Tahap 8 — Dashboard & Reporting

- Statistik
- Grafik
- Laporan
- Export

## Tahap 9 — Production

- Gunicorn
- Nginx
- MariaDB
- Redis
- Backup
- Monitoring
- HTTPS
- Security hardening

---

# 30. Prinsip Pengembangan

1. Jangan hard-code jenis PAS.
2. Jangan hard-code persyaratan.
3. Jangan hard-code workflow approval.
4. Semua proses penting harus memiliki status.
5. Semua perubahan penting dicatat di audit log.
6. Dokumen sensitif harus dilindungi.
7. Pembayaran menggunakan webhook.
8. Screening menggunakan sistem booking dan kuota.
9. QR Code menggunakan token, bukan data pribadi.
10. Sistem harus dapat dikembangkan untuk banyak jenis PAS dan banyak perusahaan.

---

# 31. Target MVP

MVP pertama harus mampu melakukan:

```text
Registrasi
    ↓
Perusahaan
    ↓
Pengajuan PAS
    ↓
Upload Dokumen
    ↓
Verifikasi
    ↓
Jadwal Screening
    ↓
Booking
    ↓
Hasil Screening
    ↓
Invoice
    ↓
Pembayaran
    ↓
Approval
    ↓
PAS + QR Code
```

Setelah MVP stabil, baru tambahkan:

- WhatsApp
- Payment Gateway
- Dashboard management
- Mobile/PWA petugas
- Scanner QR
- Reporting
- Renewal otomatis
- Integrasi sistem bandara lainnya
