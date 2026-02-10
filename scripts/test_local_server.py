"""
Local test server for webhook testing.
Uses mock APIs so you can test without real credentials.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

# Mock storage for testing
mock_events = {}
mock_contacts = {}
request_count = 0


def parse_hours(value):
    if isinstance(value, int):
        return value
    if not value:
        return 0
    import re
    match = re.search(r'\d+', str(value))
    return int(match.group()) if match else 0


def parse_time_str(time_str: str):
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


def has_drone_service(drone_value):
    if not drone_value:
        return False
    drone_str = str(drone_value).lower()
    return 'yes' in drone_str or 'true' in drone_str or drone_str == 'y'


def is_stage_booked(stage):
    if not stage:
        return False
    return stage.lower() == 'booked'


@app.route('/webhook/calendar-ghl', methods=['POST'])
def calendar_ghl_webhook():
    """Mock webhook endpoint that processes data without real API calls."""
    global request_count
    request_count += 1

    webhook_data = request.get_json() or {}

    print(f"\n{'='*60}")
    print(f"Request #{request_count}: {webhook_data.get('Opportunity Name', 'Unknown')}")
    print(f"{'='*60}")

    # Extract and log data
    opportunity_name = webhook_data.get('Opportunity Name', 'Event')
    event_date = webhook_data.get('Event Date') or datetime.now().strftime('%Y-%m-%d')
    photo_hours = parse_hours(webhook_data.get('Photography Hours'))
    video_hours = parse_hours(webhook_data.get('Videography Hours'))
    has_drone = has_drone_service(webhook_data.get('Drone Services'))
    stage = webhook_data.get('stage', '')
    is_booked = is_stage_booked(stage)
    photo_time = webhook_data.get('Photography Start Time', '10:00 AM')
    video_time = webhook_data.get('Videography Start Time', '9:00 AM')

    # Log parsed data
    print(f"  Event Date: {event_date}")
    print(f"  Photo Hours: {photo_hours}")
    print(f"  Video Hours: {video_hours}")
    print(f"  Drone: {has_drone}")
    print(f"  Stage: {stage} (Booked: {is_booked})")

    # Calculate timing
    photo_hour, _ = parse_time_str(photo_time)
    video_hour, _ = parse_time_str(video_time)
    start_hour = min(photo_hour, video_hour)
    max_hours = max(photo_hours, video_hours, 4)

    print(f"  Start Time: {start_hour}:00")
    print(f"  Duration: {max_hours} hours")

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

    print(f"  Title: {title}")

    # Check for existing event
    calendar_event_id = (
        webhook_data.get('Calendar Event ID') or
        webhook_data.get('Google Calendar Event ID From Make') or
        webhook_data.get('google_calendar_event_id_from_make')
    )

    # Create or update (mock)
    if calendar_event_id:
        action = "updated"
        event_id = calendar_event_id
    else:
        action = "created"
        event_id = f"mock_event_{request_count}"

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

    # Store mock data
    mock_events[event_id] = {
        "title": title,
        "event_date": event_date,
        "start_hour": start_hour,
        "duration": max_hours,
        "description": description,
        "is_booked": is_booked
    }

    contact_id = webhook_data.get('contact_id')
    if contact_id:
        mock_contacts[contact_id] = {
            "calendar_event_id": event_id
        }

    color = "Red (Booked)" if is_booked else "Orange (Lead)"

    print(f"  Action: {action.upper()}")
    print(f"  Event ID: {event_id}")
    print(f"  Color: {color}")
    print(f"{'='*60}\n")

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
        "note": "This is a mock response - no real calendar event created"
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "mode": "mock"})


@app.route('/mock/events', methods=['GET'])
def list_mock_events():
    """List all mock events created during testing."""
    return jsonify({
        "events": mock_events,
        "contacts": mock_contacts,
        "total_requests": request_count
    })


@app.route('/mock/reset', methods=['POST'])
def reset_mocks():
    """Reset mock storage."""
    global mock_events, mock_contacts, request_count
    mock_events.clear()
    mock_contacts.clear()
    request_count = 0
    return jsonify({"status": "reset"})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("MOCK WEBHOOK SERVER - Testing Mode")
    print("="*60)
    print("\nEndpoints:")
    print("  POST http://localhost:8080/webhook/calendar-ghl")
    print("  GET  http://localhost:8080/health")
    print("  GET  http://localhost:8080/mock/events")
    print("  POST http://localhost:8080/mock/reset")
    print("\nTest command:")
    print('  curl -X POST http://localhost:8080/webhook/calendar-ghl \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"Opportunity Name": "Test Wedding", "Event Date": "2025-06-15", "Photography Hours": "6", "stage": "booked", "contact_id": "test123"}\'')
    print("\n" + "="*60 + "\n")

    app.run(host='localhost', port=8080, debug=False)
