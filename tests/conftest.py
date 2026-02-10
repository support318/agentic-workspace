"""
Pytest configuration and fixtures for the agentic workspace.
"""

import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_ghl_webhook_payload():
    """Sample GoHighLevel webhook payload."""
    return {
        "Opportunity Name": "Johnson Wedding - Photography & Video",
        "Event Date": "2025-06-15",
        "Photography Hours": "6",
        "Videography Hours": "4",
        "Drone Services": "Yes",
        "Project Location": "123 Main St, Austin, TX",
        "Secondary Location": "Reception Hall",
        "Photography Start Time": "2:00 PM",
        "Videography Start Time": "1:00 PM",
        "Assigned Photographer": "John Smith",
        "Assigned Videographer": "Jane Doe",
        "Type of Event": "Wedding",
        "stage": "booked",
        "contact_id": "abc123xyz",
        "Calendar Event ID": "",
        "Google Calendar Event ID From Make": ""
    }


@pytest.fixture
def sample_ghl_webhook_lead():
    """Sample GHL webhook payload for a lead (not booked)."""
    return {
        "Opportunity Name": "Smith Corporate Event",
        "Event Date": "2025-08-20",
        "Photography Hours": "4",
        "Videography Hours": "0",
        "Drone Services": "No",
        "Project Location": "Downtown Hotel, Dallas, TX",
        "Photography Start Time": "10:00 AM",
        "Type of Event": "Corporate",
        "stage": "lead",
        "contact_id": "def456uvw"
    }


@pytest.fixture
def sample_ghl_webhook_update():
    """Sample GHL webhook payload for updating existing event."""
    return {
        "Opportunity Name": "Davis Birthday Party",
        "Event Date": "2025-09-10",
        "Photography Hours": "3",
        "Videography Hours": "2",
        "Drone Services": "Yes",
        "Project Location": "Backyard, Houston, TX",
        "Photography Start Time": "3:00 PM",
        "Type of Event": "Party",
        "stage": "booked",
        "contact_id": "ghi789rst",
        "Google Calendar Event ID From Make": "existing_cal_event_123"
    }
