"""
YouTube Video Uploader.
Handles OAuth, video upload, and scheduling.
"""

import os
import json
import random
import pickle
import httplib2
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    CLIENT_SECRETS_FILE, OAUTH_TOKEN_FILE, YOUTUBE_SCOPES,
    SCHEDULE_CONFIG, AUTOMATION_DIR
)


# Retry configuration
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


class YouTubeUploader:
    """Handles YouTube video uploads with OAuth."""
    
    def __init__(self):
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API using OAuth."""
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
                    str(CLIENT_SECRETS_FILE), YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token
            os.makedirs(AUTOMATION_DIR, exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("YouTube API authenticated successfully!")
    
    def upload_video(
        self, 
        video_path: str, 
        metadata: Dict,
        scheduled_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Path to the video file
            metadata: Dict with title, description, tags, category_id, privacy_status
            scheduled_time: Optional datetime to schedule the video
            
        Returns:
            Tuple of (success: bool, youtube_video_id: str or None)
        """
        try:
            # Prepare request body
            body = {
                'snippet': {
                    'title': metadata['title'][:100],  # YouTube limit
                    'description': metadata['description'][:5000],
                    'tags': metadata.get('tags', [])[:500],  # Max 500 chars total
                    'categoryId': metadata.get('category_id', '22'),
                    'defaultLanguage': 'en',
                    'defaultAudioLanguage': 'en'
                },
                'status': {
                    'privacyStatus': metadata.get('privacy_status', 'public'),
                    'selfDeclaredMadeForKids': False,
                    'embeddable': True,
                    'publicStatsViewable': True
                }
            }
            
            # Handle Shorts
            if metadata.get('is_short', False):
                # YouTube Shorts are auto-detected by aspect ratio and duration
                # Adding #Shorts to title/description helps
                if '#Shorts' not in body['snippet']['title']:
                    if len(body['snippet']['title']) < 90:
                        body['snippet']['title'] += ' #Shorts'
            
            # Handle scheduled publishing
            if scheduled_time and metadata.get('privacy_status') == 'private':
                body['status']['privacyStatus'] = 'private'
                body['status']['publishAt'] = scheduled_time.isoformat() + 'Z'
            
            # Create media upload
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            # Execute upload
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            retry = 0
            
            while response is None:
                try:
                    print(f"Uploading: {metadata['title'][:50]}...")
                    status, response = request.next_chunk()
                    
                    if status:
                        progress = int(status.progress() * 100)
                        print(f"Upload progress: {progress}%")
                        
                except HttpError as e:
                    if e.resp.status in RETRIABLE_STATUS_CODES:
                        retry += 1
                        if retry > MAX_RETRIES:
                            raise
                        sleep_time = random.random() * (2 ** retry)
                        print(f"Retrying in {sleep_time:.1f}s...")
                        import time
                        time.sleep(sleep_time)
                    else:
                        raise
            
            video_id = response.get('id')
            print(f"Upload complete! Video ID: {video_id}")
            print(f"URL: https://youtube.com/watch?v={video_id}")
            
            return True, video_id
            
        except HttpError as e:
            print(f"HTTP error during upload: {e}")
            return False, None
        except Exception as e:
            print(f"Error during upload: {e}")
            return False, None
    
    def get_channel_info(self) -> Dict:
        """Get info about the authenticated channel."""
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'subscribers': channel['statistics'].get('subscriberCount', 0),
                    'videos': channel['statistics'].get('videoCount', 0)
                }
            return {}
        except Exception as e:
            print(f"Error getting channel info: {e}")
            return {}
    
    def get_video_stats(self, video_id: str) -> Dict:
        """Get statistics for a video."""
        try:
            response = self.youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()
            
            if response.get('items'):
                stats = response['items'][0]['statistics']
                return {
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0))
                }
            return {'views': 0, 'likes': 0, 'comments': 0}
        except Exception as e:
            print(f"Error getting video stats: {e}")
            return {'views': 0, 'likes': 0, 'comments': 0}


def generate_schedule_time() -> datetime:
    """Generate a good random upload time for English audience."""
    import pytz
    
    tz = pytz.timezone(SCHEDULE_CONFIG['timezone'])
    now = datetime.now(tz)
    
    # Pick a random day within next 7 days
    days_ahead = random.randint(0, 6)
    target_date = now + timedelta(days=days_ahead)
    
    # Pick a random peak hour
    hour = random.choice(SCHEDULE_CONFIG['peak_hours'])
    minute = random.randint(0, 59)
    
    scheduled = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Ensure it's in the future
    if scheduled <= now:
        scheduled += timedelta(days=1)
    
    return scheduled


def test_uploader():
    """Test the YouTube uploader (authentication only)."""
    print("Testing YouTube Uploader...")
    uploader = YouTubeUploader()
    
    channel = uploader.get_channel_info()
    if channel:
        print(f"Authenticated as: {channel.get('title', 'Unknown')}")
        print(f"Channel ID: {channel.get('id', 'Unknown')}")
        print(f"Subscribers: {channel.get('subscribers', 0)}")
        print(f"Videos: {channel.get('videos', 0)}")
    else:
        print("Could not get channel info")
    
    return uploader


if __name__ == "__main__":
    test_uploader()
