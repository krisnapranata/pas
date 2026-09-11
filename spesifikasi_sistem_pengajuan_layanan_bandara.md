# Sistem Pengajuan Layanan Bandara

## 1. Tujuan

Aplikasi digunakan untuk mengelola proses pengajuan layanan dari Pemohon sampai persetujuan Operasi, pembayaran, pemberitahuan kepada AOCH, dan penyelesaian layanan.

Sistem menggunakan 5 role utama:

1. Pemohon
2. Komersil
3. Operasi
4. AOCH
5. Administrator

---

# 2. Role dan Hak Akses

## 2.1 Pemohon

Pemohon adalah pihak yang mengajukan layanan.

### Hak akses

- Registrasi/login
- Membuat pengajuan
- Memilih layanan
- Mengisi data pengajuan
- Mengisi jumlah pendamping
- Melihat tarif yang dihitung sistem
- Upload dokumen persyaratan
- Melakukan revisi jika diminta Komersil
- Melihat status pengajuan
- Menerima notifikasi
- Melakukan pembayaran setelah disetujui Operasi
- Melihat status pembayaran
- Melihat riwayat pengajuan

### Catatan

Jumlah tamu dapat dicatat sebagai informasi, tetapi **bukan parameter utama penentuan tarif**.

Parameter utama tarif adalah **jumlah pendamping**.

---

## 2.2 Komersil

Komersil bertugas melakukan verifikasi administrasi dan kelengkapan data.

### Hak akses

- Melihat pengajuan baru
- Memeriksa data Pemohon
- Memeriksa dokumen
- Meminta Pemohon melakukan revisi
- Menyetujui kelengkapan data
- Meneruskan pengajuan ke Operasi
- Melihat perhitungan tarif
- Melihat status pembayaran
- Melihat riwayat pengajuan

### Batas kewenangan

Komersil **tidak memberikan persetujuan operasional**.

Persetujuan operasional dilakukan oleh role Operasi.

---

## 2.3 Operasi

Operasi bertugas memeriksa kemampuan/kesiapan operasional.

### Hak akses

- Melihat pengajuan yang sudah disetujui Komersil
- Memeriksa detail pengajuan
- Menyetujui pengajuan
- Menolak pengajuan
- Mengisi alasan penolakan
- Melihat status pembayaran
- Melihat jadwal layanan
- Melihat pengajuan yang akan dilaksanakan

### Jika Operasi menolak

Alasan penolakan wajib diisi.

Sistem mengubah status menjadi:

`DITOLAK_OPERASI`

Pemohon menerima notifikasi beserta alasan penolakan.

### Jika Operasi menyetujui

Sistem mengubah status menjadi:

`DISETUJUI_OPERASI_MENUNGGU_PEMBAYARAN`

Kemudian link pembayaran menjadi aktif untuk Pemohon.

---

## 2.4 AOCH

AOCH berfungsi sebagai pihak yang menerima informasi dan melakukan monitoring/acknowledgement.

### Hak akses

- Melihat pengajuan yang sudah melewati proses Komersil dan Operasi
- Melihat detail layanan
- Melihat tanggal dan waktu kegiatan
- Melihat jumlah pendamping
- Melihat status pembayaran
- Melakukan acknowledgement
- Melihat riwayat kegiatan

### Catatan

AOCH bukan approval tambahan, kecuali proses bisnis di kemudian hari menetapkan bahwa AOCH juga harus memberikan persetujuan.

---

## 2.5 Administrator

Administrator mengelola sistem dan master data.

### Hak akses

- Mengelola user
- Mengatur role
- Mengelola Master Layanan
- Mengelola Master Tarif
- Mengatur parameter layanan
- Mengatur konfigurasi pembayaran
- Mengatur notifikasi
- Melihat audit log
- Mengatur konfigurasi sistem

---

# 3. Alur Bisnis Utama

```text
PEMOHON
   |
   | Buat Pengajuan
   v
KOMERSIL
   |
   | Verifikasi Kelengkapan
   |
   +---- Tidak Lengkap ----> PEMOHON REVISI
   |
   | Lengkap
   v
KOMERSIL SETUJUI
   |
   | Push / teruskan
   v
OPERASI
   |
   +---- TOLAK ----> PEMOHON
   |
   | SETUJU
   v
MENUNGGU PEMBAYARAN
   |
   v
PEMBAYARAN
   |
   | Berhasil
   v
AOCH
   |
   | Acknowledgement / Monitoring
   v
PELAKSANAAN
   |
   v
SELESAI
```

