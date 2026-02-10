#!/bin/bash
# Deployment script for agentic-workspace to production server

set -e

SERVER="candid@192.168.40.100"
SERVER_DIR="/home/candid/agentic-workspace"
WEBHOOK_DIR="/home/candid/webhooks"
SERVICE_NAME="agentic-webhooks"

echo "🚀 Starting deployment to $SERVER..."

# 1. Create directories on server
echo "📁 Creating directories on server..."
ssh $SERVER "mkdir -p $SERVER_DIR/directives $SERVER_DIR/execution $SERVER_DIR/tests $SERVER_DIR/logs $WEBHOOK_DIR"

# 2. Copy files to server
echo "📦 Copying files to server..."
scp execution/*.py $SERVER:$SERVER_DIR/execution/
scp directives/*.md $SERVER:$SERVER_DIR/directives/
scp tests/*.py $SERVER:$SERVER_DIR/tests/
scp tests/integration/*.py $SERVER:$SERVER_DIR/tests/integration/
scp requirements.txt $SERVER:$SERVER_DIR/
scp pytest.ini $SERVER:$SERVER_DIR/
scp .env.example $SERVER:$SERVER_DIR/

# 3. Copy webhook server to its own directory
echo "📦 Copying webhook server..."
scp execution/webhook_server.py $SERVER:$WEBHOOK_DIR/
scp services/$SERVICE_NAME.service $SERVER:/tmp/

# 4. Set up Python virtual environment on server
echo "🐍 Setting up Python virtual environment..."
ssh $SERVER << 'ENDSSH'
cd /home/candid/webhooks

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r /home/candid/agentic-workspace/requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp /home/candid/agentic-workspace/.env.example .env
    echo "⚠️  Please edit .env with your API credentials!"
fi
ENDSSH

# 5. Set up systemd service
echo "🔧 Setting up systemd service..."
ssh $SERVER << 'ENDSSH'
# Install service file
sudo mv /tmp/agentic-webhooks.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (don't start yet)
sudo systemctl enable agentic-webhooks.service
ENDSSH

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. SSH to server: ssh $SERVER"
echo "2. Edit .env: nano $WEBHOOK_DIR/.env"
echo "3. Start service: sudo systemctl start $SERVICE_NAME"
echo "4. Check status: sudo systemctl status $SERVICE_NAME"
echo "5. View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Webhook endpoints:"
echo "- Calendar: http://$SERVER:8080/webhook/calendar-ghl"
echo "- Health: http://$SERVER:8080/health"
