"""
Google Sheets Tracker with Charts/Statistics.
Tracks all uploaded videos and displays live stats.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    CLIENT_SECRETS_FILE, OAUTH_TOKEN_FILE, ALL_SCOPES,
    SPREADSHEET_NAME, TRACKER_SHEET_NAME, STATS_SHEET_NAME,
    DATA_DIR, AUTOMATION_DIR
)


class SheetsTracker:
    """Manages Google Sheets for tracking uploads and statistics."""
    
    def __init__(self):
        self.creds = self._get_credentials()
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = None
        self.tracker_sheet = None
        self.stats_sheet = None
        
    def _get_credentials(self):
        """Get OAuth credentials for Google Sheets."""
        creds = None
        token_path = OAUTH_TOKEN_FILE
        
        # Try to load existing token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid creds, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRETS_FILE), ALL_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token for next run
            os.makedirs(AUTOMATION_DIR, exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def setup_spreadsheet(self, spreadsheet_id: Optional[str] = None) -> str:
        """Create or open the tracking spreadsheet."""
        try:
            if spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            else:
                # Try to find existing spreadsheet
                try:
                    self.spreadsheet = self.client.open(SPREADSHEET_NAME)
                except gspread.SpreadsheetNotFound:
                    # Create new spreadsheet
                    self.spreadsheet = self.client.create(SPREADSHEET_NAME)
                    print(f"Created new spreadsheet: {SPREADSHEET_NAME}")
            
            # Setup sheets
            self._setup_tracker_sheet()
            self._setup_stats_sheet()
            
            return self.spreadsheet.id
            
        except Exception as e:
            print(f"Error setting up spreadsheet: {e}")
            raise
    
    def _setup_tracker_sheet(self):
        """Setup the uploads tracker sheet with headers."""
        try:
            self.tracker_sheet = self.spreadsheet.worksheet(TRACKER_SHEET_NAME)
        except gspread.WorksheetNotFound:
            self.tracker_sheet = self.spreadsheet.add_worksheet(
                title=TRACKER_SHEET_NAME, rows=1000, cols=15
            )
        
        # Check if headers exist
        existing = self.tracker_sheet.row_values(1)
        if not existing or existing[0] != "Video ID":
            headers = [
                "Video ID", "YouTube Video ID", "Title", "Category", 
                "Duration (sec)", "Width", "Height", "Is Short",
                "Upload Date", "Upload Time", "Status", "Views", 
                "Likes", "Comments", "Video URL"
            ]
            self.tracker_sheet.update('A1:O1', [headers])
            
            # Format header row
            self.tracker_sheet.format('A1:O1', {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER"
            })
    
    def _setup_stats_sheet(self):
        """Setup the statistics sheet with formulas and charts."""
        try:
            self.stats_sheet = self.spreadsheet.worksheet(STATS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            self.stats_sheet = self.spreadsheet.add_worksheet(
                title=STATS_SHEET_NAME, rows=50, cols=10
            )
        
        # Setup statistics formulas
        stats_data = [
            ["=== UPLOAD STATISTICS ===", ""],
            ["", ""],
            ["Total Videos Uploaded", f"=COUNTA({TRACKER_SHEET_NAME}!A:A)-1"],
            ["Shorts Uploaded", f"=COUNTIF({TRACKER_SHEET_NAME}!H:H,TRUE)"],
            ["Regular Videos", f"=COUNTIF({TRACKER_SHEET_NAME}!H:H,FALSE)"],
            ["", ""],
            ["=== BY CATEGORY ===", ""],
            ["Music Videos", f"=COUNTIF({TRACKER_SHEET_NAME}!D:D,\"music_video\")"],
            ["Character Vlogs", f"=COUNTIF({TRACKER_SHEET_NAME}!D:D,\"character_vlog\")"],
            ["Story Animations", f"=COUNTIF({TRACKER_SHEET_NAME}!D:D,\"script_to_video\")"],
            ["Creative Animations", f"=COUNTIF({TRACKER_SHEET_NAME}!D:D,\"create_from_scratch\")"],
            ["ASMR Videos", f"=COUNTIF({TRACKER_SHEET_NAME}!D:D,\"asmr_video\")"],
            ["", ""],
            ["=== ENGAGEMENT ===", ""],
            ["Total Views", f"=SUM({TRACKER_SHEET_NAME}!L:L)"],
            ["Total Likes", f"=SUM({TRACKER_SHEET_NAME}!M:M)"],
            ["Total Comments", f"=SUM({TRACKER_SHEET_NAME}!N:N)"],
            ["Avg Views/Video", f"=IFERROR(AVERAGE({TRACKER_SHEET_NAME}!L:L),0)"],
            ["", ""],
            ["=== UPLOAD TIMELINE ===", ""],
            ["Today's Uploads", f"=COUNTIF({TRACKER_SHEET_NAME}!I:I,TODAY())"],
            ["This Week", f"=COUNTIFS({TRACKER_SHEET_NAME}!I:I,\">=\"&(TODAY()-7))"],
            ["This Month", f"=COUNTIFS({TRACKER_SHEET_NAME}!I:I,\">=\"&(TODAY()-30))"],
        ]
        
        self.stats_sheet.update('A1:B23', stats_data)
        
        # Format headers
        self.stats_sheet.format('A1', {"textFormat": {"bold": True, "fontSize": 14}})
        self.stats_sheet.format('A7', {"textFormat": {"bold": True, "fontSize": 12}})
        self.stats_sheet.format('A14', {"textFormat": {"bold": True, "fontSize": 12}})
        self.stats_sheet.format('A20', {"textFormat": {"bold": True, "fontSize": 12}})
    
    def add_upload(self, video_info: Dict, youtube_id: str, metadata: Dict) -> bool:
        """Add a new upload record to the tracker."""
        try:
            now = datetime.now()
            row = [
                video_info.get("id", ""),
                youtube_id,
                metadata.get("title", "")[:100],
                video_info.get("category", ""),
                video_info.get("duration_sec", 0),
                video_info.get("width", 0),
                video_info.get("height", 0),
                metadata.get("is_short", False),
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                "uploaded",
                0,  # Views (updated later)
                0,  # Likes
                0,  # Comments
                f"https://youtube.com/watch?v={youtube_id}"
            ]
            
            self.tracker_sheet.append_row(row)
            print(f"Added to tracker: {metadata.get('title', '')[:50]}...")
            return True
            
        except Exception as e:
            print(f"Error adding to tracker: {e}")
            return False
    
    def get_uploaded_ids(self) -> set:
        """Get all video IDs that have been uploaded."""
        try:
            # Get all values from column A (Video ID)
            ids = self.tracker_sheet.col_values(1)[1:]  # Skip header
            return set(ids)
        except Exception as e:
            print(f"Error getting uploaded IDs: {e}")
            return set()
    
    def update_stats(self, youtube_id: str, views: int, likes: int, comments: int):
        """Update engagement stats for a video."""
        try:
            cell = self.tracker_sheet.find(youtube_id)
            if cell:
                row = cell.row
                self.tracker_sheet.update(f'L{row}:N{row}', [[views, likes, comments]])
        except Exception as e:
            print(f"Error updating stats: {e}")


def test_sheets():
    """Test the sheets tracker."""
    print("Testing Google Sheets Tracker...")
    tracker = SheetsTracker()
    spreadsheet_id = tracker.setup_spreadsheet()
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    
    # Test adding a mock upload
    test_video = {
        "id": "test123",
        "category": "music_video",
        "duration_sec": 180,
        "width": 1920,
        "height": 1080
    }
    test_metadata = {
        "title": "Test Video Title",
        "is_short": False
    }
    
    # Don't actually add test data
    # tracker.add_upload(test_video, "dQw4w9WgXcQ", test_metadata)
    
    print("Sheets tracker setup complete!")
    return spreadsheet_id


if __name__ == "__main__":
    test_sheets()
