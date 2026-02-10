"""
Lead data model with validation for email-extracted wedding vendor leads.

This module defines the LeadData dataclass which represents the structured
data extracted from wedding vendor platform emails (WeddingWire, The Knot,
Zola, StyleMePretty).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class LeadData:
    """
    Structured lead data extracted from wedding vendor platform emails.

    All fields are optional as email formats vary significantly between platforms.
    The validation methods ensure data quality before GHL contact creation.
    """

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    wedding_date: Optional[str] = None  # YYYY-MM-DD format
    location: Optional[str] = None
    partner_name: Optional[str] = None
    services_interested: Optional[str] = None
    budget: Optional[str] = None
    message: Optional[str] = None
    source_platform: Optional[str] = None  # WeddingWire, TheKnot, Zola, StyleMePretty

    # Metadata
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    extraction_method: str = "unknown"  # "ai" or "regex"

    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if self.email:
            self.email = self._normalize_email(self.email)
        if self.phone:
            self.phone = self._normalize_phone(self.phone)
        if self.wedding_date:
            self.wedding_date = self._normalize_date(self.wedding_date)
        if self.source_platform:
            self.source_platform = self._normalize_platform(self.source_platform)

    @staticmethod
    def _normalize_email(email: str) -> Optional[str]:
        """Normalize email address by trimming and lowercasing."""
        if not email:
            return None
        email = email.strip().lower()
        # Basic email validation
        if re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email):
            return email
        logger.warning(f"Invalid email format: {email}")
        return None

    @staticmethod
    def _normalize_phone(phone: str) -> Optional[str]:
        """Normalize phone number to digits only."""
        if not phone:
            return None
        # Extract all digits
        digits = re.sub(r'[^\d]', '', phone)
        if len(digits) >= 10:
            # Return format: XXXXXXXXXX or with country code
            return digits[-10:] if len(digits) == 10 else digits
        logger.warning(f"Invalid phone number: {phone}")
        return None

    @staticmethod
    def _normalize_date(date_str: str) -> Optional[str]:
        """
        Normalize various date formats to YYYY-MM-DD.

        Handles:
        - MM/DD/YYYY, DD/MM/YYYY
        - Month DD, YYYY
        - YYYY-MM-DD
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Already in YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        # Try MM/DD/YYYY or DD/MM/YYYY
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
        if match:
            month, day, year = match.groups()
            # Assume MM/DD/YYYY for US-based platforms
            try:
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except ValueError:
                pass

        # Try Month DD, YYYY (e.g., "June 15, 2025")
        match = re.match(r'^([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})$', date_str)
        if match:
            month_name, day, year = match.groups()
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            month_num = month_map.get(month_name.lower())
            if month_num:
                try:
                    return f"{year}-{month_num:02d}-{int(day):02d}"
                except ValueError:
                    pass

        logger.warning(f"Could not normalize date: {date_str}")
        return None

    @staticmethod
    def _normalize_platform(platform: str) -> Optional[str]:
        """Normalize platform name."""
        if not platform:
            return None
        platform = platform.strip().lower()
        platform_map = {
            'weddingwire': 'WeddingWire',
            'the knot': 'TheKnot',
            'theknot': 'TheKnot',
            'zola': 'Zola',
            'style me pretty': 'StyleMePretty',
            'stylemepretty': 'StyleMePretty',
        }
        return platform_map.get(platform, platform.title())

    def is_valid(self) -> bool:
        """
        Check if lead has minimum required data.

        At minimum, a lead must have either:
        - A valid email, OR
        - A valid phone number
        """
        has_email = bool(self.email)
        has_phone = bool(self.phone)

        if not (has_email or has_phone):
            logger.warning(f"Lead missing required contact info: name={self.name}")
            return False

        return True

    def get_confidence_score(self) -> float:
        """
        Calculate confidence score for extracted data.

        Returns 0.0 to 1.0 based on completeness of data.
        """
        fields = [
            self.name, self.email, self.phone, self.wedding_date,
            self.location, self.partner_name, self.services_interested,
            self.budget, self.message, self.source_platform
        ]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)

    def to_ghl_custom_fields(self) -> List[Dict[str, str]]:
        """
        Convert lead data to GHL custom fields format.

        Returns a list of dicts with 'key' and 'field_value' for fields
        that should be stored as custom fields in GHL.
        """
        custom_fields = []

        field_mapping = {
            'wedding_date': 'wedding_date',
            'location': 'event_location',
            'partner_name': 'partner_name',
            'services_interested': 'services_interested',
            'budget': 'budget',
            'message': 'lead_message',
            'source_platform': 'lead_source',
        }

        for attr, ghl_key in field_mapping.items():
            value = getattr(self, attr, None)
            if value:
                custom_fields.append({
                    'key': ghl_key,
                    'field_value': str(value)
                })

        # Add extraction metadata
        custom_fields.append({
            'key': 'lead_extracted_at',
            'field_value': self.extracted_at
        })
        custom_fields.append({
            'key': 'lead_extraction_method',
            'field_value': self.extraction_method
        })

        return custom_fields

    def split_name(self) -> tuple[str, str]:
        """
        Split name into first and last name.

        Returns:
            Tuple of (first_name, last_name)
        """
        if not self.name:
            return "", ""

        name_parts = self.name.strip().split()
        if len(name_parts) == 0:
            return "", ""
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            # First name is first part, last name is everything else
            return name_parts[0], " ".join(name_parts[1:])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LeadData':
        """Create LeadData from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"LeadData(name={self.name}, email={self.email}, "
            f"phone={self.phone}, platform={self.source_platform}, "
            f"date={self.wedding_date})"
        )


def create_lead_from_extraction(
    extracted_data: Dict[str, Any],
    extraction_method: str = "ai"
) -> LeadData:
    """
    Create LeadData from extraction result.

    Args:
        extracted_data: Dictionary from AI/regex extraction
        extraction_method: 'ai' or 'regex'

    Returns:
        LeadData instance
    """
    return LeadData(
        name=extracted_data.get('name'),
        email=extracted_data.get('email'),
        phone=extracted_data.get('phone'),
        wedding_date=extracted_data.get('wedding_date'),
        location=extracted_data.get('location'),
        partner_name=extracted_data.get('partner_name'),
        services_interested=extracted_data.get('services_interested'),
        budget=extracted_data.get('budget'),
        message=extracted_data.get('message'),
        source_platform=extracted_data.get('source_platform'),
        extraction_method=extraction_method
    )
