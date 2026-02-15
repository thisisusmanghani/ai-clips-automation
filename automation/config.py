"""
Configuration for YouTube automation pipeline.
Handles credentials, paths, and settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# API Keys from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

# Paths
DATA_DIR = BASE_DIR / "data"
CATEGORY_DIR = DATA_DIR / "by_category"
DOWNLOADS_DIR = BASE_DIR / "downloaded_videos"
AUTOMATION_DIR = BASE_DIR / "automation"

# Credentials
CLIENT_SECRETS_FILE = BASE_DIR / "client_secret_2_641582013743-kajrg2u96k60kb3gu24c5036o7h8jbh9.apps.googleusercontent.com.json"
OAUTH_TOKEN_FILE = AUTOMATION_DIR / "token.json"

# YouTube API Scopes
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

ALL_SCOPES = YOUTUBE_SCOPES + SHEETS_SCOPES

# Google Sheets Config
SPREADSHEET_NAME = "AI Clips Upload Tracker"
TRACKER_SHEET_NAME = "Uploads"
STATS_SHEET_NAME = "Statistics"

# Video Classification Thresholds
# YouTube Shorts: vertical (9:16 or similar), under 60 seconds ideally but up to 3 mins
SHORTS_MAX_DURATION = 180  # 3 minutes max for shorts
SHORTS_ASPECT_THRESHOLD = 1.0  # height > width (portrait)

# Categories to process
CATEGORIES = [
    "videos_music_video.json",
    "videos_character_vlog.json",
    "videos_script_to_video.json",
    "videos_create_from_scratch.json",
    "videos_asmr_video.json"
]

# Category display names (rebranded - no source mention)
CATEGORY_NAMES = {
    "music_video": "Music Video",
    "character_vlog": "AI Character",
    "script_to_video": "Story Animation",
    "create_from_scratch": "Creative Animation",
    "asmr_video": "Relaxing ASMR"
}

# Upload scheduling config
SCHEDULE_CONFIG = {
    # Optimal hours for English audience (US timezone focus)
    "peak_hours": [9, 12, 15, 17, 18, 19, 20, 21],  # 9AM-9PM spread
    "timezone": "America/New_York",
    "min_gap_hours": 4,  # Minimum hours between uploads
    "max_uploads_per_day": 3,
    "preferred_days": [0, 1, 2, 3, 4, 5, 6]  # All days (0=Monday)
}

# Scraper schedule
SCRAPER_INTERVAL_MONTHS = 2

# File to track uploaded videos
UPLOADED_TRACKER_FILE = DATA_DIR / "uploaded_videos.json"
