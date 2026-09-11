# PAS Bandara

Sistem Manajemen Permintaan PAS (Pass) Bandara — platform digital end-to-end untuk mengelola permintaan izin masuk area bandara: pendaftaran pemohon, pengajuan, verifikasi dokumen, persetujuan operasi, pembayaran, hingga penerbitan PAS.

Dibangun dengan Django 6 + Bootstrap 5.

## Daftar Isi

- [Fitur](#fitur)
- [Peran Pengguna](#peran-pengguna)
- [Alur Bisnis](#alur-bisnis)
- [Teknologi](#teknologi)
- [Struktur Proyek](#struktur-proyek)
- [Persyaratan](#persyaratan)
- [Instalasi & Menjalankan (Development)](#instalasi--menjalankan-development)
- [Seed Data](#seed-data)
- [Akun Demo](#akun-demo)
- [Konfigurasi (Environment)](#konfigurasi-environment)
- [Deployment (Docker)](#deployment-docker)
- [Pembayaran](#pembayaran)
- [Notifikasi & Audit](#notifikasi--audit)

## Fitur

- **Portal per peran** — pemohon, komersil, operasi, AOCH, dan administrator punya antarmuka sesuai tugasnya.
- **Pengajuan PAS** — pemilihan layanan, data PIC, jumlah tamu/pendamping, upload ID card pendamping.
- **Verifikasi dokumen** — pengecekan ID card pendamping oleh Komersil (pengecekan pertama) dan Operasi (pengecekan kedua).
- **Persetujuan berjenjang** — Komersil → Operasi, dengan opsi revisi/tolak + daftar hitam.
- **Pembayaran multi-metode** — QRIS, Virtual Account, Transfer Manual, Tunai, E-Wallet, Kartu, OTC (provider abstrak, saat ini `manual`).
- **Verifikasi bukti bayar** — upload bukti transfer + verifikasi petugas (upload ≠ lunas).
- **Penerbitan PAS** — Operasi menerbitkan PAS setelah pengajuan disetujui & dibayar; pemohon diberitahu untuk mengambil kartu fisik.
- **Notifikasi in-app + email** — status berubah otomatis memberi tahu pemohon/role terkait.
- **Audit log** — seluruh perubahan status tercatat.

## Peran Pengguna

| Role | Tugas |
|------|-------|
| `PEMOHON` | Registrasi, buat pengajuan, upload ID card, bayar, pantau status |
| `KOMERSIL` | Verifikasi dokumen (pengecekan pertama) & verifikasi bukti pembayaran |
| `OPERASI` | Persetujuan akhir, pengecekan kedua ID card, menerbitkan PAS |
| `AOCH` | Monitoring & acknowledgement |
| `ADMINISTRATOR` | Superuser / akses penuh |

## Alur Bisnis

```
Pemohon ajukan
   → Komersil verifikasi dokumen (Valid/Revisi)
   → Operasi setujui (atau tolak)
   → Pemohon bayar + upload bukti (lihat cara transfer & no. rekening)
   → Komersil verifikasi bukti bayar (Valid → DIBAYAR)
   → Operasi terbitkan PAS (PAS_TERBIT)
   → Pemohon ambil kartu fisik di Operasi
```

Timeline status pengajuan yang tampil ke pemohon:

```
Draft → Diajukan → Verifikasi Komersil → Disetujui Komersil
      → Menunggu Operasi → Menunggu Pembayaran → Sudah Dibayar → PAS Diterbitkan
```

## Teknologi

- Python 3.12
- Django 6.1
- MySQL/MariaDB (atau SQLite untuk development cepat)
- Bootstrap 5.3 (tema custom `static/css/pas-theme.css`)
- HTMX, qrcode, Pillow

## Struktur Proyek

```
├── accounts/        # User custom, login/register/profil
├── pas/             # Layanan, Pengajuan, DokumenPendamping, StatusRiwayat, DaftarHitam
├── pembayaran/      # Invoice, Transaksi, PembayaranManual, Refund, Webhook, PaymentService
├── dashboard/       # Dashboard per role, statistik, laporan, export CSV
├── audit/           # Audit log
├── notifikasi/      # Notifikasi in-app + email
├── config/          # settings (base/development/production), urls, wsgi
├── templates/       # Template HTML
├── static/          # CSS/JS
├── media/           # File dokumen (gitignored)
└── deploy/          # Dockerfile, docker-compose, nginx, backup
```

## Persyaratan

- Python 3.12
- MariaDB/MySQL (opsional — bisa pakai SQLite)
- `libmysqlclient-dev` (jika pakai MySQL)

## Instalasi & Menjalankan (Development)

```bash
# 1. Buat & aktifkan virtualenv
python -m venv venv
source venv/bin/activate

# 2. Install dependensi
pip install -r requirements.txt

# 3. Siapkan environment
cp .env.example .env
#   Sesuaikan .env (DB_ENGINE=sqlite untuk paling cepat, atau mysql)

# 4. Migrasi database
python manage.py migrate

# 5. Seed master data (layanan, daftar hitam, metode pembayaran, user demo)
python manage.py seed_master
python manage.py seed_payment_methods
python manage.py seed_demo

# 6. Jalankan server
python manage.py runserver
```

Buka `http://127.0.0.1:8000` (redirect ke halaman login).

> Saat development, email terkirim ke console (lihat output terminal `runserver`).

## Seed Data

| Command | Isi |
|---------|-----|
| `python manage.py seed_master` | Layanan (Greet, Greet & Desk, Greet Group) + contoh daftar hitam |
| `python manage.py seed_payment_methods` | Metode pembayaran (QRIS, VA, Transfer Manual, Tunai, E-Wallet, dsb.) |
| `python manage.py seed_demo` | User demo + contoh pengajuan & invoice |

## Akun Demo

| Username | Role | Password |
|----------|------|----------|
| `admin` | ADMINISTRATOR | `admin123` |
| `pemohon1` | PEMOHON | `pemohon123` |
| `komersil1` | KOMERSIL | `demo123` |
| `operasi1` | OPERASI | `demo123` |
| `aoch1` | AOCH | `demo123` |

## Konfigurasi (Environment)

Semua konfigurasi lewat `.env` (lihat `.env.example`). Yang penting:

| Variabel | Keterangan |
|----------|-----------|
| `DJANGO_ENV` | `development` / `production` |
| `DB_ENGINE` | `sqlite` / `mysql` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Koneksi MySQL |
| `PAYMENT_PROVIDER` | Provider pembayaran (default `manual`) |
| `PAYMENT_WEBHOOK_SECRET` | Secret untuk validasi webhook |
| `PAS_BASE_URL` | URL publik aplikasi |
| `ALLOWED_HOSTS` | Host yang diizinkan (pisahkan koma) |

Settings dipilih otomatis: `DJANGO_ENV=production` → `config.settings.production`, selain itu `config.settings.development`.

## Deployment (Docker)

Stack produksi: `web` (Django + Gunicorn) + `nginx` + `db` (MariaDB) + `redis` + `backup`. Entrypoint otomatis menjalankan `migrate`, `collectstatic`, dan seed master (idempotent).

Gunicorn berjalan di **port 8005** (internal container, tidak di-publish ke host). Alur akses:

```
nginx-proxy-manager (80/443 host) → nginx PAS (port 80, internal) → web/gunicorn (port 8005, internal)
```

### Langkah deploy di server

```bash
# 1. Ambil kode terbaru
git pull

# 2. Buat file environment dari template
cp deploy/env.production.example .env.production

# 3. Edit nilai wajib
nano .env.production
```

**Nilai yang WAJIB diganti** di `.env.production` (jangan biarkan `change-me`):

| Variabel | Keterangan |
|----------|-----------|
| `SECRET_KEY` | Generate random: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DB_PASSWORD` | Password user database |
| `DB_ROOT_PASSWORD` | Password root MariaDB |

**Nilai yang sudah benar** (jangan diubah): `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DB_HOST=db`, `DB_ENGINE=mysql`.

```bash
# 4. Build & jalankan (perhatikan flag --env-file!)
docker compose --env-file .env.production up -d --build

# 5. Pantau startup (migrate + collectstatic berjalan otomatis)
docker compose logs -f web
```

> **Penting — flag `--env-file`**: tanpanya, interpolasi `${DB_*}` di `docker-compose.yml` membaca `.env` (default), bukan `.env.production`, sehingga kredensial container DB (`MARIADB_*`) bisa tidak sinkron dengan aplikasi.

> **`.env.production` sudah di-gitignore** — dibuat manual di server, tidak ikut ter-commit.

### Akses lewat nginx-proxy-manager

Nginx PAS tidak mem-publish port 80/443 (sudah dipakai NPM), melainkan di-attach ke network `proxy_default`:

1. Di UI **nginx-proxy-manager**, tambah **Proxy Host**:
   - Domain: `pas.lop-aoch.online`
   - Forward hostname: `pas-nginx-1` (nama container nginx PAS)
   - Forward port: `80`
2. Opsional: aktifkan **SSL** via Let's Encrypt.
3. Pastikan DNS `pas.lop-aoch.online` sudah punya A-record ke IP server.

### Port & konflik

- Port **3306** (DB): service `db` tidak punya `ports:` → hanya internal network, tidak bentrok dengan host.
- Port **8005** (Gunicorn): internal container, tidak dipublish.
- Port **80/443**: dipegang nginx-proxy-manager; nginx PAS tidak publish.
- Akses via IP langsung `http://<ip>` tetap butuh host di `ALLOWED_HOSTS` & `CSRF_TRUSTED_ORIGINS` (sudah disiapkan di template).

## Pembayaran

- **Abstraksi provider** ada di `pembayaran/services.py` (`BasePaymentProvider` + `PaymentService`).
- Saat ini `PAYMENT_PROVIDER=manual` (fallback) — tidak membuat charge nyata.
- Metode otomatis (QRIS/VA) bergantung pada **webhook** provider (`/pembayaran/webhook/<provider>/`) yang memvalidasi signature, nominal, dan idempotency.
- Metode manual (Transfer Manual/Tunai): pemohon upload bukti → status `PENDING` → petugas verifikasi `Valid/Tidak Valid`.

## Notifikasi & Audit

- `notifikasi/services.py` menyediakan `notify(user, ...)` dan `notify_role(role, ...)` untuk notifikasi in-app + email.
- Semua perubahan status/aksi dicatat lewat `audit.models.log_action`.
