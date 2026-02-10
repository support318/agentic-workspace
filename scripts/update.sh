#!/bin/bash
# Update script for agentic-workspace on production server

set -e

SERVER="candid@192.168.40.100"
WEBHOOK_DIR="/home/candid/webhooks"
SERVICE_NAME="agentic-webhooks"

echo "🔄 Updating agentic-workspace on $SERVER..."

# Pull latest code (if using git)
# ssh $SERVER "cd $WEBHOOK_DIR && git pull"

# Or copy files directly
echo "📦 Copying updated files..."
scp execution/*.py $SERVER:$WEBHOOK_DIR/ 2>/dev/null || true
scp requirements.txt $SERVER:$WEBHOOK_DIR/ 2>/dev/null || true

# Restart service
echo "🔄 Restarting service..."
ssh $SERVER "sudo systemctl restart $SERVICE_NAME"

# Wait for service to start
sleep 2

# Check status
echo "📊 Service status:"
ssh $SERVER "sudo systemctl status $SERVICE_NAME --no-pager"

echo ""
echo "✅ Update complete!"
echo "View logs: ssh $SERVER 'sudo journalctl -u $SERVICE_NAME -f'"
