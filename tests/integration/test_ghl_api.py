"""
Unit tests for GoHighLevel API wrapper.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from execution.ghl_api import GoHighLevelAPI


@pytest.fixture
def mock_api():
    """Create a mocked GHL API instance."""
    with patch.object(GoHighLevelAPI, '__init__', lambda self: None):
        api = GoHighLevelAPI()
        api.api_token = "test-token"
        api.base_url = "https://services.leadconnectorhq.com"
        api.headers = {
            "Authorization": "Bearer test-token",
            "Accept": "application/json",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }
        return api


class TestGoHighLevelAPI:
    """Test suite for GoHighLevel API."""

    @patch('execution.ghl_api.requests.request')
    def test_get_contact(self, mock_request, mock_api):
        """Test fetching a contact by ID."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "contact123",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User"
        }
        mock_request.return_value = mock_response

        result = mock_api.get_contact("contact123")

        assert result["id"] == "contact123"
        assert result["email"] == "test@example.com"
        mock_request.assert_called_once()

    @patch('execution.ghl_api.requests.request')
    def test_update_contact_calendar_event_id(self, mock_request, mock_api):
        """Test updating contact with calendar event ID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "contact123",
            "customFields": [
                {"key": "google_calendar_event_id_from_make", "field_value": "event456"}
            ]
        }
        mock_request.return_value = mock_response

        result = mock_api.update_contact_calendar_event_id("contact123", "event456")

        assert result["id"] == "contact123"
        call_args = mock_request.call_args
        assert call_args[0][0] == "PUT"
        assert "contact123" in call_args[0][1]

    @patch('execution.ghl_api.requests.request')
    def test_search_contacts(self, mock_request, mock_api):
        """Test searching for contacts."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "contacts": [
                {"id": "contact1", "email": "test1@example.com"},
                {"id": "contact2", "email": "test2@example.com"}
            ]
        }
        mock_request.return_value = mock_response

        result = mock_api.search_contacts("test")

        assert "contacts" in result
        assert len(result["contacts"]) == 2

    def test_get_custom_field_value(self, mock_api):
        """Test extracting custom field value from contact data."""
        contact = {
            "id": "contact123",
            "customFields": [
                {"key": "google_calendar_event_id_from_make", "field_value": "event456"},
                {"key": "other_field", "field_value": "other_value"}
            ]
        }

        result = mock_api.get_custom_field_value(contact, "google_calendar_event_id_from_make")
        assert result == "event456"

        # Test missing field
        result = mock_api.get_custom_field_value(contact, "missing_field")
        assert result is None


class TestHelperFunctions:
    """Test helper utility functions."""

    def test_parse_hours(self):
        """Test hours parsing from various formats."""
        from execution.webhook_server import parse_hours

        assert parse_hours(4) == 4
        assert parse_hours("6 hours") == 6
        assert parse_hours("8") == 8
        assert parse_hours(None) == 0
        assert parse_hours("") == 0
        assert parse_hours("invalid") == 0

    def test_parse_time_str(self):
        """Test time string parsing."""
        from execution.webhook_server import parse_time_str

        assert parse_time_str("10:00 AM") == (10, 0)
        assert parse_time_str("2:30 PM") == (14, 30)
        assert parse_time_str("12:00 AM") == (0, 0)
        assert parse_time_str("12:00 PM") == (12, 0)
        assert parse_time_str("invalid") == (10, 0)  # Default

    def test_has_drone_service(self):
        """Test drone service detection."""
        from execution.webhook_server import has_drone_service

        assert has_drone_service("Yes") is True
        assert has_drone_service("yes") is True
        assert has_drone_service("true") is True
        assert has_drone_service("y") is True
        assert has_drone_service("No") is False
        assert has_drone_service("false") is False
        assert has_drone_service(None) is False
        assert has_drone_service("") is False

    def test_is_stage_booked(self):
        """Test booked stage detection."""
        from execution.webhook_server import is_stage_booked

        assert is_stage_booked("booked") is True
        assert is_stage_booked("Booked") is True
        assert is_stage_booked("BOOKED") is True
        assert is_stage_booked("lead") is False
        assert is_stage_booked("") is False
        assert is_stage_booked(None) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
