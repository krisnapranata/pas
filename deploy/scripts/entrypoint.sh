#!/usr/bin/env bash
# Entrypoint production: migrate, collectstatic, lalu jalankan gunicorn.
set -e

echo "== Menjalankan migrate =="
python manage.py migrate --noinput

echo "== Mengumpulkan static files =="
python manage.py collectstatic --noinput

echo "== Menjalankan seed (idempotent) =="
python manage.py seed_master || true
python manage.py seed_payment_methods || true
python manage.py seed_workflow || true

echo "== Menjalankan Gunicorn =="
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
