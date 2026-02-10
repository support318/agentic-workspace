"""
Email lead extraction using AI (Gemini) with regex fallback.

This module extracts structured lead data from wedding vendor platform
emails using a hybrid approach:
1. Primary: Google Gemini API for flexible, intelligent extraction
2. Fallback: Regex patterns for each platform when API fails
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from dotenv import load_dotenv
from models.lead_data import LeadData, create_lead_from_extraction

load_dotenv()

logger = logging.getLogger(__name__)


# Platform detection patterns
PLATFORM_PATTERNS = {
    'WeddingWire': [
        r'weddingwire\.com',
        r'WeddingWire',
        r'from WeddingWire'
    ],
    'TheKnot': [
        r'theknot\.com',
        r'theknot',
        r'from The Knot'
    ],
    'Zola': [
        r'zola\.com',
        r'from Zola',
        r'Zola Wedding'
    ],
    'StyleMePretty': [
        r'stylemepretty\.(com|com)',
        r'Style Me Pretty',
        r'StyleMePretty'
    ]
}


# Regex extraction patterns for fallback
REGEX_PATTERNS = {
    'WeddingWire': {
        'name': [
            r'(?:Inquiry from|Name:?|Contact:?)\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+is interested'
        ],
        'email': [
            r'([\w\.-]+@[\w\.-]+\.\w+)',
        ],
        'phone': [
            r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s*\d{3}[-.\s]?\d{4})',
        ],
        'wedding_date': [
            r'(?:wedding\s*date|date|event\s*date)[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})',
            r'for\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        ],
        'location': [
            r'(?:location|venue|city|where)[:\s]+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)',
        ],
        'message': [
            r'(?:message|comments|inquiry|question)[:\s\n]+(.*?)(?:\n\n|\Z)',
        ]
    },
    'TheKnot': {
        'name': [
            r'(?:From|Name|Contact)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ],
        'email': [
            r'[Ee]mail[:\s]+([\w\.-]+@[\w\.-]+\.\w+)',
        ],
        'phone': [
            r'[Pp]hone[:\s]+(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
        ],
        'wedding_date': [
            r'(?:Wedding\s*Date|Date)[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        ],
        'location': [
            r'(?:Location|Venue|City)[:\s]+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)',
        ],
    },
    'Zola': {
        'name': [
            r'([A-Z][a-z]+ [A-Z][a-z]+) & [A-Z][a-z]+ [A-Z][a-z]+ sent you',
            r'(?:Name|From)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ],
        'email': [
            r'Couple email: ([\w\.-]+@[\w\.-]+\.\w+)',
            r'([\w\.-]+@[\w\.-]+\.\w+)',
        ],
        'phone': [
            r'Couple phone: (\d{10})',
            r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
        ],
        'wedding_date': [
            r'Desired day: ([A-Z][a-z]+ \d{1,2}, \d{4})',
            r'Wedding\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
        ],
        'location': [
            r'Wedding Location: ([A-Z][a-z]+(?:, [A-Z]{2})?)',
        ],
        'message': [
            r'Their note to you\s*“([^”]+)”',
        ],
    },
    'StyleMePretty': {
        'name': [
            r'Inquiry\s+from\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ],
        'email': [
            r'([\w\.-]+@[\w\.-]+\.\w+)',
        ],
        'phone': [
            r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
        ],
    }
}


class EmailExtractor:
    """
    Extract lead data from wedding vendor platform emails.

    Uses Google Gemini API for intelligent extraction with regex fallback.
    """

    # Extraction prompt template
    EXTRACTION_PROMPT = """You are a data extraction assistant for wedding vendor leads.
Extract the following information from this email. If a field is not found, return null.

Email to analyze:
{email_text}

Email headers:
From: {from_addr}
Subject: {subject}

Return ONLY a valid JSON object with these exact keys:
{{
  "name": "full name of person inquiring",
  "email": "email address",
  "phone": "phone number (10 digits)",
  "wedding_date": "wedding date in YYYY-MM-DD format",
  "location": "venue name or city/state",
  "partner_name": "fiance's name if mentioned",
  "services_interested": "photography, videography, drone, etc.",
  "budget": "budget if mentioned",
  "message": "the main inquiry message",
  "source_platform": "one of: WeddingWire, TheKnot, Zola, or StyleMePretty"
}}

Rules:
- If date is in MM/DD/YYYY or DD/MM/YYYY format, convert to YYYY-MM-DD
- If date is "June 15, 2025", convert to "2025-06-15"
- Normalize phone to just digits (e.g., "5551234567")
- Detect the platform from email content/signature
- Return null for any missing fields
- Return ONLY the JSON, no other text