---

# 4. Status Pengajuan

Status utama yang digunakan:

| Kode Status | Nama Status | Keterangan |
|---|---|---|
| `DRAFT` | Draft | Pengajuan belum dikirim |
| `DIAJUKAN` | Diajukan | Pemohon sudah mengirim pengajuan |
| `VERIFIKASI_KOMERSIL` | Verifikasi Komersil | Sedang diperiksa Komersil |
| `REVISI_PEMOHON` | Revisi Pemohon | Data/dokumen perlu diperbaiki |
| `DISETUJUI_KOMERSIL` | Disetujui Komersil | Data sudah lengkap |
| `MENUNGGU_OPERASI` | Menunggu Operasi | Menunggu keputusan Operasi |
| `DITOLAK_OPERASI` | Ditolak Operasi | Operasi menolak pengajuan |
| `DISETUJUI_OPERASI` | Disetujui Operasi | Operasi menyetujui |
| `MENUNGGU_PEMBAYARAN` | Menunggu Pembayaran | Link pembayaran aktif |
| `DIBAYAR` | Sudah Dibayar | Pembayaran berhasil |
| `SIAP_DILAKSANAKAN` | Siap Dilaksanakan | Pengajuan siap dilaksanakan |
| `DILAKSANAKAN` | Dilaksanakan | Layanan sedang/ telah dilaksanakan |
| `ACKNOWLEDGED_AOCH` | Acknowledged AOCH | AOCH sudah mengetahui |
| `SELESAI` | Selesai | Proses selesai |
| `DIBATALKAN` | Dibatalkan | Pengajuan dibatalkan |

---

# 5. Modul Pemohon

## Form Pengajuan

### A. Data Pemohon

- Nama
- Nomor identitas
- Nomor HP
- WhatsApp
- Email
- Instansi/perusahaan
- Alamat

### B. Data Layanan

- Pilih layanan
- Tanggal pelaksanaan
- Waktu kedatangan
- Nomor penerbangan
- Asal penerbangan
- Tujuan/instansi
- Jumlah tamu
- **Jumlah pendamping**
- Keterangan tambahan

### C. Dokumen

Dokumen dapat disesuaikan berdasarkan Master Layanan.

Contoh:

- Identitas
- Surat tugas
- Surat permohonan
- Dokumen pendukung lainnya

---

# 6. Pemilihan Layanan

Pemohon memilih layanan dari Master Layanan.

Contoh:

### Greet Service

- Minimal pendamping: 1
- Maksimal pendamping: 5
- Harga: Rp1.000.000
- Satuan: Per hari

### Greet & Desk Service

- Minimal pendamping: 1
- Maksimal pendamping: 5
- Harga: Rp1.500.000
- Satuan: Per hari

### Greet Group Service

- Minimal pendamping: 6
- Maksimal pendamping: tidak terbatas
- Harga: Rp200.000
- Satuan: Per pendamping / hari

---

# 7. Perhitungan Tarif Otomatis

Tarif **tidak boleh hard-code di source code**.

Tarif dibaca dari Master Layanan/Master Tarif.

## Contoh

Master:

```text
Layanan:
Greet Group Service

Harga:
Rp200.000 / pendamping / hari
```

Pemohon memilih:

```text
Jumlah pendamping = 8
```

Sistem menghitung:

```text
8 x Rp200.000
= Rp1.600.000
```

Maka ditampilkan:

```text
Greet Group Service
8 Pendamping
Rp200.000 / pendamping / hari

TOTAL
Rp1.600.000
```

Jika Pemohon mengubah jumlah menjadi 10:

```text
10 x Rp200.000
= Rp2.000.000
```

Total harus berubah otomatis.

---

# 8. Master Layanan

Master Layanan harus dapat diatur tanpa mengubah source code.

Field yang disarankan:

```text
id
kode_layanan
nama_layanan
deskripsi
minimal_pendamping
maksimal_pendamping
jenis_tarif
harga
satuan
aktif
tanggal_mulai_berlaku
tanggal_akhir_berlaku
created_at
updated_at
```

## Jenis tarif

Contoh:

```text
FIXED
PER_PENDAMPING
PER_HARI
PER_PENDAMPING_PER_HARI
BY_REQUEST
```

