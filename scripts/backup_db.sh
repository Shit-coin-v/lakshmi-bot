#!/usr/bin/env bash
# Backup PostgreSQL database
# Usage: ./scripts/backup_db.sh
# Or via docker: docker compose exec db ./scripts/backup_db.sh
#
# Environment variables:
#   POSTGRES_USER - database user (default: lakshmi)
#   POSTGRES_DB   - database name (default: lakshmi)
#   BACKUP_DIR    - backup directory (default: /var/lib/postgresql/backups)

set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-lakshmi}"
POSTGRES_DB="${POSTGRES_DB:-lakshmi}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/postgresql/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Creating backup: $BACKUP_FILE"
pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

echo "Backup created successfully: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# Backup Metabase H2 database (O10)
METABASE_BACKUP="${BACKUP_DIR}/metabase_${TIMESTAMP}.db"
if docker compose cp metabase:/metabase-data/metabase.db "$METABASE_BACKUP" 2>/dev/null; then
    echo "Metabase backup created: $METABASE_BACKUP"
    echo "Size: $(du -h "$METABASE_BACKUP" | cut -f1)"
else
    echo "Warning: Metabase backup skipped (container not running or file not found)"
fi
