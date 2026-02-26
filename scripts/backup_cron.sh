#!/usr/bin/env bash
# Automated PostgreSQL backup with rotation.
# Designed to run inside a postgres:17 container with access to the db service.
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-lakshmi}"
POSTGRES_DB="${POSTGRES_DB:-lakshmi}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup: $BACKUP_FILE"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

# Validate backup file size (< 1KB likely means failure)
FILESIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo 0)
if [ "$FILESIZE" -lt 1024 ]; then
    echo "[$(date)] ERROR: Backup file too small (${FILESIZE} bytes), likely failed" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup OK ($SIZE). Rotating (keep ${RETENTION_DAYS}d)..."
find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete

REMAINING=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
echo "[$(date)] Done. Total backups: $REMAINING"
