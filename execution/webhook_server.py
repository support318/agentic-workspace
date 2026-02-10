"""
Flask webhook server to receive GoHighLevel webhooks.

This replaces the n8n webhook endpoint with a Python Flask server.
Routes incoming webhooks to the appropriate execution scripts.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from flask import Flask, request, jsonify
from functools import wraps

from dotenv import load_dotenv

# Import our execution scripts
from ghl_api import GoHighLevelAPI, get_contact_with_calendar_event
from google_calendar import create_ghl_event, GoogleCalendarAPI

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Metrics tracking
_metrics = {
    'requests_total': 0,
    'requests_success': 0,
    'requests_error': 0,
    'webhooks_received': 0,
    'calendar_events_created': 0,
    'calendar_events_updated': 0,
    'start_time': datetime.utcnow().isoformat()
}

# Webhook configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
ALLOWED_IPS = os.getenv('ALLOWED_IPS', '').split(',') if os.getenv('ALLOWED_IPS') else []


def validate_webhook_request() -> Tuple[bool, str]:
    """
    Validate incoming webhook request.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check IP whitelist if configured
    if ALLOWED_IPS and ALLOWED_IPS != ['']:
        client_ip = request.remote_addr
        if client_ip not in ALLOWED_IPS:
            logger.warning(f"Blocked request from unallowed IP: {client_ip}")
            return False, f"IP {client_ip} not allowed"

    # Check webhook secret if configured
    if WEBHOOK_SECRET:
        provided_secret = request.headers.get('X-Webhook-Secret', '')
        if provided_secret != WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret provided")
            return False, "Invalid webhook secret"

    return True, ""


def parse_hours(value: Any) -> int:
    """Parse hours from string or int."""
    if isinstance(value, int):
        return value
    if not value:
        return 0
    import re
    match = re.search(r'\d+', str(value))
    return int(match.group()) if match else 0


def parse_time_str(time_str: str) -> tuple[int, int]:
    """Parse '10:00 AM' to (hour, minute)."""
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
    return 10, 0  # Default


def has_drone_service(drone_value: Any) -> bool:
    """Check if drone services are requested."""
    if not drone_value:
        return False
    drone_str = str(drone_value).lower()
    return 'yes' in drone_str or 'true' in drone_str or drone_str == 'y'


def is_opportunity_booked(pipeline: str) -> bool:
    """
    Check if opportunity is booked based on pipeline.

    Rule: Only SALES pipeline is considered a lead.
    All other pipelines (PLANNING, PHOTO EDITING, VIDEO EDITING, etc.) are booked.
    """
    if not pipeline:
        return False  # Default to lead if no pipeline info
    return pipeline.upper() != "SALES"


