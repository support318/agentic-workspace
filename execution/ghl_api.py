"""
GoHighLevel (GHL) API wrapper for contact and opportunity management.

API Documentation: https://highlevel.stoplight.io/docs/integrations/
"""

import os
import requests
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from datetime import datetime
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoHighLevelAPI:
    """Client for GoHighLevel LeadConnector API."""

    def __init__(self):
        self.api_token = os.getenv('GHL_API_TOKEN')
        self.location_id = os.getenv('GHL_LOCATION_ID')
        self.base_url = "https://services.leadconnectorhq.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }

        if not self.api_token:
            raise ValueError("GHL_API_TOKEN not configured in .env file")

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an authenticated request to GHL API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            response.raise_for_status()

            # Return empty dict for 204 No Content
            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"GHL API error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"GHL API request failed: {e}")
            raise

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Get a contact by ID.

        Args:
            contact_id: GHL contact ID

        Returns:
            Contact data including custom fields
        """
        endpoint = f"/contacts/{contact_id}"
        return self._request("GET", endpoint)

    def update_contact(self, contact_id: str, custom_fields: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Update contact with custom field values.

        Args:
            contact_id: GHL contact ID
            custom_fields: List of dicts with 'key' and 'field_value'

        Returns:
            Updated contact data
        """
        endpoint = f"/contacts/{contact_id}"
        payload = {"customFields": custom_fields}
        return self._request("PUT", endpoint, json=payload)

    def update_contact_calendar_event_id(self, contact_id: str, calendar_event_id: str) -> Dict[str, Any]:
        """
        Update contact with Google Calendar event ID.

        Args:
            contact_id: GHL contact ID
            calendar_event_id: Google Calendar event ID

        Returns:
            Updated contact data
        """
        custom_fields = [
            {
                "key": "google_calendar_event_id_from_make",
                "field_value": calendar_event_id
            }
        ]
        return self.update_contact(contact_id, custom_fields)

    def search_contacts(self, query: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for contacts by query string.

        Args:
            query: Search query (name, email, phone)
            location_id: Optional location ID override

        Returns:
            Search results with contacts list
        """
        location_id = location_id or self.location_id
        params = {
            "query": query,
            "locationId": location_id
        }
        return self._request("GET", "/contacts", params=params)

    def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Get an opportunity by ID.

        Args:
            opportunity_id: GHL opportunity/pipeline ID

        Returns:
            Opportunity data
        """
        endpoint = f"/opportunities/{opportunity_id}"
        return self._request("GET", endpoint)

    def get_pipeline_opportunities(self, pipeline_id: str, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all opportunities in a pipeline.

        Args:
            pipeline_id: Pipeline ID
            location_id: Optional location ID override

        Returns:
            List of opportunities
        """
        location_id = location_id or self.location_id
        params = {
            "pipelineId": pipeline_id,
            "locationId": location_id
        }
        result = self._request("GET", "/opportunities", params=params)
        return result.get("opportunities", [])

    def create_contact(self, email: str, first_name: str = "", last_name: str = "",
                      phone: str = "", location_id: Optional[str] = None,
                      custom_fields: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a new contact.

        Args:
            email: Contact email
            first_name: First name
            last_name: Last name
            phone: Phone number
            location_id: Optional location ID override
            custom_fields: Optional list of custom field dicts

        Returns:
            Created contact data
        """
        location_id = location_id or self.location_id
        payload = {
            "email": email,
            "locationId": location_id
        }

        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if phone:
            payload["phone"] = phone
        if custom_fields:
            payload["customFields"] = custom_fields

        return self._request("POST", "/contacts", json=payload)

    def get_custom_field_value(self, contact: Dict[str, Any], field_key: str) -> Optional[str]:
        """
        Extract a custom field value from contact data.

        Args:
            contact: Contact data from API
            field_key: Custom field key to find

        Returns:
            Field value or None if not found
        """
        custom_fields = contact.get("customFields", [])
        for field in custom_fields:
            if field.get("key") == field_key:
                return field.get("field_value")
        return None

    def search_opportunities(self, query: str, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for opportunities by name.

        Args:
            query: Search query (opportunity name)
            location_id: Optional location ID override

        Returns:
            List of matching opportunities
        """
        location_id = location_id or self.location_id
        url = f"{self.base_url}/opportunities/search"
        payload = {
            "locationId": location_id,
            "query": query
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("opportunities", [])
        except requests.exceptions.HTTPError as e:
            logger.error(f"GHL API search error: {e.response.status_code} - {e.response.text}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"GHL API search failed: {e}")
            return []

    def get_pipelines(self, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pipelines for the location.

        Args:
            location_id: Optional location ID override

        Returns:
            List of pipelines with stages
        """
        location_id = location_id or self.location_id
        url = f"{self.base_url}/opportunities/pipelines"
        params = {"locationId": location_id}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("pipelines", [])
        except requests.exceptions.HTTPError as e:
            logger.error(f"GHL API pipelines error: {e.response.status_code} - {e.response.text}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"GHL API pipelines failed: {e}")
            return []

    def get_pipeline_name_for_opportunity(self, opportunity_name: str) -> Optional[str]:
        """
        Get the pipeline name for an opportunity by searching for it.

        Args:
            opportunity_name: Name of the opportunity

        Returns:
            Pipeline name (e.g., "1. SALES", "2. PLANNING") or None
        """
        # Try multiple search strategies to handle apostrophes and special characters
        search_queries = [
            opportunity_name,  # Full name
            opportunity_name.split("'")[0],  # Before apostrophe (e.g., "Ryan & Alison")
            opportunity_name.split(" ")[0],  # First word only
        ]

        opportunities = []
        for query in search_queries:
            opportunities = self.search_opportunities(query)
            if opportunities:
                logger.info(f"Found {len(opportunities)} opportunities with query: '{query}'")
                break

        if not opportunities:
            logger.warning(f"No opportunity found with name: {opportunity_name}")
            return None

        # Get the first matching opportunity
        opportunity = opportunities[0]
        pipeline_id = opportunity.get("pipelineId")

        if not pipeline_id:
            logger.warning(f"Opportunity {opportunity_name} has no pipeline ID")
            return None

        # Get all pipelines and find the matching one
        pipelines = self.get_pipelines()
        for pipeline in pipelines:
            if pipeline.get("id") == pipeline_id:
                pipeline_name = pipeline.get("name", "")
                logger.info(f"Found pipeline '{pipeline_name}' for opportunity '{opportunity_name}'")
                return pipeline_name

        logger.warning(f"Pipeline ID {pipeline_id} not found in pipelines list")
        return None

    _pipeline_cache = None
    _pipeline_cache_time = None

    def get_pipeline_name_by_id(self, pipeline_id: str) -> Optional[str]:
        """
        Get pipeline name by ID with caching.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline name or None
        """
        from datetime import timedelta

        # Cache pipelines for 5 minutes
        if (self._pipeline_cache is None or
            self._pipeline_cache_time is None or
            datetime.now() - self._pipeline_cache_time > timedelta(minutes=5)):

            pipelines = self.get_pipelines()
            self._pipeline_cache = {p.get("id"): p.get("name") for p in pipelines}
            self._pipeline_cache_time = datetime.now()
            logger.info(f"Refreshed pipeline cache: {len(self._pipeline_cache)} pipelines")

        return self._pipeline_cache.get(pipeline_id)

    def create_opportunity(
        self,
        pipeline_id: str,
        stage_id: str,
        contact_id: str,
        title: str,
        value: Optional[float] = None,
        status: str = "open",
        location_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new opportunity (pipeline deal).

        Args:
            pipeline_id: Pipeline ID
            stage_id: Stage ID within the pipeline
            contact_id: Contact ID to link to
            title: Opportunity/deal title
            value: Monetary value (optional)
            status: 'open' or 'won' or 'lost'
            location_id: Optional location ID override

        Returns:
            Created opportunity data
        """
        location_id = location_id or self.location_id
        payload = {
            "pipelineId": pipeline_id,
            "contactId": contact_id,
            "name": title,  # GHL uses "name" not "title"
            "status": status,
            "locationId": location_id
        }

        if value is not None:
            payload["value"] = value
            payload["monetary"] = True

        # Create the opportunity first (without stage)
        result = self._request("POST", "/opportunities/", json=payload)

        # Then update it to set the stage
        opportunity_id = result.get("opportunity", {}).get("id")
        if opportunity_id and stage_id:
            try:
                self._request("PUT", f"/opportunities/{opportunity_id}", json={
                    "stageId": stage_id,
                    "locationId": location_id
                })
            except Exception as e:
                logger.warning(f"Could not set stage for opportunity {opportunity_id}: {e}")

        return result

    def get_pipeline_id_by_name(self, pipeline_name: str, location_id: Optional[str] = None) -> Optional[str]:
        """
        Get pipeline ID by name.

        Args:
            pipeline_name: Pipeline name (e.g., "SALES", "1. SALES")
            location_id: Optional location ID override

        Returns:
            Pipeline ID or None
        """
        pipelines = self.get_pipelines(location_id)
        for pipeline in pipelines:
            if pipeline_name.lower() in pipeline.get("name", "").lower():
                return pipeline.get("id")
            # Also try exact match
            if pipeline.get("name") == pipeline_name:
                return pipeline.get("id")
        return None

    def get_pipeline_stage_id_by_name(
        self,
        pipeline_id: str,
        stage_name: str,
        location_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Get stage ID within a pipeline by stage name.

        Args:
            pipeline_id: Pipeline ID
            stage_name: Stage name (e.g., "New Lead")
            location_id: Optional location ID override

        Returns:
            Stage ID or None
        """
        # Get all pipelines (which includes stages)
        pipelines = self.get_pipelines(location_id)

        # Find the pipeline
        pipeline = None
        for p in pipelines:
            if p.get("id") == pipeline_id:
                pipeline = p
                break

        if not pipeline:
            logger.warning(f"Pipeline {pipeline_id} not found")
            return None

        # Search for the stage
        stages = pipeline.get("stages", [])
        for stage in stages:
            if stage_name.lower() in stage.get("name", "").lower():
                return stage.get("id")
            # Also try exact match
            if stage.get("name") == stage_name:
                return stage.get("id")

        logger.warning(f"Stage '{stage_name}' not found in pipeline {pipeline_id}")
        return None


# Convenience functions for common operations
def get_contact_with_calendar_event(contact_id: str) -> Dict[str, Any]:
    """
    Get contact and check if it has a calendar event ID.

    Args:
        contact_id: GHL contact ID

    Returns:
        Dict with contact data and calendar_event_id
    """
    api = GoHighLevelAPI()
    contact = api.get_contact(contact_id)
    calendar_event_id = api.get_custom_field_value(contact, "google_calendar_event_id_from_make")

    return {
        "contact": contact,
        "calendar_event_id": calendar_event_id,
        "has_existing_event": bool(calendar_event_id)
    }


if __name__ == "__main__":
    # Test the API connection
    api = GoHighLevelAPI()
    print(f"GHL API initialized with token: {api.api_token[:20]}...")
    print("GHL API wrapper ready")
