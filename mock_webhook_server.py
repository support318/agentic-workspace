#!/usr/bin/env python3
"""
Webhook server with mock Google Calendar for testing.
GHL webhook reception works, calendar events are mocked.
"""
import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Metrics
_metrics = {
    'requests_total': 0,
    'requests_success': 0,
    'requests_error': 0,
    'webhooks_received': 0,
    'calendar_events_created': 0,
    'calendar_events_updated': 0,
    'ghl_contact_updates': 0,
    'start_time': datetime.utcnow().isoformat()
}

# Mock event storage
_mock_events = {}
_event_counter = 0


# GHL API helpers
def update_ghl_contact(contact_id: str, event_id: str) -> bool:
    """Update GHL contact with calendar event ID."""
    try:
        token = os.getenv('GHL_API_TOKEN')
        if not token:
            logger.warning("GHL_API_TOKEN not set")
            return False

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }

        payload = {
            "customFields": [
                {
                    "key": "google_calendar_event_id_from_make",
                    "field_value": event_id
                }
            ]
        }

        response = requests.put(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"Updated GHL contact {contact_id} with event ID {event_id}")
            _metrics['ghl_contact_updates'] += 1
            return True
        else:
            logger.error(f"GHL update failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to update GHL contact: {e}")
        return False


# Helper functions
def parse_hours(value):
    if isinstance(value, int):
        return value
    if not value:
        return 0
    import re
    match = re.search(r'\d+', str(value))
    return int(match.group()) if match else 0


def parse_time_str(time_str: str) -> tuple:
    import re
    match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = match.group(3).upper()
        if meridiem == 'PM' and hour != 12:
            hour += 12
        if meridiem == 'AM' and hour == 12:
            hour = 0
        return hour, minute
    return 10, 0


def has_drone_service(drone_value) -> bool:
    if not drone_value:
        return False
    drone_str = str(drone_value).lower()
    return 'yes' in drone_str or 'true' in drone_str or drone_str == 'y'


def is_stage_booked(stage) -> bool:
    if not stage:
        return False
    return stage.lower() == 'booked'


@app.route('/webhook/calendar-ghl', methods=['POST'])
def calendar_ghl_webhook():
    """Main GHL calendar webhook with mock calendar."""
    global _metrics, _event_counter, _mock_events
    _metrics['requests_total'] += 1
    _metrics['webhooks_received'] += 1

    webhook_data = request.get_json() or {}

    logger.info(f"Received GHL calendar webhook: {webhook_data.get('Opportunity Name', 'Unknown')}")

    # Extract data
    opportunity_name = webhook_data.get('Opportunity Name', 'Event')
    event_date = webhook_data.get('Event Date') or datetime.now().strftime('%Y-%m-%d')
    photo_hours = parse_hours(webhook_data.get('Photography Hours'))
    video_hours = parse_hours(webhook_data.get('Videography Hours'))
    has_drone = has_drone_service(webhook_data.get('Drone Services'))
    stage = webhook_data.get('stage', '')
    is_booked = is_stage_booked(stage)
    photo_time = webhook_data.get('Photography Start Time', '10:00 AM')
    video_time = webhook_data.get('Videography Start Time', '9:00 AM')

    # Calculate timing
    photo_hour, _ = parse_time_str(photo_time)
    video_hour, _ = parse_time_str(video_time)
    start_hour = min(photo_hour, video_hour)
    max_hours = max(photo_hours, video_hours, 4)

    # Build title
    services = []
    if photo_hours > 0:
        services.append("Photo")
    if video_hours > 0:
        services.append("Video")
    if has_drone:
        services.append("Drone")

    title = opportunity_name or "Event"
    if services:
        title += f" - {'/'.join(services)}"
    if not is_booked:
        title += " (Lead)"

    # Check for existing event
    calendar_event_id = (
        webhook_data.get('Calendar Event ID') or
        webhook_data.get('Google Calendar Event ID From Make') or
        webhook_data.get('google_calendar_event_id_from_make')
    )

    # Create or update (mock calendar)
    if calendar_event_id:
        action = "updated"
        event_id = calendar_event_id
    else:
        action = "created"
        _event_counter += 1
        event_id = f"mock_event_{_event_counter}"

    # Build description
    desc_parts = []
    if webhook_data.get('Type of Event'):
        desc_parts.append(f"Type of Event: {webhook_data['Type of Event']}")
    if photo_hours:
        desc_parts.append(f"Photography Hours: {photo_hours}")
    if video_hours:
        desc_parts.append(f"Videography Hours: {video_hours}")
    if has_drone:
        desc_parts.append(f"Drone Services: Yes")
    if webhook_data.get('Project Location'):
        desc_parts.append(f"Location: {webhook_data['Project Location']}")
    description = " | ".join(desc_parts)

    # Store mock event
    _mock_events[event_id] = {
        "title": title,
        "event_date": event_date,
        "start_hour": start_hour,
        "duration": max_hours,
        "description": description,
        "is_booked": is_booked,
        "services": services
    }

    color = "Red (Booked)" if is_booked else "Orange (Lead)"
    contact_id = webhook_data.get('contact_id')

    # Update GHL contact
    ghl_updated = False
    if contact_id and event_id:
        ghl_updated = update_ghl_contact(contact_id, event_id)

    _metrics['requests_success'] += 1
    if action == 'created':
        _metrics['calendar_events_created'] += 1
    else:
        _metrics['calendar_events_updated'] += 1

    logger.info(f"Processed webhook: {action} | {title} | {event_id} | {color}")

    return jsonify({
        "status": "success",
        "action": action,
        "event_id": event_id,
        "event_title": title,
        "event_date": event_date,
        "start_hour": start_hour,
        "duration_hours": max_hours,
        "is_booked": is_booked,
        "color": color,
        "description": description,
        "ghl_contact_updated": ghl_updated,
        "note": "MOCK MODE - Calendar event not created (no Google credentials)"
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "mode": "mock_calendar"})


@app.route('/metrics', methods=['GET'])
def metrics():
    uptime = (datetime.utcnow() - datetime.fromisoformat(_metrics['start_time'])).total_seconds()
    return jsonify({
        "metrics": _metrics,
        "mock_events": len(_mock_events),
        "uptime_seconds": uptime
    })


@app.route('/mock/events', methods=['GET'])
def list_events():
    return jsonify({"events": _mock_events})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8082))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print("="*60)
    print("AGENTIC WEBHOOK SERVER - MOCK CALENDAR MODE")
    print("="*60)
    print(f"Port: {port}")
    print(f"GHL Token: {os.getenv('GHL_API_TOKEN', 'NOT SET')[:20]}...")
    print(f"GHL Location: {os.getenv('GHL_LOCATION_ID', 'NOT SET')}")
    print(f"Google Calendar: MOCKED (no credentials)")
    print("="*60)
    print(f"Webhook: http://0.0.0.0:{port}/webhook/calendar-ghl")
    print(f"Health: http://0.0.0.0:{port}/health")
    print(f"Metrics: http://0.0.0.0:{port}/metrics")
    print("="*60)

    app.run(host='0.0.0.0', port=port, debug=debug)
