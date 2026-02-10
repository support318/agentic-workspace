"""
Google Calendar API wrapper for event management.

Uses either the google-calendar-mcp-server or direct API calls.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Google Calendar API libraries
GOOGLE_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pickle
    GOOGLE_AVAILABLE = True
except ImportError:
    logger.warning("Google API libraries not available. Install with: pip install google-api-python-client google-auth-oauthlib")


class GoogleCalendarAPI:
    """Client for Google Calendar API."""

    # Calendar color IDs
    COLOR_LEAD = "6"      # Orange/tangerine for leads
    COLOR_BOOKED = "11"   # Red for booked events
    COLOR_DEFAULT = "1"   # Blue (default)

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, calendar_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize Google Calendar client.

        Args:
            calendar_id: Calendar email address (default: support@candidstudios.net)
            credentials_path: Path to OAuth credentials JSON
        """
        self.calendar_id = calendar_id or os.getenv('GOOGLE_CALENDAR_ID', 'support@candidstudios.net')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.service = None

        if GOOGLE_AVAILABLE and self.credentials_path:
            self._authenticate()

    def _authenticate(self):
        """Set up OAuth2 authentication."""
        creds = None
        token_path = os.path.join(os.path.dirname(self.credentials_path), 'token.pickle')

        # Load existing token if available
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('calendar', 'v3', credentials=creds)
        logger.info(f"Authenticated to Google Calendar: {self.calendar_id}")

    def create_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
        color_id: Optional[str] = None,
        timezone: str = "America/New_York"
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            title: Event title
            start: Start datetime in ISO format or "YYYY-MM-DD"
            end: End datetime in ISO format or "YYYY-MM-DD"
            description: Event description (HTML supported)
            location: Event location
            color_id: Calendar color ID (6=lead, 11=booked)
            timezone: Timezone for the event

        Returns:
            Created event data with 'id' field
        """
        if not self.service:
            raise RuntimeError("Google Calendar service not authenticated")

        # Parse datetime strings
        is_all_day = 'T' not in start

        event_body = {
            'summary': title,
            'location': location,
            'description': description,
            'colorId': color_id or self.COLOR_LEAD,
        }

        if is_all_day:
            event_body['start'] = {'date': start}
            event_body['end'] = {'date': end}
        else:
            event_body['start'] = {
                'dateTime': start,
                'timeZone': timezone
            }
            event_body['end'] = {
                'dateTime': end,
                'timeZone': timezone
            }

        try:
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body,
                sendUpdates='all'
            ).execute()

            logger.info(f"Created event: {event.get('id')} - {title}")
            return event

        except HttpError as e:
            logger.error(f"Error creating event: {e}")
            raise

    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        color_id: Optional[str] = None,
        timezone: str = "America/New_York"
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            event_id: Google Calendar event ID
            title: Event title
            start: Start datetime
            end: End datetime
            description: Event description
            location: Event location
            color_id: Calendar color ID
            timezone: Timezone for the event

        Returns:
            Updated event data
        """
        if not self.service:
            raise RuntimeError("Google Calendar service not authenticated")

        # First, get existing event
        try:
            existing = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
        except HttpError as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            raise

        # Update fields if provided
        if title is not None:
            # Always strip "(Lead)" from existing title before applying new title
            # This ensures we clean up any "(Lead)" suffix when moving to booked
            existing_title = existing.get('summary', '')
            if '(Lead)' in existing_title or '(Lead)' in existing_title:
                logger.info(f"Stripping '(Lead)' from existing title: {existing_title}")
                # Extract just the opportunity name and services (before "(Lead)")
                parts = existing_title.split(' (Lead)')[0].split(' (Lead)')[0]
                existing['summary'] = parts[0] if parts else existing_title
            existing['summary'] = title
        if description is not None:
            existing['description'] = description
        if location is not None:
            existing['location'] = location
        if color_id is not None:
            existing['colorId'] = color_id

        # Handle datetime updates
        if start is not None or end is not None:
            is_all_day = 'T' not in (start or existing['start'].get('date', ''))

            if start is not None:
                if is_all_day:
                    existing['start'] = {'date': start}
                else:
                    existing['start'] = {'dateTime': start, 'timeZone': timezone}

            if end is not None:
                if is_all_day:
                    existing['end'] = {'date': end}
                else:
                    existing['end'] = {'dateTime': end, 'timeZone': timezone}

        try:
            updated = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=existing,
                sendUpdates='all'
            ).execute()

            logger.info(f"Updated event: {event_id} - {title}")
            return updated

        except HttpError as e:
            logger.error(f"Error updating event: {e}")
            raise

    def find_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a specific event by ID.

        Args:
            event_id: Google Calendar event ID

        Returns:
            Event data or None if not found
        """
        if not self.service:
            raise RuntimeError("Google Calendar service not authenticated")

        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return event
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error(f"Error finding event: {e}")
            raise

    def find_event_by_title_and_date(self, title: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Find an event by title and date.

        Args:
            title: Event title to search for
            date: Date in YYYY-MM-DD format

        Returns:
            Event data or None if not found
        """
        if not self.service:
            raise RuntimeError("Google Calendar service not authenticated")

        try:
            # Search for events on the specific date
            start_of_day = f"{date}T00:00:00Z"
            end_of_day = f"{date}T23:59:59Z"

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_of_day,
                timeMax=end_of_day,
                q=title,  # Search query matches title
                singleEvents=True,
                maxResults=10
            ).execute()

            events = events_result.get('items', [])
            for event in events:
                # Check if this is our event (compare without "(Lead)" suffix)
                event_summary = event.get('summary', '')
                # Remove (Lead) suffix from both for comparison
                event_title_clean = event_summary.replace(' (Lead)', '').replace('(Lead)', '').strip().lower()
                search_title_clean = title.replace(' (Lead)', '').replace('(Lead)', '').strip().lower()

                if event_title_clean == search_title_clean:
                    logger.info(f"Found matching event: {event.get('id')} - {event_summary}")
                    return event

            return None

        except HttpError as e:
            logger.error(f"Error searching for event: {e}")
            return None

    def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 250
    ) -> List[Dict[str, Any]]:
        """
        List events in the calendar.

        Args:
            start_date: Start date in YYYY-MM-DD format (default: today)
            end_date: End date in YYYY-MM-DD format (default: 30 days from now)
            query: Search query to filter events
            max_results: Maximum number of events to return

        Returns:
            List of event dicts
        """
        if not self.service:
            raise RuntimeError("Google Calendar service not authenticated")

        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=f"{start_date}T00:00:00Z",
                timeMax=f"{end_date}T23:59:59Z",
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])

        except HttpError as e:
            logger.error(f"Error listing events: {e}")
            raise

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if deleted successfully
        """
        if not self.service:
            raise RuntimeError("Google Calendar service not authenticated")

        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            logger.info(f"Deleted event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Error deleting event: {e}")
            return False


# Convenience functions for common operations
def create_ghl_event(
    opportunity_name: str,
    event_date: str,
    photo_hours: int = 0,
    video_hours: int = 0,
    has_drone: bool = False,
    is_booked: bool = False,
    pipeline: str = "",
    start_time: str = "10:00 AM",
    event_type: str = "",
    project_location: str = "",
    assigned_photographer: str = "",
    assigned_videographer: str = "",
    calendar_event_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create or update a Google Calendar event from GHL opportunity data.

    This mimics the logic from the n8n workflow.

    Args:
        opportunity_name: Opportunity/event name
        event_date: Event date (YYYY-MM-DD)
        photo_hours: Photography hours
        video_hours: Videography hours
        has_drone: Whether drone services are included
        is_booked: Whether the event is booked (vs lead)
        pipeline: GHL pipeline name (SALES = lead, others = booked)
        start_time: Event start time (e.g., "10:00 AM")
        event_type: Type of event
        project_location: Primary location
        assigned_photographer: Assigned photographer name
        assigned_videographer: Assigned videographer name
        calendar_event_id: Existing event ID (if updating)

    Returns:
        Dict with event data and action taken ('created' or 'updated')
    """
    api = GoogleCalendarAPI()

    # Build services list
    services = []
    if photo_hours > 0:
        services.append("Photo")
    if video_hours > 0:
        services.append("Video")
    if has_drone:
        services.append("Drone")

    # Build title - strip any existing "(Lead)" suffix first
    title = opportunity_name or "Event"
    title = title.replace(" (Lead)", "").replace("(Lead)", "").strip()
    if services:
        title += f" - {'/'.join(services)}"
    if not is_booked:
        title += " (Lead)"

    # Calculate duration
    max_hours = max(photo_hours, video_hours, 4)

    # Parse start time
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

    start_hour, start_minute = parse_time_str(start_time)

    # Parse event date - handle multiple formats from GHL
    # GHL may send: "2025-06-15", "03/01/26T10:00:00", or "03/01/2026"
    parsed_date = None
    if 'T' in event_date:
        # Format: "03/01/26T10:00:00" - extract date part
        date_part = event_date.split('T')[0]
        if '/' in date_part:
            parts = date_part.split('/')
            if len(parts) == 3:
                # Check if year is 2 digits
                year = int(parts[2])
                if year < 100:
                    year += 2000 if year < 50 else 1900
                parsed_date = f"{year:04d}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    elif '/' in event_date:
        # Format: "03/01/2026"
        parts = event_date.split('/')
        if len(parts) == 3:
            year = int(parts[2])
            if year < 100:
                year += 2000 if year < 50 else 1900
            parsed_date = f"{year:04d}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    else:
        # Already in YYYY-MM-DD format
        parsed_date = event_date

    # Build datetimes
    start_datetime = f"{parsed_date}T{start_hour:02d}:{start_minute:02d}:00"

    # Add max_hours for end time
    start_dt = datetime.fromisoformat(start_datetime)
    end_dt = start_dt + timedelta(hours=max_hours)
    end_datetime = end_dt.isoformat()

    # Build description with HTML line breaks and separators
    description_parts = []

    # Add separator before details
    description_parts.append("<hr>")
    description_parts.append("<b>EVENT DETAILS</b>")

    if event_type:
        description_parts.append(f"🎉 Type of Event: {event_type}")
    if photo_hours:
        description_parts.append(f"📸 Photography Hours: {photo_hours}")
    if video_hours:
        description_parts.append(f"🎬 Videography Hours: {video_hours}")
    if has_drone:
        description_parts.append(f"🚁 Drone Services: Yes")
    if project_location:
        description_parts.append(f"📍 Project Location: {project_location}")
    if assigned_photographer:
        description_parts.append(f"👨‍💼 Assigned Photographer: {assigned_photographer}")
    if assigned_videographer:
        description_parts.append(f"👨‍💼 Assigned Videographer: {assigned_videographer}")
    if start_time:
        description_parts.append(f"⏰ Start Time: {start_time}")

    # Add separator after details (with extra line break)
    description_parts.append("<br><hr>")

    description = "<br>".join(description_parts)

    # Determine color
    color_id = api.COLOR_BOOKED if is_booked else api.COLOR_LEAD

    # Create or update
    # If calendar_event_id is provided, verify it exists first
    if calendar_event_id:
        # Verify the event actually exists in Google Calendar
        existing_event = api.find_event(calendar_event_id)
        if existing_event:
            # Event exists, update it
            event = api.update_event(
                event_id=calendar_event_id,
                title=title,
                start=start_datetime,
                end=end_datetime,
                description=description,
                location=project_location,
                color_id=color_id
            )
            logger.info(f"Updated existing event: {calendar_event_id}")
            return {"event": event, "action": "updated"}
        else:
            # Event ID in GHL but event doesn't exist in calendar - create new
            logger.info(f"Event ID {calendar_event_id} not found in calendar, will search for existing by name+date")

    # Search for existing event by title and date (in case GHL doesn't have the event ID)
    # This prevents duplicate events when GHL sends multiple webhooks
    search_result = api.find_event_by_title_and_date(title, parsed_date)
    if search_result:
        # Found existing event, update it
        logger.info(f"Found existing event by title+date: {search_result.get('id')}, updating")
        event = api.update_event(
            event_id=search_result.get('id'),
            title=title,
            start=start_datetime,
            end=end_datetime,
            description=description,
            location=project_location,
            color_id=color_id
        )
        return {"event": event, "action": "updated"}

    # Create new event
    event = api.create_event(
        title=title,
        start=start_datetime,
        end=end_datetime,
        description=description,
        location=project_location,
        color_id=color_id
    )
    logger.info(f"Created new event: {event.get('id')}")
    return {"event": event, "action": "created"}


if __name__ == "__main__":
    # Test the API connection
    try:
        api = GoogleCalendarAPI()
        if api.service:
            print(f"Google Calendar API initialized for: {api.calendar_id}")
            print("Google Calendar API wrapper ready")
        else:
            print("Google Calendar not authenticated. Configure credentials.")
    except Exception as e:
        print(f"Google Calendar initialization error: {e}")