JSON:"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize email extractor.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Gemini model to use (defaults to gemini-2.0-flash-exp or gemini-1.5-flash)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')

        # Try different model names based on availability
        self.model = model or os.getenv('EXTRACTION_MODEL', 'gemini-2.0-flash-exp')

        self.use_ai = False

        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
                self.use_ai = True
                logger.info(f"EmailExtractor initialized with Gemini model: {self.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}. Using regex-only mode.")
                self.use_ai = False
        else:
            if not self.api_key:
                logger.warning("No Google API key found. Using regex-only extraction.")
            elif not GENAI_AVAILABLE:
                logger.warning("google-generativeai not installed. Run: pip install google-generativeai")
            self.use_ai = False

        if not self.use_ai:
            logger.info("EmailExtractor running in regex-only mode")

    def detect_platform(self, email_text: str, headers: Dict[str, str]) -> Optional[str]:
        """
        Detect which platform the email came from.

        Args:
            email_text: Email body text
            headers: Email headers

        Returns:
            Platform name or None
        """
        combined_text = email_text + " " + headers.get('from', '') + " " + headers.get('subject', '')

        for platform, patterns in PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.debug(f"Detected platform: {platform}")
                    return platform

        logger.warning("Could not detect platform from email")
        return None

    def extract_with_ai(
        self,
        email_text: str,
        from_addr: str,
        subject: str,
        headers: Dict[str, str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract lead data using Gemini API.

        Args:
            email_text: Email body text
            from_addr: From address
            subject: Email subject
            headers: Email headers

        Returns:
            Extracted data dict or None if extraction fails
        """
        if not self.use_ai:
            return None

        headers = headers or {}

        # Truncate very long emails to avoid token limits
        max_length = 15000
        if len(email_text) > max_length:
            email_text = email_text[:max_length]
            logger.debug("Truncated email text for AI extraction")

        prompt = self.EXTRACTION_PROMPT.format(
            email_text=email_text[:8000],
            from_addr=from_addr,
            subject=subject
        )

        try:
            logger.debug("Calling Gemini API for extraction...")

            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=2000,
                )
            )

            # Extract text from response
            content = response.text

            # Clean up markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            extracted = json.loads(content)

            # Validate required fields exist
            if not isinstance(extracted, dict):
                logger.error("AI extraction returned non-dict response")
                return None

            logger.info(f"AI extraction successful, extracted {len([v for v in extracted.values() if v])} fields")
            return extracted

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            if 'content' in locals():
                logger.debug(f"Response content: {content[:500]}")
            return None

        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return None

    def extract_with_regex(
        self,
        email_text: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Extract lead data using regex patterns.

        Args:
            email_text: Email body text
            platform: Detected platform name

        Returns:
            Extracted data dict
        """
        patterns = REGEX_PATTERNS.get(platform, REGEX_PATTERNS.get('WeddingWire', {}))
        extracted = {}

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, email_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    # Clean up the value
                    value = re.sub(r'\s+', ' ', value)
                    extracted[field] = value
                    break

        # Always add the detected platform
        extracted['source_platform'] = platform

        logger.info(f"Regex extraction found {len(extracted)} fields for {platform}")
        return extracted

    def extract(
        self,
        email_text: str,
        from_addr: str,
        subject: str,
        headers: Dict[str, str] = None
    ) -> Optional[LeadData]:
        """
        Extract lead data from email using AI with regex fallback.

        Args:
            email_text: Email body text
            from_addr: From address
            subject: Email subject
            headers: Email headers

        Returns:
            LeadData instance or None if extraction fails
        """
        headers = headers or {}

        # Detect platform first
        platform = self.detect_platform(email_text, headers)

        # Try AI extraction first (if available)
        extracted_data = None
        extraction_method = "regex"

        if self.use_ai:
            extracted_data = self.extract_with_ai(email_text, from_addr, subject, headers)
            if extracted_data:
                extraction_method = "ai"

        # If AI fails or not available, try regex
        if not extracted_data:
            if not self.use_ai:
                logger.debug("Using regex extraction (AI not available)")
            else:
                logger.warning("AI extraction failed, falling back to regex")

            if platform:
                extracted_data = self.extract_with_regex(email_text, platform)
            else:
                logger.error("Cannot use regex fallback - platform unknown")
                return None

        # Validate we have minimum required data
        has_email = bool(extracted_data.get('email'))
        has_phone = bool(extracted_data.get('phone'))

        if not (has_email or has_phone):
            logger.warning("Extracted data missing both email and phone")
            # Still return the data, let the caller decide

        # Override platform if detected
        if platform and not extracted_data.get('source_platform'):
            extracted_data['source_platform'] = platform

        # Create LeadData
        try:
            lead = create_lead_from_extraction(extracted_data, extraction_method)

            # Validate
            if not lead.is_valid():
                logger.warning(f"Extracted lead failed validation: {lead}")
                # Return anyway - might still have useful info

            logger.info(f"Successfully extracted lead: {lead}")
            return lead

        except Exception as e:
            logger.error(f"Failed to create LeadData: {e}")
            return None


def extract_lead_from_email(
    email_text: str,
    from_addr: str,
    subject: str,
    headers: Dict[str, str] = None
) -> Optional[LeadData]:
    """
    Convenience function to extract lead data from email.

    Args:
        email_text: Email body text
        from_addr: From address
        subject: Email subject
        headers: Email headers

    Returns:
        LeadData instance or None if extraction fails
    """
    extractor = EmailExtractor()
    return extractor.extract(email_text, from_addr, subject, headers)


if __name__ == "__main__":
    # Test the extractor
    logging.basicConfig(level=logging.DEBUG)

    # Sample email text
    sample_email = """
    New inquiry from WeddingWire

    Name: Sarah Johnson
    Email: sarah.johnson@email.com
    Phone: (555) 123-4567

    Wedding Date: June 15, 2025
    Location: Austin, TX

    Message:
    Hi, we're looking for a photographer and videographer for our wedding.
    We're also interested in drone services. Our budget is around $5000.

    Thanks,
    Sarah
    """

    extractor = EmailExtractor()
    lead = extractor.extract(
        email_text=sample_email,
        from_addr="notifications@weddingwire.com",
        subject="New Inquiry from WeddingWire"
    )

    if lead:
        print(f"\nExtracted Lead:")
        print(f"  Name: {lead.name}")
        print(f"  Email: {lead.email}")
        print(f"  Phone: {lead.phone}")
        print(f"  Wedding Date: {lead.wedding_date}")
        print(f"  Location: {lead.location}")
        print(f"  Platform: {lead.source_platform}")
        print(f"  Confidence: {lead.get_confidence_score():.2%}")
    else:
        print("Failed to extract lead")
