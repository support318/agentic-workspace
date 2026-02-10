"""
Unit tests for webhook server.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


@pytest.fixture
def app():
    """Create a test Flask app."""
    from execution.webhook_server import app
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestWebhookServer:
    """Test suite for webhook server endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_index(self, client):
        """Test root endpoint."""
        response = client.get('/')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "endpoints" in data
        assert "calendar_ghl" in data["endpoints"]

    @patch('execution.webhook_server.create_ghl_event')
    @patch('execution.webhook_server.GoHighLevelAPI')
    def test_calendar_webhook_create_new_event(self, mock_ghl_api, mock_create_event, client):
        """Test calendar webhook creates new event."""
        # Mock create_ghl_event
        mock_create_event.return_value = {
            "event": {"id": "cal123", "summary": "Test Event (Lead)"},
            "action": "created"
        }

        # Mock GHL API
        mock_api = MagicMock()
        mock_ghl_api.return_value = mock_api

        # Send webhook
        payload = {
            "Opportunity Name": "Smith Wedding",
            "Event Date": "2025-06-15",
            "Photography Hours": "6",
            "Videography Hours": "0",
            "stage": "lead",
            "contact_id": "contact123"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["action"] == "created"
        assert data["event_id"] == "cal123"
        assert data["is_booked"] is False

    @patch('execution.webhook_server.create_ghl_event')
    @patch('execution.webhook_server.GoHighLevelAPI')
    def test_calendar_webhook_update_existing_event(self, mock_ghl_api, mock_create_event, client):
        """Test calendar webhook updates existing event."""
        mock_create_event.return_value = {
            "event": {"id": "cal123", "summary": "Smith Wedding - Photo (Booked)"},
            "action": "updated"
        }

        mock_api = MagicMock()
        mock_ghl_api.return_value = mock_api

        payload = {
            "Opportunity Name": "Smith Wedding",
            "Event Date": "2025-06-15",
            "Photography Hours": "6",
            "stage": "booked",
            "contact_id": "contact123",
            "Google Calendar Event ID From Make": "cal123"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["action"] == "updated"
        assert data["is_booked"] is True

    def test_calendar_webhook_missing_data(self, client):
        """Test webhook handles missing required data gracefully."""
        payload = {}

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should return error but not crash
        assert response.status_code in [200, 500]


class TestPayloadParsing:
    """Test webhook payload parsing logic."""

    def test_parse_hours(self):
        """Test hours parsing."""
        from execution.webhook_server import parse_hours

        assert parse_hours("6 hours") == 6
        assert parse_hours("8") == 8
        assert parse_hours(None) == 0
        assert parse_hours("") == 0

    def test_parse_time_str(self):
        """Test time string parsing."""
        from execution.webhook_server import parse_time_str

        assert parse_time_str("10:00 AM") == (10, 0)
        assert parse_time_str("2:30 PM") == (14, 30)
        assert parse_time_str("invalid") == (10, 0)

    def test_has_drone_service(self):
        """Test drone service detection."""
        from execution.webhook_server import has_drone_service

        assert has_drone_service("Yes") is True
        assert has_drone_service("No") is False
        assert has_drone_service(None) is False

    def test_is_stage_booked(self):
        """Test booked stage detection."""
        from execution.webhook_server import is_stage_booked

        assert is_stage_booked("booked") is True
        assert is_stage_booked("Booked") is True
        assert is_stage_booked("lead") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