@app.route('/webhook/calendar-ghl', methods=['POST'])
def calendar_ghl_webhook():
    """
    Main webhook endpoint for GHL Calendar sync.

    Expected payload from GoHighLevel:
    {
        "Opportunity Name": "...",
        "Event Date": "YYYY-MM-DD",
        "Photography Hours": "4",
        "Videography Hours": "2",
        "Drone Services": "Yes",
        "Project Location": "...",
        "Photography Start Time": "10:00 AM",
        "Videography Start Time": "9:00 AM",
        "Assigned Photographer": "...",
        "Assigned Videographer": "...",
        "Type of Event": "...",
        "pipeline": "SALES" | "PLANNING" | "PHOTO EDITING" | "VIDEO EDITING" | ...,
        "contact_id": "...",
        "Calendar Event ID": "...",
        "Google Calendar Event ID From Make": "..."
    }

    Pipeline determines booking status:
    - SALES = Lead (orange color, "(Lead)" suffix)
    - All others = Booked (red color, no "(Lead)" suffix)
    - APPLICANTS = Skip (no calendar event)
    - ARCHIVED = Delete existing event

    Returns:
        JSON response with status and event details
    """
    global _metrics
    _metrics['requests_total'] += 1
    _metrics['webhooks_received'] += 1

    # Validate request
    is_valid, error_msg = validate_webhook_request()
    if not is_valid:
        _metrics['requests_error'] += 1
        return jsonify({"error": error_msg}), 403

    try:
        # Get webhook data
        webhook_data = request.get_json() or {}

        logger.info(f"Received GHL calendar webhook: {webhook_data.get('Opportunity Name', 'Unknown')}")

        # Log all webhook data for debugging
        logger.info(f"Full webhook data: {json.dumps(webhook_data, indent=2)}")

        # Extract pipeline field for booking status determination
        pipeline = webhook_data.get('pipeline', '')

        # If pipeline is not in webhook data, fetch it from GHL API
        if not pipeline:
            opportunity_name = webhook_data.get('Opportunity Name', '')
            if opportunity_name:
                try:
                    api = GoHighLevelAPI()
                    pipeline = api.get_pipeline_name_for_opportunity(opportunity_name)
                    logger.info(f"Fetched pipeline from GHL API: '{pipeline}' for opportunity '{opportunity_name}'")
                except Exception as e:
                    logger.error(f"Failed to fetch pipeline from GHL API: {e}")

        logger.info(f"Pipeline: '{pipeline}', is_booked will be: {pipeline.upper() != 'SALES' if pipeline else 'False (no pipeline)'}")

        # Special pipeline handling
        if pipeline and pipeline.upper() == "APPLICANTS":
            # Skip calendar creation for job applicants
            opportunity_name = webhook_data.get('Opportunity Name', 'Unknown')
            logger.info(f"Skipping calendar event for Applicants pipeline: {opportunity_name}")
            return jsonify({
                "status": "skipped",
                "message": "Applicants pipeline - no calendar event created"
            })

        # Check for existing calendar event before potentially deleting
        calendar_event_id = (
            webhook_data.get('Calendar Event ID') or
            webhook_data.get('Google Calendar Event ID From Make') or
            webhook_data.get('google_calendar_event_id_from_make')
        )

        if pipeline and pipeline.upper() == "ARCHIVED":
            # Delete existing calendar event if it exists
            if calendar_event_id:
                try:
                    api = GoogleCalendarAPI()
                    api.delete_event(calendar_event_id)
                    logger.info(f"Deleted calendar event for Archived pipeline: {calendar_event_id}")
                except Exception as e:
                    logger.error(f"Failed to delete calendar event: {e}")
            return jsonify({
                "status": "deleted",
                "message": "Archived - event removed"
            })

        # Extract key fields
        opportunity_name = webhook_data.get('Opportunity Name', 'Event')
        event_date = webhook_data.get('Event Date') or datetime.now().strftime('%Y-%m-%d')
        photo_hours = parse_hours(webhook_data.get('Photography Hours'))
        video_hours = parse_hours(webhook_data.get('Videography Hours'))
        has_drone = has_drone_service(webhook_data.get('Drone Services'))

        # Determine booking status based on pipeline (not stage)
        is_booked = is_opportunity_booked(pipeline)

        photo_time = webhook_data.get('Photography Start Time', '10:00 AM')
        video_time = webhook_data.get('Videography Start Time', '9:00 AM')

        # Use earlier time as start
        photo_hour, _ = parse_time_str(photo_time)
        video_hour, _ = parse_time_str(video_time)
        start_time = f"{min(photo_hour, video_hour):02d}:00 AM"

        # Create or update calendar event
        result = create_ghl_event(
            opportunity_name=opportunity_name,
            event_date=event_date,
            photo_hours=photo_hours,
            video_hours=video_hours,
            has_drone=has_drone,
            is_booked=is_booked,
            pipeline=pipeline,
            start_time=start_time,
            event_type=webhook_data.get('Type of Event', ''),
            project_location=webhook_data.get('Project Location', ''),
            assigned_photographer=webhook_data.get('Assigned Photographer', ''),
            assigned_videographer=webhook_data.get('Assigned Videographer', ''),
            calendar_event_id=calendar_event_id if calendar_event_id else None
        )

        event = result['event']
        action = result['action']
        new_event_id = event.get('id')

        # Update metrics
        if action == 'created':
            _metrics['calendar_events_created'] += 1
        else:
            _metrics['calendar_events_updated'] += 1
        _metrics['requests_success'] += 1

        # Update GHL contact with the event ID
        contact_id = webhook_data.get('contact_id')
        if contact_id and new_event_id:
            try:
                api = GoHighLevelAPI()
                api.update_contact_calendar_event_id(contact_id, new_event_id)
                logger.info(f"Updated GHL contact {contact_id} with event ID {new_event_id}")
            except Exception as e:
                logger.error(f"Failed to update GHL contact: {e}")
                # Don't fail the webhook if GHL update fails

        return jsonify({
            "status": "success",
            "action": action,
            "event_id": new_event_id,
            "event_title": event.get('summary'),
            "event_start": event.get('start', {}),
            "is_booked": is_booked
        })

    except Exception as e:
        _metrics['requests_error'] += 1
        logger.error(f"Error processing calendar webhook: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/webhook/lead-created', methods=['POST'])
def lead_created_webhook():
    """
    Webhook endpoint for new lead notifications.

    Can trigger:
    - Email notifications
    - Lead enrichment
    - Assignment logic
    """
    is_valid, error_msg = validate_webhook_request()
    if not is_valid:
        return jsonify({"error": error_msg}), 403

    try:
        webhook_data = request.get_json() or {}
        logger.info(f"New lead created: {webhook_data.get('contactId', 'Unknown')}")

        # TODO: Implement lead notification logic
        # - Send email to admin
        # - Add to CRM queue
        # - Trigger welcome sequence

        return jsonify({
            "status": "success",
            "message": "Lead notification received"
        })

    except Exception as e:
        logger.error(f"Error processing lead webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/webhook/contact-updated', methods=['POST'])
def contact_updated_webhook():
    """
    Webhook endpoint for contact updates.

    Handles changes to contact information.
    """
    is_valid, error_msg = validate_webhook_request()
    if not is_valid:
        return jsonify({"error": error_msg}), 403

    try:
        webhook_data = request.get_json() or {}
        contact_id = webhook_data.get('contactId')
        logger.info(f"Contact updated: {contact_id}")

        # Check if stage changed to booked
        # Update calendar event color if needed

        return jsonify({
            "status": "success",
            "message": "Contact update received"
        })

    except Exception as e:
        logger.error(f"Error processing contact update webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "agentic-webhooks"
    })


@app.route('/metrics', methods=['GET'])
def metrics():
    """Metrics endpoint for monitoring."""
    uptime_seconds = (datetime.utcnow() - datetime.fromisoformat(_metrics['start_time'])).total_seconds()
    return jsonify({
        "metrics": _metrics,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Detailed status endpoint."""
    # Check API connections
    status_info = {
        "service": "agentic-webhooks",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(_metrics['start_time'])).total_seconds(),
        "metrics": _metrics.copy(),
        "apis": {}
    }

    # Check GHL API
    try:
        if os.getenv('GHL_API_TOKEN'):
            status_info["apis"]["ghl"] = {"configured": True}
        else:
            status_info["apis"]["ghl"] = {"configured": False, "error": "No token"}
    except Exception as e:
        status_info["apis"]["ghl"] = {"configured": False, "error": str(e)}

    # Check Google Calendar
    try:
        if os.getenv('GOOGLE_CALENDAR_ID'):
            status_info["apis"]["google_calendar"] = {"configured": True}
        else:
            status_info["apis"]["google_calendar"] = {"configured": False, "error": "No calendar ID"}
    except Exception as e:
        status_info["apis"]["google_calendar"] = {"configured": False, "error": str(e)}

    return jsonify(status_info)


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with service info."""
    return jsonify({
        "service": "Agentic Webhook Server",
        "version": "1.0.0",
        "endpoints": {
            "calendar_ghl": "/webhook/calendar-ghl",
            "lead_created": "/webhook/lead-created",
            "contact_updated": "/webhook/contact-updated",
            "health": "/health",
            "metrics": "/metrics",
            "status": "/status"
        }
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting webhook server on port {port}")
    logger.info(f"Calendar webhook: http://localhost:{port}/webhook/calendar-ghl")

    app.run(host='0.0.0.0', port=port, debug=debug)
