# Deployment PAS Bandara

Dokumentasi alur development → staging → production.

## Ringkasan Lingkungan

| Lingkungan | Lokasi            | Settings                              | Database          | Web server   |
|------------|-------------------|---------------------------------------|-------------------|--------------|
| Development| Laptop            | `config.settings.development`          | MariaDB lokal     | `runserver`  |
| Staging    | Server pengujian  | `config.settings.development`/`production` | MariaDB staging | Gunicorn + Nginx |
| Production | Server utama       | `config.settings.production`           | MariaDB (Docker)  | Docker (Gunicorn + Nginx) |

## Struktur Settings

```
config/settings/
├── __init__.py      # memilih env berdasarkan DJANGO_ENV
├── base.py          # setting bersama
├── development.py   # DEBUG on, host lokal
└── production.py    # DEBUG off, hardening lengkap
```

Pilih environment lewat variabel:

```bash
# development (default)
DJANGO_ENV=development python manage.py runserver

# production
DJANGO_SETTINGS_MODULE=config.settings.production gunicorn config.wsgi
```

`.env` berisi nilai per lingkungan (TIDAK di-commit). Salin dari `.env.example`:

```bash
cp .env.example .env
```

## 1. Development (laptop)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# siapkan database lokal
mysql -u <user> -p -e "CREATE DATABASE pas_bandara CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
# isi .env (DB_ENGINE=mysql, DB_NAME=pas_bandara, DB_USER, DB_PASSWORD, DB_HOST=127.0.0.1)

python manage.py migrate
python manage.py seed_master
python manage.py seed_payment_methods
python manage.py seed_workflow
python manage.py createsuperuser

python manage.py runserver
```

## 2. Staging (server pengujian)

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# restart gunicorn
sudo systemctl restart pas-gunicorn
```

## 3. Production (server utama, via Docker)

> Skeleton Docker (`Dockerfile`, `docker-compose.yml`, Nginx config) akan
> ditambahkan pada Tahap Production. Service yang direncanakan:
> `web` (Gunicorn), `nginx`, `db` (MariaDB), `redis`, `backup` (cron mdump DB + rsync media).

```bash
# di server utama
git pull
cp .env.example .env.production   # isi kredensial production
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

## Alur Kerja Harian

```
laptop (dev)       → edit → runserver → tes → git commit → git push
server staging     → git pull → migrate → tes
server production  → git pull → docker compose up -d --build
```

## Catatan Keamanan

- `.env`, `.env.*` dan `media/` **tidak pernah** masuk Git (lihat `.gitignore`).
- Credential database & payment ada di environment variable, bukan source code.
- `staticfiles/` hasil `collectstatic` tidak di-commit.
- Dokumen sensitif (`media/`) harus dibackup terpisah, tidak via Git.