Namun untuk kebutuhan saat ini, layanan yang sebelumnya disebut "By Request" menggunakan:

`PER_PENDAMPING_PER_HARI`

Artinya harga otomatis dihitung berdasarkan jumlah pendamping.

---

# 9. Perubahan Tarif

Admin/role yang diberi kewenangan dapat mengubah harga.

Contoh:

Sebelumnya:

```text
Rp200.000 / pendamping / hari
```

Diubah menjadi:

```text
Rp250.000 / pendamping / hari
```

Pengajuan baru menggunakan tarif:

```text
Rp250.000
```

Tetapi transaksi/pengajuan lama **tidak boleh ikut berubah**.

---

# 10. Snapshot Tarif

Ketika pengajuan dibuat, sistem menyimpan tarif yang digunakan pada saat pengajuan.

Contoh:

```text
tarif_master = Rp200.000
jumlah_pendamping = 8
total = Rp1.600.000
```

Jika kemudian Master Tarif berubah menjadi Rp250.000, pengajuan lama tetap:

```text
Rp1.600.000
```

Hal ini penting untuk:

- Audit
- Laporan
- Rekonsiliasi pembayaran
- Histori transaksi
- Menghindari perubahan nilai transaksi lama

---

# 11. Notifikasi

Notifikasi harus berjalan berdasarkan perubahan status.

## Pemohon

### Pengajuan berhasil

```text
Pengajuan Anda berhasil diterima dan sedang menunggu
verifikasi Komersil.
```

### Data tidak lengkap

```text
Pengajuan Anda memerlukan revisi.
Silakan lengkapi data/dokumen.
```

### Commercial menyetujui

```text
Data pengajuan Anda telah dinyatakan lengkap oleh Komersil.
Pengajuan sedang menunggu informasi/persetujuan Operasi.
```

### Operasi menolak

```text
Pengajuan Anda ditolak oleh Operasi.

Alasan:
[alasan penolakan]
```

### Operasi menyetujui

```text
Pengajuan Anda telah disetujui oleh Operasi.

Total pembayaran:
Rp1.600.000

Silakan melakukan pembayaran melalui link pembayaran.
```

### Pembayaran berhasil

```text
Pembayaran pengajuan Anda telah berhasil.
Pengajuan siap diproses untuk pelaksanaan layanan.
```

---

# 12. Notifikasi Komersil

Komersil menerima notifikasi ketika:

- Ada pengajuan baru
- Pemohon melakukan revisi
- Pemohon melengkapi data
- Pengajuan membutuhkan verifikasi

---

# 13. Notifikasi Operasi

Operasi menerima notifikasi ketika:

- Komersil menyetujui pengajuan
- Ada pengajuan baru yang harus diputuskan
- Pembayaran berhasil
- Jadwal pelaksanaan mendekat

---

# 14. Notifikasi AOCH

AOCH menerima notifikasi ketika:

- Pengajuan telah disetujui Operasi
- Pembayaran telah berhasil
- Layanan siap dilaksanakan
- Ada perubahan jadwal/status penting

---

# 15. Pembayaran

Link pembayaran **tidak boleh muncul sebelum Operasi menyetujui pengajuan**.

Alur:

```text
Operasi Setuju
      |
      v
Generate Payment
      |
      v
Payment Link Aktif
      |
      v
Pemohon Bayar
      |
      v
Payment Gateway
      |
      v
Webhook
      |
      v
Status DIBAYAR
```

Sistem sebaiknya mendukung beberapa metode pembayaran sesuai payment gateway yang digunakan, misalnya:

- QRIS
- Virtual Account
- Transfer
- E-wallet
- Metode lain yang tersedia pada payment gateway

---

# 16. Dashboard Pemohon

Dashboard menampilkan:

```text
Total Pengajuan
Menunggu Verifikasi
Menunggu Operasi
Menunggu Pembayaran
Sudah Dibayar
Selesai
Ditolak
```

Daftar pengajuan:

| Nomor | Layanan | Tanggal | Pendamping | Total | Status |
|---|---|---|---:|---:|---|
| #001 | Greet Service | 20-09-2026 | 3 | Rp1.000.000 | Menunggu Operasi |
| #002 | Greet Group | 22-09-2026 | 8 | Rp1.600.000 | Menunggu Pembayaran |

---

# 17. Dashboard Komersil

Menu:

