"""
Upload data to Google Sheets.
Requires Google Sheets API credentials.
"""

import os
from typing import List, Dict
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class GoogleSheetsUploader:
    """Upload data to Google Sheets."""

    def __init__(self, credentials_path=None):
        """Initialize with Google credentials."""
        self.credentials_path = credentials_path or os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            if self.credentials_path and os.path.exists(self.credentials_path):
                scope = ['https://www.googleapis.com/auth/spreadsheets']
                creds = Credentials.from_service_account_file(self.credentials_path, scopes=scope)
                self.gc = gspread.authorize(creds)
                self.authenticated = True
            else:
                print("Warning: No Google credentials configured")
                self.authenticated = False
        except ImportError:
            print("Warning: gspread not installed. Run: pip install gspread")
            self.authenticated = False

    def create_sheet(self, name: str, data: List[Dict], folder_url: str = None) -> str:
        """
        Create a new Google Sheet with data.

        Args:
            name: Sheet name
            data: List of dictionaries (rows)
            folder_url: Optional Google Drive folder URL

        Returns:
            URL of created sheet
        """
        if not self.authenticated:
            return None

        try:
            import gspread

            # Create workbook
            sh = self.gc.create(name)

            # Select first worksheet
            worksheet = sh.sheet1

            # Convert data to DataFrame for easier handling
            df = pd.DataFrame(data)

            # Clear and update
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())

            # Format header row
            worksheet.format("A1:Z1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })

            return sh.url

        except Exception as e:
            print(f"Error creating sheet: {e}")
            return None

    def append_to_sheet(self, sheet_url: str, data: List[Dict]) -> bool:
        """Append data to existing sheet."""
        if not self.authenticated:
            return False

        try:
            import gspread

            sh = self.gc.open_by_url(sheet_url)
            worksheet = sh.sheet1

            df = pd.DataFrame(data)

            # Find first empty row
            existing = worksheet.get_all_values()
            next_row = len(existing) + 1

            # Update starting at next_row
            cell_range = f"A{next_row}"
            worksheet.update(cell_range, df.values.tolist())

            return True

        except Exception as e:
            print(f"Error appending to sheet: {e}")
            return False


def save_simple_csv(data: List[Dict], filename: str) -> str:
    """
    Save data to CSV file as a backup.

    Args:
        data: List of dictionaries
        filename: Output filename

    Returns:
        Full path to saved file
    """
    df = pd.DataFrame(data)

    # Ensure tmp directory exists
    os.makedirs('tmp', exist_ok=True)

    filepath = os.path.join('tmp', filename)
    df.to_csv(filepath, index=False)

    return filepath


if __name__ == "__main__":
    # Test with sample data
    sample_data = [
        {
            'business_name': 'Test Venue',
            'email': 'info@testvenue.com',
            'phone': '555-123-4567',
            'location': 'Austin, TX',
            'vendor_type': 'Venue'
        }
    ]

    # Try CSV fallback
    path = save_simple_csv(sample_data, 'test_leads.csv')
    print(f"Saved to: {path}")
