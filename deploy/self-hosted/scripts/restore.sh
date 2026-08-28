#!/usr/bin/env sh

set -eu

if [ "$#" -ne 3 ]; then
  echo "Usage:" >&2
  echo "  RESTORE_CONFIRM=YES $0 BACKUP_DIR TARGET_DB_URL TARGET_STORAGE_VOLUME" >&2
  exit 1
fi

BACKUP_DIR="$1"
TARGET_DB_URL="$2"
TARGET_STORAGE_VOLUME="$3"

if [ "${RESTORE_CONFIRM:-}" != "YES" ]; then
  echo "Restore refused." >&2
  echo "Set RESTORE_CONFIRM=YES after verifying all target values." >&2
  exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory does not exist: $BACKUP_DIR" >&2
  exit 1
fi

BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd -P)"

for file in \
  SHA256SUMS \
  roles.sql \
  schema.sql \
  data.sql \
  migration-schema.sql \
  migration-data.sql \
  storage.tar.gz; do
  if [ ! -s "$BACKUP_DIR/$file" ]; then
    echo "Missing or empty backup file: $file" >&2
    exit 1
  fi
done

command -v psql >/dev/null 2>&1 || {
  echo "psql is required" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || {
  echo "Docker is required" >&2
  exit 1
}

echo "Verifying backup checksums..."

(
  cd "$BACKUP_DIR"
  sha256sum --check SHA256SUMS
)

if ! docker volume inspect "$TARGET_STORAGE_VOLUME" >/dev/null 2>&1; then
  echo "Target Storage volume does not exist: $TARGET_STORAGE_VOLUME" >&2
  exit 1
fi

ACTIVE_STORAGE_VOLUME="$(
  docker inspect supabase-storage \
    --format '{{range .Mounts}}{{if eq .Destination "/var/lib/storage"}}{{.Name}}{{end}}{{end}}' \
    2>/dev/null ||
    true
)"

if [ -n "$ACTIVE_STORAGE_VOLUME" ] &&
  [ "$TARGET_STORAGE_VOLUME" = "$ACTIVE_STORAGE_VOLUME" ]; then
  echo "Refusing to overwrite the active Storage volume." >&2
  exit 1
fi

if ! docker run --rm \
  --volume "$TARGET_STORAGE_VOLUME:/target" \
  alpine:3.22 \
  sh -c 'test -z "$(find /target -mindepth 1 -print -quit)"'; then
  echo "Target Storage volume is not empty." >&2
  exit 1
fi

echo "Checking target database connection..."

psql \
  --dbname "$TARGET_DB_URL" \
  --variable ON_ERROR_STOP=1 \
  --command 'select current_database(), current_user;' \
  >/dev/null

echo
echo "Restore target:"
echo "  Backup: $BACKUP_DIR"
echo "  Storage volume: $TARGET_STORAGE_VOLUME"
echo
echo "Restoring PostgreSQL..."

psql \
  --single-transaction \
  --variable ON_ERROR_STOP=1 \
  --file "$BACKUP_DIR/roles.sql" \
  --file "$BACKUP_DIR/schema.sql" \
  --command 'set session_replication_role = replica' \
  --file "$BACKUP_DIR/data.sql" \
  --dbname "$TARGET_DB_URL"

echo "Restoring migration history..."

psql \
  --single-transaction \
  --variable ON_ERROR_STOP=1 \
  --file "$BACKUP_DIR/migration-schema.sql" \
  --file "$BACKUP_DIR/migration-data.sql" \
  --dbname "$TARGET_DB_URL"

echo "Restoring Storage files..."

docker run --rm \
  --volume "$TARGET_STORAGE_VOLUME:/target" \
  --volume "$BACKUP_DIR:/backup:ro" \
  alpine:3.22 \
  tar -xzf /backup/storage.tar.gz -C /target

echo "Restore completed."
echo "Start the target stack and run application-level verification."
