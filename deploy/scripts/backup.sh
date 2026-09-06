#!/bin/sh
# Backup database dump + media. Dijalankan cron setiap hari (default 02:00).
set -e

STAMP=$(date +%F_%H%M%S)
DEST=/backup
RETAIN_DAYS=${BACKUP_RETAIN_DAYS:-14}

mkdir -p "$DEST/db" "$DEST/media"

echo "[$STAMP] Backup dimulai"

# Dump database
mysqldump \
  -h "${DB_HOST:-db}" \
  -u "${DB_USER:-pas_user}" \
  -p"${DB_PASSWORD:-change-me}" \
  --single-transaction --routines --triggers \
  "${DB_NAME:-pas_bandara}" > "$DEST/db/pas_bandara_${STAMP}.sql"

gzip "$DEST/db/pas_bandara_${STAMP}.sql"

# Rsync media (dari volume yang dishare — opsional, sesuaikan source path)
if [ -d /media ]; then
    rsync -a --delete /media/ "$DEST/media/"
fi

# Hapus backup lama
find "$DEST/db" -name "*.sql.gz" -mtime +$RETAIN_DAYS -delete

echo "[$STAMP] Backup selesai:"
ls -la "$DEST/db" | tail -5
