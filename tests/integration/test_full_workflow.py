"""
Integration test for full GHL → Calendar → GHL workflow.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestFullWorkflow:
    """End-to-end workflow tests."""

    @patch('execution.webhook_server.GoHighLevelAPI')
    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_full_workflow_new_lead(self, mock_calendar_api_class, mock_ghl_api_class):
        """Test full workflow for a new lead opportunity."""
        from execution.webhook_server import app
        from execution.ghl_api import GoHighLevelAPI

        # Setup mocks
        mock_calendar_api = MagicMock()
        mock_calendar_api_class.return_value = mock_calendar_api
        mock_calendar_api.create_event.return_value = {
            "id": "new_event_123",
            "summary": "Johnson Wedding - Photo/Video (Lead)",
            "start": {"dateTime": "2025-06-15T13:00:00"},
            "end": {"dateTime": "2025-06-15T19:00:00"}
        }
        mock_calendar_api.COLOR_LEAD = "6"
        mock_calendar_api.COLOR_BOOKED = "11"

        mock_ghl_api = MagicMock()
        mock_ghl_api_class.return_value = mock_ghl_api
        mock_ghl_api.update_contact_calendar_event_id.return_value = {
            "id": "contact456",
            "customFields": [
                {"key": "google_calendar_event_id_from_make", "field_value": "new_event_123"}
            ]
        }

        # Create test client
        app.config['TESTING'] = True
        client = app.test_client()

        # Send webhook payload
        payload = {
            "Opportunity Name": "Johnson Wedding",
            "Event Date": "2025-06-15",
            "Photography Hours": "6",
            "Videography Hours": "4",
            "Drone Services": "Yes",
            "Project Location": "123 Main St, Austin, TX",
            "Photography Start Time": "2:00 PM",
            "Videography Start Time": "1:00 PM",
            "Assigned Photographer": "John Smith",
            "Assigned Videographer": "Jane Doe",
            "Type of Event": "Wedding",
            "stage": "lead",
            "contact_id": "contact456"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["action"] == "created"
        assert data["event_id"] == "new_event_123"
        assert data["is_booked"] is False

        # Verify calendar event was created
        mock_calendar_api.create_event.assert_called_once()
        call_kwargs = mock_calendar_api.create_event.call_args[1]
        assert "Johnson Wedding" in call_kwargs["title"]
        assert "(Lead)" in call_kwargs["title"]

        # Verify GHL contact was updated
        mock_ghl_api.update_contact_calendar_event_id.assert_called_once_with(
            "contact456", "new_event_123"
        )

    @patch('execution.webhook_server.GoHighLevelAPI')
    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_full_workflow_update_booked_event(self, mock_calendar_api_class, mock_ghl_api_class):
        """Test full workflow for updating a booked event."""
        from execution.webhook_server import app

        # Setup mocks
        mock_calendar_api = MagicMock()
        mock_calendar_api_class.return_value = mock_calendar_api
        mock_calendar_api.update_event.return_value = {
            "id": "existing_event_456",
            "summary": "Smith Wedding - Photo (Booked)",
            "start": {"dateTime": "2025-07-20T14:00:00"},
            "end": {"dateTime": "2025-07-20T20:00:00"}
        }
        mock_calendar_api.COLOR_LEAD = "6"
        mock_calendar_api.COLOR_BOOKED = "11"

        mock_ghl_api = MagicMock()
        mock_ghl_api_class.return_value = mock_ghl_api

        # Create test client
        app.config['TESTING'] = True
        client = app.test_client()

        # Send webhook payload for existing event
        payload = {
            "Opportunity Name": "Smith Wedding",
            "Event Date": "2025-07-20",
            "Photography Hours": "6",
            "Videography Hours": "0",
            "Drone Services": "No",
            "Project Location": "456 Oak Ave, Dallas, TX",
            "Photography Start Time": "2:00 PM",
            "Type of Event": "Wedding",
            "stage": "booked",
            "contact_id": "contact789",
            "Calendar Event ID": "existing_event_456"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["action"] == "updated"
        assert data["is_booked"] is True

        # Verify calendar event was updated
        mock_calendar_api.update_event.assert_called_once()
        call_kwargs = mock_calendar_api.update_event.call_args[1]
        assert call_kwargs["event_id"] == "existing_event_456"
        assert call_kwargs["color_id"] == "11"

    @patch('execution.webhook_server.GoHighLevelAPI')
    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_full_workflow_with_minimal_data(self, mock_calendar_api_class, mock_ghl_api_class):
        """Test workflow with minimal required data."""
        from execution.webhook_server import app

        # Setup mocks
        mock_calendar_api = MagicMock()
        mock_calendar_api_class.return_value = mock_calendar_api
        mock_calendar_api.create_event.return_value = {
            "id": "minimal_event",
            "summary": "Event (Lead)"
        }
        mock_calendar_api.COLOR_LEAD = "6"
        mock_calendar_api.COLOR_BOOKED = "11"

        mock_ghl_api = MagicMock()
        mock_ghl_api_class.return_value = mock_ghl_api

        app.config['TESTING'] = True
        client = app.test_client()

        # Minimal payload
        payload = {
            "Opportunity Name": "Test Event",
            "contact_id": "test_contact"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should still succeed with defaults
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"


class TestErrorHandling:
    """Test error scenarios."""

    @patch('execution.webhook_server.GoHighLevelAPI')
    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_calendar_api_error(self, mock_calendar_api_class, mock_ghl_api_class):
        """Test handling of calendar API errors."""
        from execution.webhook_server import app

        mock_calendar_api = MagicMock()
        mock_calendar_api_class.return_value = mock_calendar_api
        mock_calendar_api.create_event.side_effect = Exception("Calendar API error")

        mock_ghl_api = MagicMock()
        mock_ghl_api_class.return_value = mock_ghl_api

        app.config['TESTING'] = True
        client = app.test_client()

        payload = {
            "Opportunity Name": "Test Event",
            "contact_id": "test123"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should return error
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    @patch('execution.webhook_server.GoHighLevelAPI')
    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_ghl_update_fails_but_calendar_succeeds(self, mock_calendar_api_class, mock_ghl_api_class):
        """Test that webhook succeeds even if GHL update fails."""
        from execution.webhook_server import app

        mock_calendar_api = MagicMock()
        mock_calendar_api_class.return_value = mock_calendar_api
        mock_calendar_api.create_event.return_value = {
            "id": "event123",
            "summary": "Test Event"
        }
        mock_calendar_api.COLOR_LEAD = "6"

        mock_ghl_api = MagicMock()
        mock_ghl_api_class.return_value = mock_ghl_api
        mock_ghl_api.update_contact_calendar_event_id.side_effect = Exception("GHL API error")

        app.config['TESTING'] = True
        client = app.test_client()

        payload = {
            "Opportunity Name": "Test Event",
            "contact_id": "test123"
        }

        response = client.post(
            '/webhook/calendar-ghl',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should still succeed because calendar was created
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
