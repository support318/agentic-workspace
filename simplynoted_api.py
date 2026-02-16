"""
SimplyNoted API wrapper for sending handwritten cards.

API Documentation: https://api.simplynoted.com
"""

import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplyNotedAPI:
    """Client for the SimplyNoted handwritten card API."""

    RETURN_ADDRESS = {
        "name": "Candid Studios",
        "address1": "210 174th St",
        "address2": "Unit 705",
        "city": "Sunny Isles Beach",
        "state": "FL",
        "zip": "33160",
        "country": "US"
    }

    HANDWRITING_STYLE = "Nemo"

    def __init__(self):
        self.api_key = os.getenv('SIMPLYNOTED_API_KEY')
        self.user_id = os.getenv('SIMPLYNOTED_USER_ID')
        self.base_url = "https://api.simplynoted.com/api"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if not self.api_key:
            raise ValueError("SIMPLYNOTED_API_KEY not configured in .env file")

        # Card ID mappings from env
        self.card_ids = {
            "wedding": os.getenv('SIMPLYNOTED_CARD_WEDDING', '7bf536d5-2e14-4645-b3d1-7ccc9ae5d013'),
            "quinceanera": os.getenv('SIMPLYNOTED_CARD_QUINCE', '18d28c4c-cef6-4a04-bb4b-b570581d4c96'),
            "default": os.getenv('SIMPLYNOTED_CARD_DEFAULT', 'db46a6da-30aa-409d-81ff-448b310666f5'),
        }

    def get_card_id(self, event_type: str) -> str:
        """Get the appropriate card ID based on event type.

        Args:
            event_type: Type of event (wedding, quinceanera, etc.)

        Returns:
            Card product ID
        """
        event_lower = event_type.lower().strip() if event_type else ""

        if "wedding" in event_lower:
            return self.card_ids["wedding"]
        elif "quincea" in event_lower:
            return self.card_ids["quinceanera"]
        else:
            return self.card_ids["default"]

    def send_card(
        self,
        card_id: str,
        message: str,
        recipient: Dict[str, str],
        shipping_date: str
    ) -> Dict[str, Any]:
        """Send a handwritten card via SimplyNoted.

        Args:
            card_id: Product/card ID from SimplyNoted
            message: Custom message to write on the card
            recipient: Dict with name, address1, address2, city, state, zip
            shipping_date: ISO date string (YYYY-MM-DD)

        Returns:
            API response with order details
        """
        payload = {
            "productId": card_id,
            "customMessage": message,
            "handwritingStyle": self.HANDWRITING_STYLE,
            "shippingDate": shipping_date,
            "returnAddress": self.RETURN_ADDRESS,
            "recipients": [
                {
                    "name": recipient.get("name", ""),
                    "address1": recipient.get("address1", ""),
                    "address2": recipient.get("address2", ""),
                    "city": recipient.get("city", ""),
                    "state": recipient.get("state", ""),
                    "zip": recipient.get("zip", ""),
                    "country": recipient.get("country", "US")
                }
            ]
        }

        logger.info(f"Sending card to {recipient.get('name')} - Card: {card_id} - Ship: {shipping_date}")

        try:
            response = requests.post(
                f"{self.base_url}/orders",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"SimplyNoted order created successfully: {result}")
            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"SimplyNoted API error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"SimplyNoted API request failed: {e}")
            raise


if __name__ == "__main__":
    api = SimplyNotedAPI()
    print(f"SimplyNoted API initialized with key: {api.api_key[:12]}...")
    print(f"Card IDs: {api.card_ids}")
    print("SimplyNoted API wrapper ready")