```text
Dashboard
Pengajuan Baru
Perlu Revisi
Verifikasi
Disetujui
Diteruskan ke Operasi
Riwayat
Laporan
```

Statistik:

```text
Pengajuan Baru
Perlu Revisi
Disetujui Hari Ini
Menunggu Operasi
Total Bulan Ini
```

---

# 18. Dashboard Operasi

Menu:

```text
Dashboard
Menunggu Persetujuan
Disetujui
Ditolak
Menunggu Pembayaran
Sudah Dibayar
Jadwal Hari Ini
Jadwal Mendatang
Riwayat
```

---

# 19. Dashboard AOCH

Menu:

```text
Dashboard
Pengajuan Akan Datang
Sudah Dibayar
Belum Acknowledged
Acknowledged
Jadwal Hari Ini
Riwayat
```

---

# 20. Dashboard Administrator

Menu:

```text
Dashboard

User Management
├── User
├── Role
└── Permission

Master Data
├── Master Layanan
├── Master Tarif
├── Master Dokumen
└── Master Parameter

Pembayaran
├── Payment Gateway
├── Payment Method
└── Transaction

Notifikasi
├── Template Notifikasi
└── Notification Log

Audit
└── Audit Log

Laporan
└── Laporan Pengajuan
```

---

# 21. Audit Log

Setiap tindakan penting harus dicatat.

Contoh:

```text
User:
komersil01

Action:
APPROVE_COMMERCIAL

Pengajuan:
REQ-20260911-0001

Status Sebelum:
VERIFIKASI_KOMERSIL

Status Sesudah:
MENUNGGU_OPERASI

Tanggal:
2026-09-11 13:30:00
```

Audit log minimal mencatat:

- User
- Role
- Action
- Nomor pengajuan
- Status sebelum
- Status sesudah
- IP address
- Timestamp
- Catatan/alasan jika ada

---

# 22. Aturan Penting Sistem

1. Pemohon tidak dapat mengubah pengajuan setelah masuk proses verifikasi kecuali diminta revisi.
2. Komersil hanya memvalidasi kelengkapan dan meneruskan ke Operasi.
3. Operasi adalah pihak yang memberikan keputusan operasional.
4. Operasi wajib memberikan alasan ketika menolak.
5. Link pembayaran hanya aktif setelah Operasi menyetujui.
6. Tarif dihitung otomatis berdasarkan Master Tarif.
7. Jumlah pendamping menjadi parameter utama tarif.
8. Jumlah tamu hanya menjadi informasi tambahan.
9. Perubahan Master Tarif tidak boleh mengubah transaksi lama.
10. Semua perubahan status penting dicatat dalam Audit Log.
11. Semua perpindahan status dapat menghasilkan notifikasi.
12. Hak akses setiap role harus menggunakan permission/role-based access control.
13. Data pembayaran harus diperbarui melalui webhook/payment confirmation dari payment gateway.
14. Nomor pengajuan harus unik.
15. Semua transaksi harus memiliki histori status.

---

# 23. Contoh Skenario Lengkap

Pemohon mengajukan:

```text
Layanan:
Greet Group Service

Tanggal:
20 September 2026

Jumlah Pendamping:
8

Harga:
Rp200.000 / orang / hari
```

Sistem otomatis:

```text
8 x Rp200.000
= Rp1.600.000
```

### Tahap 1

Status:

`DIAJUKAN`

Komersil mendapat notifikasi.

### Tahap 2

Komersil memeriksa data.

Jika lengkap:

`DISETUJUI_KOMERSIL`

Pemohon mendapat:

> Data Anda telah lengkap dan sedang menunggu informasi dari Operasi.

### Tahap 3

Pengajuan masuk Operasi.

Operasi memiliki dua pilihan:

```text
[ TOLAK ]       [ SETUJUI ]
```

### Jika ditolak

Status:

`DITOLAK_OPERASI`

Pemohon mendapat alasan.

### Jika disetujui

Status:

`MENUNGGU_PEMBAYARAN`

Sistem menampilkan:

```text
Total:
Rp1.600.000

[ BAYAR SEKARANG ]
```

### Tahap 4

Pemohon melakukan pembayaran.

Payment gateway mengirim webhook.

Status:

`DIBAYAR`

### Tahap 5

AOCH mendapat notifikasi.

AOCH melakukan:

`ACKNOWLEDGED`

### Tahap 6

Layanan dilaksanakan.

Status:

