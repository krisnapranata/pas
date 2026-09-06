#!/usr/bin/env bash
# Script deploy staging: pull, install deps, migrate, collectstatic, restart gunicorn.
# Jalankan di server staging dalam virtualenv yang sudah ada.
set -e

echo "== Pull kode terbaru =="
git pull

echo "== Install dependencies =="
source venv/bin/activate || source .venv/bin/activate
pip install -r requirements.txt

echo "== Migrasi database =="
python manage.py migrate --noinput

echo "== Collect static =="
python manage.py collectstatic --noinput

echo "== Seed master data (idempotent) =="
python manage.py seed_master || true
python manage.py seed_payment_methods || true
python manage.py seed_workflow || true

echo "== Restart Gunicorn =="
sudo systemctl restart pas-gunicorn || echo "Gunakan supervisor/pid manual sesuai setup staging Anda."

echo "== Selesai =="
