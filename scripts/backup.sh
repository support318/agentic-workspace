#!/bin/bash
# Backup script for agentic-workspace configurations

set -e

SERVER="candid@192.168.40.100"
WEBHOOK_DIR="/home/candid/webhooks"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "💾 Creating backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup .env file
echo "Backing up .env..."
ssh $SERVER "cat $WEBHOOK_DIR/.env" > "$BACKUP_DIR/env_$TIMESTAMP.txt"

# Backup systemd service
echo "Backing up service file..."
scp $SERVER:/etc/systemd/system/$SERVICE_NAME.service "$BACKUP_DIR/" 2>/dev/null || true

# Backup recent logs
echo "Backing up recent logs..."
ssh $SERVER "sudo journalctl -u agentic-webhooks -n 1000 --no-pager" > "$BACKUP_DIR/logs_$TIMESTAMP.txt"

# Create archive
echo "Creating archive..."
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" "$BACKUP_DIR"/*_$TIMESTAMP.*

# Clean up individual files
rm -f "$BACKUP_DIR"/*_$TIMESTAMP.*

echo ""
echo "✅ Backup created: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
echo ""
echo "To restore:"
echo "  scp $BACKUP_DIR/backup_$TIMESTAMP.tar.gz $SERVER:/tmp/"
echo "  ssh $SERVER 'cd /home/candid/webhooks && tar -xzf /tmp/backup_$TIMESTAMP.tar.gz'"
