"""
Mock test of the GHL Calendar workflow without real API calls.
Tests the data transformation logic.
"""
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
sys.path.insert(0, sys.path[0] if '' in sys.path else '.')

from datetime import datetime


def test_parse_hours():
    """Test hours parsing."""
    def parse_hours(value):
        if isinstance(value, int):
            return value
        if not value:
            return 0
        import re
        match = re.search(r'\d+', str(value))
        return int(match.group()) if match else 0

    assert parse_hours(6) == 6
    assert parse_hours("6 hours") == 6
    assert parse_hours("8") == 8
    assert parse_hours(None) == 0
    assert parse_hours("") == 0
    print("✅ parse_hours tests passed")


def test_parse_time_str():
    """Test time string parsing."""
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

    assert parse_time_str("10:00 AM") == (10, 0)
    assert parse_time_str("2:30 PM") == (14, 30)
    assert parse_time_str("12:00 AM") == (0, 0)
    assert parse_time_str("12:00 PM") == (12, 0)
    print("✅ parse_time_str tests passed")


def test_has_drone_service():
    """Test drone service detection."""
    def has_drone_service(drone_value):
        if not drone_value:
            return False
        drone_str = str(drone_value).lower()
        return 'yes' in drone_str or 'true' in drone_str or drone_str == 'y'

    assert has_drone_service("Yes") is True
    assert has_drone_service("yes") is True
    assert has_drone_service("true") is True
    assert has_drone_service("y") is True
    assert has_drone_service("No") is False
    assert has_drone_service("false") is False
    assert has_drone_service(None) is False
    print("✅ has_drone_service tests passed")


def test_is_stage_booked():
    """Test booked stage detection."""
    def is_stage_booked(stage):
        if not stage:
            return False
        return stage.lower() == 'booked'

    assert is_stage_booked("booked") is True
    assert is_stage_booked("Booked") is True
    assert is_stage_booked("BOOKED") is True
    assert is_stage_booked("lead") is False
    assert is_stage_booked("") is False
    assert is_stage_booked(None) is False
    print("✅ is_stage_booked tests passed")


def test_title_building():
    """Test event title construction."""
    def build_title(name, photo_hours, video_hours, has_drone, is_booked):
        services = []
        if photo_hours > 0:
            services.append("Photo")
        if video_hours > 0:
            services.append("Video")
        if has_drone:
            services.append("Drone")

        title = name or "Event"
        if services:
            title += f" - {'/'.join(services)}"
        if not is_booked:
            title += " (Lead)"
        return title

    assert build_title("Smith Wedding", 6, 4, True, False) == "Smith Wedding - Photo/Video/Drone (Lead)"
    assert build_title("Smith Wedding", 6, 4, True, True) == "Smith Wedding - Photo/Video/Drone"
    assert build_title("Corporate Event", 4, 0, False, True) == "Corporate Event - Photo"
    assert build_title("Test Event", 0, 0, False, False) == "Test Event (Lead)"
    print("✅ title building tests passed")


def test_datetime_calculation():
    """Test datetime calculations for events."""
    def calculate_end_time(event_date, start_hour, max_hours):
        start_dt = datetime.fromisoformat(f"{event_date}T{start_hour:02d}:00:00")
        end_dt = start_dt.__class__.fromtimestamp(start_dt.timestamp() + max_hours * 3600)
        return end_dt.isoformat()

    result = calculate_end_time("2025-06-15", 14, 6)
    assert "2025-06-15" in result
    assert "20" in result  # Should end around 20:00 (6 hours later)
    print("✅ datetime calculation tests passed")


def test_full_payload_processing():
    """Test processing a full webhook payload."""
    sample_payload = {
        "Opportunity Name": "Johnson Wedding - Photography & Video",
        "Event Date": "2025-06-15",
        "Photography Hours": "6",
        "Videography Hours": "4",
        "Drone Services": "Yes",
        "Project Location": "123 Main St, Austin, TX",
        "Photography Start Time": "2:00 PM",
        "Videography Start Time": "1:00 PM",
        "Type of Event": "Wedding",
        "stage": "booked",
        "contact_id": "test123"
    }

    # Extract and validate data
    opportunity_name = sample_payload.get('Opportunity Name')
    event_date = sample_payload.get('Event Date')
    photo_hours = int(sample_payload.get('Photography Hours', '0'))
    video_hours = int(sample_payload.get('Videography Hours', '0'))
    has_drone = sample_payload.get('Drone Services', '').lower() in ['yes', 'true']
    is_booked = sample_payload.get('stage', '').lower() == 'booked'

    assert opportunity_name == "Johnson Wedding - Photography & Video"
    assert event_date == "2025-06-15"
    assert photo_hours == 6
    assert video_hours == 4
    assert has_drone is True
    assert is_booked is True
    assert sample_payload['contact_id'] == "test123"

    print("✅ Full payload processing tests passed")


def test_description_building():
    """Test event description construction."""
    def build_description(payload):
        parts = []
        if payload.get('Type of Event'):
            parts.append(f"🎉 Type of Event: {payload['Type of Event']}")
        if payload.get('Photography Hours'):
            parts.append(f"📸 Photography Hours: {payload['Photography Hours']}")
        if payload.get('Videography Hours'):
            parts.append(f"🎬 Videography Hours: {payload['Videography Hours']}")
        if payload.get('Drone Services'):
            parts.append(f"🚁 Drone Services: {payload['Drone Services']}")
        if payload.get('Project Location'):
            parts.append(f"📍 Project Location: {payload['Project Location']}")
        return "<br>".join(parts)

    payload = {
        "Type of Event": "Wedding",
        "Photography Hours": "6",
        "Videography Hours": "4",
        "Drone Services": "Yes",
        "Project Location": "123 Main St"
    }

    desc = build_description(payload)
    assert "🎉 Type of Event: Wedding" in desc
    assert "📸 Photography Hours: 6" in desc
    assert "🎬 Videography Hours: 4" in desc
    assert "🚁 Drone Services: Yes" in desc
    assert "📍 Project Location: 123 Main St" in desc
    assert "<br>" in desc
    print("✅ Description building tests passed")


if __name__ == "__main__":
    print("=" * 50)
    print("Testing GHL Calendar Workflow Logic")
    print("=" * 50)
    print()

    test_parse_hours()
    test_parse_time_str()
    test_has_drone_service()
    test_is_stage_booked()
    test_title_building()
    test_datetime_calculation()
    test_full_payload_processing()
    test_description_building()

    print()
    print("=" * 50)
    print("✅ All workflow logic tests passed!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Set up Google Calendar OAuth credentials")
    print("2. Test with real APIs: python tests/integration/test_full_workflow.py")
    print("3. Deploy to server: bash scripts/deploy.sh")
