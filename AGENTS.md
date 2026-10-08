# AGENTS.md — PAS Bandara

Django 6 + Bootstrap 5 app (Indonesian UI, `LANGUAGE_CODE=id`, `TIME_ZONE=Asia/Jakarta`).
Custom user model: `accounts.User` (roles: PEMOHON, KOMERSIL, OPERASI, AOCH, AVSEC, ADMINISTRATOR).

## Setup & run
- Python venv at `./venv` — use `./venv/bin/python manage.py ...` (no activate needed).
- `.env` at repo root is required (`DB_ENGINE`, `DB_*`, `DJANGO_ENV`); `.env.example` documents it. Default settings module: development DB is local MariaDB (`pas_bandara`, user `sik`), tests need a reachable MySQL.
- Run dev server: `./venv/bin/python manage.py runserver` (reads `.env` automatically, no need to set `DJANGO_SETTINGS_MODULE`).

## Tests & checks
- All tests: `./venv/bin/python manage.py test`
- One app: `./venv/bin/python manage.py test pas`
- Focus a test: `./venv/bin/python manage.py test pas.tests.VerifikasiPasTests.test_xxx`
- `-k "verifikasi"` also works for name filtering (Django 6).
- Always run `python manage.py test pas` (or affected app) after editing views/models.

## Structure quirks
- Settings are split: `config/settings/base.py`, `development.py`, `production.py`.
- Apps: `accounts`, `pas`, `pembayaran`, `dashboard`, `audit`, `notifikasi`. Templates live in top-level `templates/`, static in `static/`, per-app overrides under each app.
- Custom template tag `{% load rupiah %}` lives in `accounts/templatetags/rupiah.py` and formats IDR amounts; required at the top of any template that uses it.
- Dev DB is MySQL (`mysqlclient`); `DB_ENGINE=sqlite` also supported via `.env`.
- Status flow of an pengajuan: DRAFT → DIAJUKAN → VERIFIKASI_KOMERSIL → DISETUJUI_KOMERSIL → VERIFIKASI_OPERASI → PAS_TERBIT → SELESAI; keep `status_masa_berlaku` (PAS model property) semantics in mind when touching verification/notification code.
- Nomor PAS can be reused across pengajuan once the old card is returned/SELESAI — lookups must exclude those (see `pas/views.py::verifikasi_pas`).
- Email backend is console in development; Redis/gunicorn only in production (`config/settings/production.py`).

## Deploy
- Docker: `docker compose up` (see `DEPLOY.md`, `Dockerfile`); production settings need `DJANGO_SETTINGS_MODULE=config.settings.production`.
- Demo accounts/seed: `python manage.py seed_demo` (accounts), `python manage.py seed_master` (pas); credentials in `demo_users.txt`.
