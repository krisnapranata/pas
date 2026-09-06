# Backup service: dump MariaDB + rsync media secara berkala (cron).
FROM alpine:3.20

RUN apk add --no-cache \
    mariadb-client \
    rsync \
    busybox-suid \
    tzdata

COPY deploy/scripts/backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

RUN mkdir -p /backup

CMD ["crond", "-f"]
