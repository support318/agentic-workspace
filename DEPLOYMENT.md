# Deployment Guide - Agentic Webhook Server

This guide covers deploying the agentic webhook server to production.

## Prerequisites

### Server Requirements
- Ubuntu/Debian Linux server
- Python 3.8+
- SSH access
- sudo privileges

### Before Deploying

1. **Get Google OAuth Credentials**
   ```bash
   # On your local machine
   # 1. Go to Google Cloud Console
   # 2. Create OAuth 2.0 credentials (Desktop app)
   # 3. Download credentials.json
   # 4. Transfer to server securely
   ```

2. **Get GHL API Token**
   - Log into GoHighLevel
   - Go to Settings > API
   - Generate/refresh API token
   - Note: Token from n8n was `pit-10e989e3-51b5-4787-bccb-f12d284eda13`

3. **Configure DNS (optional)**
   ```
   webhook.candidstudios.net → 192.168.40.100
   ```

## Deployment Steps

### Step 1: Initial Deployment

```bash
# From local machine
cd ~/agentic-workspace
bash scripts/deploy.sh
```

This will:
- Create directories on server
- Copy files to server
- Set up Python virtual environment
- Install dependencies
- Configure systemd service

### Step 2: Configure Environment

```bash
# SSH to server
ssh candid@192.168.40.100

# Edit environment file
cd /home/candid/webhooks
nano .env
```

Add your credentials:
```bash
# GoHighLevel
GHL_API_TOKEN=your_actual_token_here
GHL_LOCATION_ID=your_location_id

# Google Calendar
GOOGLE_CALENDAR_ID=support@candidstudios.net
GOOGLE_CREDENTIALS_PATH=/home/candid/webhooks/credentials.json

# Webhook Server
PORT=8080
DEBUG=False
WEBHOOK_SECRET=your_random_secret_here
ALLOWED_IPS=127.0.0.1,webhook.gohighlevel.com
```

### Step 3: Set Up Google Credentials

```bash
# Transfer credentials file to server (from your local machine)
scp ~/Downloads/credentials.json candid@192.168.40.100:/home/candid/webhooks/

# On server, set correct permissions
chmod 600 /home/candid/webhooks/credentials.json
```

### Step 4: Start Service

```bash
# Start the service
sudo systemctl start agentic-webhooks

# Enable to start on boot
sudo systemctl enable agentic-webhooks

# Check status
sudo systemctl status agentic-webhooks
```

### Step 5: Verify Deployment

```bash
# Test health endpoint
curl http://localhost:8080/health

# Run connection tests
cd ~/agentic-workspace
bash scripts/test_connection.sh

# Test webhook (from local machine)
WEBHOOK_URL=http://192.168.40.100:8080/webhook/calendar-ghl \
  bash scripts/test_webhook.sh
```

## Monitoring

### View Logs

```bash
# Real-time logs
sudo journalctl -u agentic-webhooks -f

# Last 100 lines
sudo journalctl -u agentic-webhooks -n 100

# Since today
sudo journalctl -u agentic-webhooks --since today

# Filter by log level
sudo journalctl -u agentic-webhooks -p err
```

### Check Metrics

```bash
# Metrics endpoint
curl http://localhost:8080/metrics | jq .

# Detailed status
curl http://localhost:8080/status | jq .
```

## Updating Code

### Quick Update

```bash
# From local machine
cd ~/agentic-workspace
bash scripts/update.sh
```

### Manual Update

```bash
# 1. Copy updated files
scp execution/*.py candid@192.168.40.100:/home/candid/webhooks/

# 2. Restart service
ssh candid@192.168.40.100 'sudo systemctl restart agentic-webhooks'
```

## Backup and Restore

### Backup

```bash
cd ~/agentic-workspace
bash scripts/backup.sh
```

### Restore

```bash
# Copy backup to server
scp backups/backup_YYYYMMDD_HHMMSS.tar.gz candid@192.168.40.100:/tmp/

# Extract on server
ssh candid@192.168.40.100
cd /home/candid/webhooks
tar -xzf /tmp/backup_*.tar.gz
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status agentic-webhooks

# View error logs
sudo journalctl -u agentic-webhooks -p err -n 50

# Check if port is in use
sudo lsof -i :8080
```

### Import Errors

```bash
# Reinstall dependencies
cd /home/candid/webhooks
source venv/bin/activate
pip install -r requirements.txt
```

### Google Calendar Not Working

```bash
# Test OAuth flow manually
cd /home/candid/webhooks
source venv/bin/activate
python3 -c "
from execution.google_calendar import GoogleCalendarAPI
api = GoogleCalendarAPI()
events = api.list_events(max_results=1)
print(events)
"
```

### GHL API Token Expired

Update `.env` and restart:
```bash
nano /home/candid/webhooks/.env
sudo systemctl restart agentic-webhooks
```

## Webhook Configuration

### Update GoHighLevel Webhook

1. Log into GoHighLevel
2. Go to Settings > Webhooks
3. Find existing n8n webhook
4. Update URL to: `https://webhook.candidstudios.net/webhook/calendar-ghl`
5. Or configure new webhook

### Test with Shadow Mode

Run both n8n and new webhook in parallel:
1. Keep n8n running
2. Deploy new webhook on different port
3. Configure GHL to send to both
4. Compare results
5. Switch over when confident

## Firewall Configuration

If needed, open port 8080:

```bash
# UFW
sudo ufw allow 8080/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables-save
```

## Nginx Reverse Proxy (Optional)

To use HTTPS and standard ports:

```nginx
# /etc/nginx/sites-available/agentic-webhooks
server {
    listen 443 ssl;
    server_name webhook.candidstudios.net;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /webhook/ {
        proxy_pass http://localhost:8080/webhook/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://localhost:8080/health;
    }

    location /metrics {
        proxy_pass http://localhost:8080/metrics;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/agentic-webhooks /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Rollback Plan

If deployment fails:

```bash
# Stop new service
sudo systemctl stop agentic-webhooks

# Restore from backup
cd ~/agentic-workspace
bash scripts/restore.sh

# Or restart n8n
sudo systemctl start n8n
```

## Security Checklist

- [ ] API tokens stored in `.env` (never committed)
- [ ] Google credentials file permissions set to 600
- [ ] Webhook secret configured
- [ ] IP whitelist configured (if applicable)
- [ ] Firewall rules in place
- [ ] HTTPS enabled (via Nginx)
- [ ] Service runs as non-root user
- [ ] Log rotation configured

## Support

For issues:
1. Check logs: `sudo journalctl -u agentic-webhooks -f`
2. Run diagnostics: `bash scripts/test_connection.sh`
3. Check status: `curl http://localhost:8080/status`
