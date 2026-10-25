#!/bin/bash

# Paths
DB_NAME="weather_data.db"
BACKUP_DIR="/opt/weather/backups"
BACKUP_PREFIX="weather_backup"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Timestamp format: YYYY-MM-DD_HH-MM-SS
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# Full backup filename
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_PREFIX}_${TIMESTAMP}.db"

# Copy the DB
cp "/opt/weather/$DB_NAME" "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"

# Keep only the 10 most recent backups
echo "🧹 Cleaning up old backups..."
ls -1t "$BACKUP_DIR"/${BACKUP_PREFIX}_*.db | tail -n +11 | xargs -r rm -v

echo "✅ Backup cleanup done."
