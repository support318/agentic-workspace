#!/usr/bin/env python3
"""
Candid Studios Webhook Server
Receives webhooks from GoHighLevel for staff assignment, calendar sync,
and SimplyNoted thank you card automation.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from functools import wraps

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Configuration
PORT = int(os.getenv('PORT', 8082))
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Import modules
try:
    from staff_assignment import find_top_candidates
    MODULES_AVAILABLE = True
    logger.info("Core modules loaded successfully")
except ImportError as e:
    MODULES_AVAILABLE = False
    logger.warning(f"Could not import core modules: {e}")

try:
    from simplynoted_api import SimplyNotedAPI
    SIMPLYNOTED_AVAILABLE = True
    logger.info("SimplyNoted module loaded successfully")
except ImportError as e:
    SIMPLYNOTED_AVAILABLE = False
    logger.warning(f"Could not import SimplyNoted module: {e}")

def verify_webhook_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if WEBHOOK_SECRET:
            provided_secret = request.headers.get('X-Webhook-Secret', '')
            if provided_secret != WEBHOOK_SECRET:
                logger.warning("Invalid webhook secret provided")
                return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'modules_loaded': MODULES_AVAILABLE,
        'simplynoted_loaded': SIMPLYNOTED_AVAILABLE,
        'version': '1.1.0'
    })

@app.route('/webhook/staff-assignment', methods=['POST'])
@verify_webhook_secret
def staff_assignment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        logger.info(f"Received staff assignment request: {json.dumps(data, indent=2)}")
        
        lead_email = data.get('lead_email')
        lead_name = data.get('lead_name', 'Valued Customer')
        
        if not lead_email:
            return jsonify({'error': 'lead_email is required'}), 400
        
        # Map services_needed to categories (photo/video)
        services_needed = data.get('services_needed', {})
        event_address = data.get('event_address', '')
        event_hours = int(data.get('event_hours', 0))
        preferred_staff = data.get('preferred_staff')
        
        logger.info(f"Processing assignment for {lead_name} - Services: {services_needed}")
        
        if not MODULES_AVAILABLE:
            logger.warning("Core modules not available, returning mock response")
            return jsonify({
                'status': 'accepted',
                'message': 'Request accepted (modules not available)',
                'lead_email': lead_email,
                'services_needed': services_needed
            }), 202
        
        results = {}
        
        # Process each service type
        for service, needed in services_needed.items():
            if not needed:
                continue
            
            # Map service to category for the staff assignment system
            category = 'photo' if service == 'photography' else 'video' if service == 'videography' else service
            
            try:
                candidates = find_top_candidates(
                    event_location=event_address,
                    preferred_staff=preferred_staff,
                    category=category,
                    top_n=3,
                    max_distance_miles=200
                )
                
                # Convert Candidate objects to dicts
                candidate_list = []
                for c in candidates:
                    candidate_list.append({
                        'name': c.staff.full_name if hasattr(c, 'staff') else str(c),
                        'email': c.staff.email if hasattr(c, 'staff') else '',
                        'phone': c.staff.phone if hasattr(c, 'staff') else '',
                        'distance_miles': c.distance_miles if hasattr(c, 'distance_miles') else 0,
                        'duration_text': c.duration_text if hasattr(c, 'duration_text') else ''
                    })
                
                results[service] = {
                    'candidates_found': len(candidate_list),
                    'top_candidates': candidate_list
                }
                
                logger.info(f"Found {len(candidate_list)} candidates for {service}")
                
            except Exception as e:
                logger.error(f"Error finding candidates for {service}: {e}", exc_info=True)
                results[service] = {'error': str(e)}
        
        return jsonify({
            'status': 'success',
            'message': 'Staff assignment processed',
            'lead_email': lead_email,
            'services_needed': services_needed,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing staff assignment: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/calendar-ghl', methods=['POST'])
@verify_webhook_secret
def calendar_ghl():
    try:
        data = request.get_json()
        logger.info(f"Received calendar webhook: {json.dumps(data, indent=2)}")
        return jsonify({'status': 'success', 'message': 'Calendar webhook processed'}), 200
    except Exception as e:
        logger.error(f"Error processing calendar webhook: {e}")
        return jsonify({'error': str(e)}), 500


# --- SimplyNoted Thank You Card Messages ---

SIMPLYNOTED_MESSAGES = {
    "wedding": (
        "Dear {first_name} & {partner_name},\n\n"
        "Thank you for allowing us to be part of your special day! "
        "It was an absolute pleasure capturing all the beautiful moments "
        "of your wedding. We can't wait for you to see the final result.\n\n"
        "Warm regards,\nThe Candid Studios Team"
    ),
    "mitzvah": (
        "Dear {first_name},\n\n"
        "Congratulations on your {event_type}! It was such an honor to be "
        "part of this milestone celebration. We loved capturing every special "
        "moment and can't wait for you to relive them.\n\n"
        "Warm regards,\nThe Candid Studios Team"
    ),
    "quinceanera": (
        "Dear {first_name},\n\n"
        "What a beautiful celebration of your daughter's quinceañera! "
        "Thank you for trusting us to capture these precious memories. "
        "It was truly a magical evening and we're honored to have been part of it.\n\n"
        "Warm regards,\nThe Candid Studios Team"
    ),
    "corporate": (
        "Dear {first_name},\n\n"
        "Thank you for choosing to work with us for your event. "
        "It was a pleasure providing our services and we hope the results "
        "exceed your expectations. We look forward to working together again!\n\n"
        "Warm regards,\nThe Candid Studios Team"
    ),
}


def _get_message_and_card(event_type, first_name, partner_name, simplynoted_api):
    """Determine the correct message template and card ID based on event type."""
    event_lower = (event_type or "").lower().strip()

    if "wedding" in event_lower:
        display_partner = partner_name if partner_name else ""
        if display_partner:
            msg = SIMPLYNOTED_MESSAGES["wedding"].format(
                first_name=first_name, partner_name=display_partner
            )
        else:
            # No partner name - adjust greeting
            msg = SIMPLYNOTED_MESSAGES["wedding"].replace(
                "Dear {first_name} & {partner_name},",
                f"Dear {first_name},"
            ).format(first_name=first_name, partner_name="")
        card_id = simplynoted_api.get_card_id("wedding")
        return msg, card_id

    if "mitzvah" in event_lower:
        msg = SIMPLYNOTED_MESSAGES["mitzvah"].format(
            first_name=first_name, event_type=event_type
        )
        card_id = simplynoted_api.get_card_id("bar mitzvah")
        return msg, card_id

    if "quincea" in event_lower:
        msg = SIMPLYNOTED_MESSAGES["quinceanera"].format(first_name=first_name)
        card_id = simplynoted_api.get_card_id("quinceanera")
        return msg, card_id

    # Corporate / event / commercial / anything else
    msg = SIMPLYNOTED_MESSAGES["corporate"].format(first_name=first_name)
    card_id = simplynoted_api.get_card_id(event_type or "default")
    return msg, card_id


@app.route('/webhook/simplynoted-thank-you', methods=['POST'])
def simplynoted_thank_you():
    """Send a handwritten thank you card via SimplyNoted after an event."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        logger.info(f"Received SimplyNoted request: {json.dumps(data, indent=2)}")

        if not SIMPLYNOTED_AVAILABLE:
            logger.error("SimplyNoted module not available")
            return jsonify({'error': 'SimplyNoted module not loaded'}), 500

        # Extract fields from GHL payload
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        partner_name = data.get("Partner's First Name", data.get('partners_first_name_primary', '')).strip()
        event_type = data.get('Type of Event', data.get('type_of_event_primary', '')).strip()
        event_date_str = data.get('Event Date', data.get('when_is_the_event_primary', '')).strip()
        address1 = data.get('address1', data.get('mailing_address', '')).strip()
        address2 = data.get('address2', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        postal_code = data.get('postalCode', data.get('postal_code', '')).strip()

        # Validate required fields
        if not first_name:
            return jsonify({'error': 'first_name is required'}), 400
        if not address1 or not city or not state or not postal_code:
            missing = [f for f, v in {'address1': address1, 'city': city, 'state': state, 'postalCode': postal_code}.items() if not v]
            return jsonify({'error': f'Missing required address fields: {", ".join(missing)}'}), 400

        # Calculate shipping date (day after event, or tomorrow if no date)
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
            except ValueError:
                # Try alternate formats
                for fmt in ('%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d'):
                    try:
                        event_date = datetime.strptime(event_date_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    logger.warning(f"Could not parse event date '{event_date_str}', using tomorrow")
                    event_date = datetime.now()
        else:
            event_date = datetime.now()

        shipping_date = (event_date + timedelta(days=1)).strftime('%Y-%m-%d')

        # Initialize API and determine card + message
        simplynoted_api = SimplyNotedAPI()
        message, card_id = _get_message_and_card(event_type, first_name, partner_name, simplynoted_api)

        recipient = {
            "name": f"{first_name} {last_name}".strip(),
            "address1": address1,
            "address2": address2,
            "city": city,
            "state": state,
            "zip": postal_code,
            "country": "US"
        }

        logger.info(f"Sending {event_type or 'default'} card to {recipient['name']} - Ship: {shipping_date}")

        # Send the card
        result = simplynoted_api.send_card(
            card_id=card_id,
            message=message,
            recipient=recipient,
            shipping_date=shipping_date
        )

        return jsonify({
            'status': 'success',
            'message': 'Thank you card order submitted',
            'recipient': recipient['name'],
            'event_type': event_type,
            'card_id': card_id,
            'shipping_date': shipping_date,
            'simplynoted_response': result,
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error processing SimplyNoted webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'running',
        'port': PORT,
        'modules': 'loaded' if MODULES_AVAILABLE else 'partial',
        'simplynoted': 'loaded' if SIMPLYNOTED_AVAILABLE else 'not loaded',
        'timestamp': datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

def main():
    print("="*60)
    print("CANDID STUDIOS WEBHOOK SERVER")
    print("="*60)
    print(f"Port: {PORT}")
    print(f"Webhook Secret: {'Set' if WEBHOOK_SECRET else 'None'}")
    print(f"SimplyNoted:    {'Ready' if SIMPLYNOTED_AVAILABLE else 'Not loaded'}")
    print("="*60)
    print(f"Staff Assignment:   http://127.0.0.1:{PORT}/webhook/staff-assignment")
    print(f"Calendar GHL:       http://127.0.0.1:{PORT}/webhook/calendar-ghl")
    print(f"SimplyNoted Cards:  http://127.0.0.1:{PORT}/webhook/simplynoted-thank-you")
    print(f"Health Check:       http://127.0.0.1:{PORT}/health")
    print("="*60)
    app.run(host='127.0.0.1', port=PORT, debug=DEBUG)

if __name__ == '__main__':
    main()