`DILAKSANAKAN`

Setelah selesai:

`SELESAI`

---

# 24. Rekomendasi Arsitektur Django

Aplikasi dapat dibuat menggunakan:

```text
Django
Python
PostgreSQL / MySQL
Django Templates
HTMX
Bootstrap
Redis
Celery (opsional untuk background task)
Payment Gateway
```

Struktur aplikasi yang disarankan:

```text
project/
├── accounts/
├── applications/
├── services/
├── pricing/
├── payments/
├── notifications/
├── operations/
├── commercial/
├── aoch/
├── audit/
├── reports/
└── core/
```

Role menggunakan Django Groups/Permissions:

```text
PEMOHON
KOMERSIL
OPERASI
AOCH
ADMINISTRATOR
```

---

# 25. Model Data Utama

Minimal model:

```text
User
Role
ApplicantProfile

Service
ServicePricing

Application
ApplicationDocument
ApplicationStatusHistory

Payment
PaymentTransaction

Notification
NotificationTemplate

AuditLog
```

Relasi utama:

```text
User
  |
  +--- ApplicantProfile
  |
  +--- Role

Application
  |
  +--- Applicant
  +--- Service
  +--- Pricing Snapshot
  +--- Documents
  +--- Status History
  +--- Payment
  +--- Notifications
  +--- Audit Log
```

---

# 26. Prinsip Utama Sistem

Sistem harus memisahkan dengan jelas:

```text
DATA PEMOHON
      ↓
VERIFIKASI KOMERSIL
      ↓
PERSETUJUAN OPERASI
      ↓
PEMBAYARAN
      ↓
INFORMASI AOCH
      ↓
PELAKSANAAN
      ↓
SELESAI
```

Sedangkan:

```text
MASTER LAYANAN
MASTER TARIF
MASTER DOKUMEN
MASTER USER
KONFIGURASI PEMBAYARAN
```

dikelola dari sisi Administrator.

---

# 27. Prinsip Tarif

Tarif harus bersifat configurable.

Contoh:

```text
Greet Service
Rp1.000.000 / hari

Greet & Desk Service
Rp1.500.000 / hari

Greet Group Service
Rp200.000 / pendamping / hari
```

Administrator dapat mengubah:

```text
Rp200.000
       ↓
Rp250.000
```

Tanpa mengubah program.

Perhitungan:

```text
total = jumlah_pendamping × harga_per_pendamping × jumlah_hari
```

Jika hanya satu hari:

```text
total = jumlah_pendamping × harga_per_pendamping
```

---

# 28. Status Pembayaran

Status pembayaran terpisah dari status pengajuan.

```text
UNPAID
PENDING
PAID
FAILED
EXPIRED
CANCELLED
REFUNDED
```

Ini penting karena:

- Status pengajuan menunjukkan proses bisnis.
- Status pembayaran menunjukkan proses keuangan.

Keduanya tidak boleh digabung menjadi satu field.

---

# 29. Target UI

UI harus:

- Mobile friendly
- Responsive
- Mudah digunakan oleh Pemohon
- Dashboard berbeda berdasarkan role
- Menampilkan status dengan jelas
- Menampilkan notifikasi
- Memiliki timeline proses pengajuan
- Mengurangi input manual
- Menghitung tarif otomatis
- Menghindari kesalahan perhitungan

Contoh timeline:

```text
✓ Pengajuan Dibuat
      ↓
✓ Verifikasi Komersil
      ↓
✓ Disetujui Komersil
      ↓
● Menunggu Operasi
      ↓
○ Pembayaran
      ↓
○ AOCH
      ↓
○ Pelaksanaan
      ↓
○ Selesai
```

---

# 30. Kesimpulan

Aplikasi memiliki 5 role:

**Pemohon → Komersil → Operasi → AOCH → Administrator**

Alur utama:

**Pemohon mengajukan → Komersil memeriksa kelengkapan → Komersil meneruskan ke Operasi → Operasi menolak atau menyetujui → jika disetujui link pembayaran muncul → pembayaran berhasil → AOCH mendapat informasi → layanan dilaksanakan → selesai.**

Tarif tidak hard-code.

**Jumlah pendamping menjadi parameter tarif**, dan harga per orang dapat diubah melalui Master Tarif.

Setiap pengajuan menyimpan **snapshot tarif**, sehingga perubahan tarif di masa depan tidak mengubah transaksi lama.
