#!/usr/bin/env python3
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from webhook_server import app

if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 8082))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print("="*60)
    print("AGENTIC WEBHOOK SERVER - PRODUCTION")
    print("="*60)
    print(f"Port: {port}")
    print(f"Google Calendar: {os.getenv('GOOGLE_CALENDAR_ID')}")
    print(f"GHL Location: {os.getenv('GHL_LOCATION_ID')}")
    print("="*60)
    print(f"Webhook: http://0.0.0.0:{port}/webhook/calendar-ghl")
    print("="*60)

    app.run(host='0.0.0.0', port=port, debug=debug)
