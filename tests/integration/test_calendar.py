"""
Unit tests for Google Calendar wrapper.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestGoogleCalendarAPI:
    """Test suite for Google Calendar API."""

    def test_color_constants(self):
        """Test color ID constants are defined."""
        from execution.google_calendar import GoogleCalendarAPI

        assert GoogleCalendarAPI.COLOR_LEAD == "6"
        assert GoogleCalendarAPI.COLOR_BOOKED == "11"
        assert GoogleCalendarAPI.COLOR_DEFAULT == "1"


class TestCreateGHLEvent:
    """Test the create_ghl_event convenience function."""

    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_create_event_basic(self, mock_api_class):
        """Test creating a basic event."""
        from execution.google_calendar import create_ghl_event

        # Mock the API instance
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.COLOR_LEAD = "6"
        mock_api.COLOR_BOOKED = "11"
        mock_api.create_event.return_value = {
            "id": "event123",
            "summary": "Test Event"
        }

        result = create_ghl_event(
            opportunity_name="Test Wedding",
            event_date="2025-06-15",
            photo_hours=6,
            video_hours=0,
            has_drone=False,
            is_booked=False
        )

        assert result["action"] == "created"
        assert result["event"]["id"] == "event123"
        mock_api.create_event.assert_called_once()

    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_update_existing_event(self, mock_api_class):
        """Test updating an existing event."""
        from execution.google_calendar import create_ghl_event

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.update_event.return_value = {
            "id": "event123",
            "summary": "Updated Event"
        }

        result = create_ghl_event(
            opportunity_name="Test Wedding",
            event_date="2025-06-15",
            photo_hours=6,
            video_hours=0,
            has_drone=False,
            is_booked=True,
            calendar_event_id="event123"
        )

        assert result["action"] == "updated"
        mock_api.update_event.assert_called_once()

    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_booked_vs_lead_colors(self, mock_api_class):
        """Test color selection based on booked status."""
        from execution.google_calendar import create_ghl_event

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.COLOR_LEAD = "6"
        mock_api.COLOR_BOOKED = "11"
        mock_api.create_event.return_value = {"id": "event1"}

        # Test lead color
        create_ghl_event(
            opportunity_name="Test",
            event_date="2025-06-15",
            is_booked=False
        )
        call_kwargs = mock_api.create_event.call_args[1]
        assert call_kwargs["color_id"] == "6"

        # Test booked color
        create_ghl_event(
            opportunity_name="Test",
            event_date="2025-06-15",
            is_booked=True
        )
        call_kwargs = mock_api.create_event.call_args[1]
        assert call_kwargs["color_id"] == "11"

    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_title_building(self, mock_api_class):
        """Test event title construction."""
        from execution.google_calendar import create_ghl_event

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.create_event.return_value = {"id": "event1"}

        # Test with services
        create_ghl_event(
            opportunity_name="Smith Wedding",
            event_date="2025-06-15",
            photo_hours=6,
            video_hours=4,
            has_drone=True,
            is_booked=False
        )
        call_kwargs = mock_api.create_event.call_args[1]
        assert "Smith Wedding" in call_kwargs["title"]
        assert "Photo" in call_kwargs["title"]
        assert "Video" in call_kwargs["title"]
        assert "Drone" in call_kwargs["title"]
        assert "(Lead)" in call_kwargs["title"]

    @patch('execution.google_calendar.GoogleCalendarAPI')
    def test_title_booked_no_lead_suffix(self, mock_api_class):
        """Test that booked events don't have (Lead) suffix."""
        from execution.google_calendar import create_ghl_event

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.create_event.return_value = {"id": "event1"}

        create_ghl_event(
            opportunity_name="Smith Wedding",
            event_date="2025-06-15",
            is_booked=True
        )
        call_kwargs = mock_api.create_event.call_args[1]
        assert "(Lead)" not in call_kwargs["title"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
