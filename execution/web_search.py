"""
Web search utility for finding wedding vendor leads.
Uses web search to discover vendor directories and listings.
"""

import requests
import re
import time
from typing import List, Dict
from urllib.parse import quote, urljoin

class WebSearcher:
    """Search for wedding vendors in a specific location."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def search_vendors(self, location: str, vendor_type: str = "wedding venues", limit: int = 50) -> List[Dict]:
        """
        Search for vendors in a location.

        Args:
            location: City, region or area
            vendor_type: Type of vendor to search
            limit: Maximum results

        Returns:
            List of vendor dictionaries with basic info
        """
        # Search query construction
        query = f"{vendor_type} in {location}"
        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

        results = []
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            # Parse results from DDG HTML
            # This is a simplified version - in production, use a proper search API
            results = self._parse_ddg_results(response.text, limit)

        except Exception as e:
            print(f"Search error: {e}")

        return results

    def _parse_ddg_results(self, html: str, limit: int) -> List[Dict]:
        """Parse DuckDuckGo HTML results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # Find all result elements
        result_divs = soup.find_all('div', class_='result')

        for div in result_divs[:limit]:
            try:
                title_elem = div.find('a', class_='result__a')
                if not title_elem:
                    continue

                url = title_elem.get('href', '')
                title = title_elem.get_text(strip=True)

                snippet_elem = div.find('a', class_='result__snippet')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
            except Exception as e:
                continue

        return results

    def find_contact_from_website(self, url: str) -> Dict:
        """
        Visit a website and extract contact information.

        Args:
            url: Website URL

        Returns:
            Dictionary with email, phone, social links
        """
        contact_info = {
            'email': None,
            'phone': None,
            'facebook': None,
            'instagram': None,
            'twitter': None
        }

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            # Extract emails
            emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', response.text)
            if emails:
                # Prefer info@, contact@, hello@ emails
                priority_prefixes = ['info', 'contact', 'hello', 'inquiries', 'booking']
                for prefix in priority_prefixes:
                    for email in emails:
                        if email.startswith(prefix + '@'):
                            contact_info['email'] = email
                            break
                    if contact_info['email']:
                        break

                if not contact_info['email']:
                    contact_info['email'] = emails[0]

            # Extract phone numbers (US format)
            phones = re.findall(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s*\d{3}[-.\s]?\d{4})', response.text)
            if phones:
                contact_info['phone'] = phones[0]

            # Extract social media
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'facebook.com' in href and not contact_info['facebook']:
                    contact_info['facebook'] = href
                elif 'instagram.com' in href and not contact_info['instagram']:
                    contact_info['instagram'] = href
                elif 'twitter.com' in href and not contact_info['twitter']:
                    contact_info['twitter'] = href

        except Exception as e:
            print(f"Error scraping {url}: {e}")

        return contact_info


if __name__ == "__main__":
    # Quick test
    searcher = WebSearcher()
    results = searcher.search_vendors("Austin TX", "wedding venues", 5)

    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  - {r['title']}: {r['url']}")
