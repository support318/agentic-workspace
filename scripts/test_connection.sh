#!/bin/bash
# Test script for API connections on production server

set -e

SERVER="candid@192.168.40.100"
WEBHOOK_DIR="/home/candid/webhooks"

echo "🧪 Testing API connections..."
echo ""

# Test GHL API
echo "1️⃣ Testing GoHighLevel API..."
ssh $SERVER << 'ENDSSH'
cd /home/candid/webhooks
source venv/bin/activate
python3 << 'PYEOF'
import os
from dotenv import load_dotenv
import requests

load_dotenv()

token = os.getenv('GHL_API_TOKEN')
if token:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Version": "2021-07-28"
    }
    try:
        # Test with a simple request
        response = requests.get("https://services.leadconnectorhq.com/ping", headers=headers, timeout=10)
        print(f"   GHL API Status: {response.status_code}")
    except Exception as e:
        print(f"   GHL API Error: {e}")
else:
    print("   GHL_API_TOKEN not set")
PYEOF
ENDSSH

echo ""

# Test Google Calendar API
echo "2️⃣ Testing Google Calendar API..."
ssh $SERVER << 'ENDSSH'
cd /home/candid/webhooks
source venv/bin/activate
python3 << 'PYEOF'
import os
from dotenv import load_dotenv

load_dotenv()

calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')

if calendar_id:
    print(f"   Calendar ID: {calendar_id}")
else:
    print("   GOOGLE_CALENDAR_ID not set")

if creds_path:
    print(f"   Credentials path: {creds_path}")
    # Check if file exists
    import os
    if os.path.exists(creds_path):
        print("   ✅ Credentials file exists")
    else:
        print("   ❌ Credentials file not found")
else:
    print("   GOOGLE_CREDENTIALS_PATH not set")
PYEOF
ENDSSH

echo ""

# Test Keycloak API
echo "3️⃣ Testing Keycloak API..."
ssh $SERVER << 'ENDSSH'
cd /home/candid/webhooks
source venv/bin/activate
python3 << 'PYEOF'
import os
from dotenv import load_dotenv

load_dotenv()

server_url = os.getenv('KEYCLOAK_SERVER_URL')
realm = os.getenv('KEYCLOAK_REALM')

if server_url:
    print(f"   Server URL: {server_url}")
    print(f"   Realm: {realm}")

    # Try connection
    import requests
    try:
        response = requests.get(f"{server_url}/realms/{realm}", timeout=5)
        if response.status_code == 200:
            print("   ✅ Keycloak is accessible")
        else:
            print(f"   ❌ Keycloak returned: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Keycloak Error: {e}")
else:
    print("   KEYCLOAK_SERVER_URL not set")
PYEOF
ENDSSH

echo ""

# Test webhook server health
echo "4️⃣ Testing Webhook Server..."
ssh $SERVER << 'ENDSSH'
curl -s http://localhost:8080/health | python3 -m json.tool || echo "   Webhook server not responding"
ENDSSH

echo ""
echo "✅ Connection tests complete!"
