"""
Production webhook server with real GHL API.
Start this and then either:
1. Use ngrok to expose to internet
2. Test with curl
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os

# Check if Google credentials are configured
from dotenv import load_dotenv
load_dotenv()

google_creds = os.getenv('GOOGLE_CREDENTIALS_PATH')
if not google_creds:
    print("⚠️  WARNING: Google Calendar credentials not configured")
    print("   Calendar events will be MOCKED only")
    print("   To enable real calendar sync, add GOOGLE_CREDENTIALS_PATH to .env")
    print()

# Import and run the real server
print("="*60)
print("PRODUCTION WEBHOOK SERVER")
print("="*60)
print()
print("Configuration:")
print(f"  GHL Token: {os.getenv('GHL_API_TOKEN', 'NOT SET')[:20]}...")
print(f"  GHL Location: {os.getenv('GHL_LOCATION_ID', 'NOT SET')}")
print(f"  Google Calendar: {os.getenv('GOOGLE_CALENDAR_ID', 'NOT SET')}")
print()
print("Endpoints:")
print("  POST http://localhost:8080/webhook/calendar-ghl")
print("  GET  http://localhost:8080/health")
print("  GET  http://localhost:8080/status")
print()
print("To expose GHL webhooks, use ngrok:")
print("  ngrok http 8080")
print()
print("="*60)
print()

# Import after dotenv is loaded
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
from execution.webhook_server import app

app.run(host='0.0.0.0', port=8080, debug=True)
