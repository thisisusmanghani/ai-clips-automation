"""
Main Pipeline Orchestrator.
Downloads videos, rebrands metadata, uploads to YouTube, tracks in Sheets.
"""

import os
import sys
import json
import random
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    CATEGORY_DIR, DOWNLOADS_DIR, DATA_DIR, CATEGORIES,
    UPLOADED_TRACKER_FILE, SCHEDULE_CONFIG
)
from metadata_rebrander import generate_rebranded_metadata, classify_as_short
from youtube_uploader import YouTubeUploader, generate_schedule_time
from sheets_tracker import SheetsTracker


class VideoPipeline:
    """Main orchestrator for the video upload pipeline."""
    
    def __init__(self):
        self.uploader = None
        self.tracker = None
        self.uploaded_ids = set()
        self._load_uploaded_tracker()
    
    def _load_uploaded_tracker(self):
        """Load the list of already uploaded video IDs."""
        try:
            if os.path.exists(UPLOADED_TRACKER_FILE):
                with open(UPLOADED_TRACKER_FILE, 'r') as f:
                    data = json.load(f)
                    self.uploaded_ids = set(data.get('uploaded_ids', []))
                    print(f"Loaded {len(self.uploaded_ids)} previously uploaded IDs")
        except Exception as e:
            print(f"Warning: Could not load uploaded tracker: {e}")
            self.uploaded_ids = set()
    
    def _save_uploaded_tracker(self):
        """Save the uploaded video IDs to prevent duplicates."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(UPLOADED_TRACKER_FILE, 'w') as f:
                json.dump({
                    'uploaded_ids': list(self.uploaded_ids),
                    'last_updated': datetime.now().isoformat(),
                    'total_count': len(self.uploaded_ids)
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving uploaded tracker: {e}")
    
    def initialize(self, spreadsheet_id: Optional[str] = None):
        """Initialize YouTube and Sheets connections."""
        print("Initializing pipeline...")
        
        # Initialize YouTube uploader
        self.uploader = YouTubeUploader()
        
        # Initialize Sheets tracker
        self.tracker = SheetsTracker()
        sheet_id = self.tracker.setup_spreadsheet(spreadsheet_id)
        
        # Also get uploaded IDs from sheets (backup)
        sheet_uploaded = self.tracker.get_uploaded_ids()
        self.uploaded_ids.update(sheet_uploaded)
        
        print(f"Pipeline initialized. Spreadsheet: https://docs.google.com/spreadsheets/d/{sheet_id}")
        return sheet_id
    
    def get_available_videos(self, category: Optional[str] = None, 
                             prefer_shorts: bool = False) -> List[Dict]:
        """Get videos that haven't been uploaded yet."""
        available = []
        
        categories = [category + ".json"] if category else CATEGORIES
        
        for cat_file in categories:
            cat_path = CATEGORY_DIR / cat_file
            if not cat_path.exists():
                continue
            
            with open(cat_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for video in data.get('videos', []):
                video_id = video.get('id')
                if video_id and video_id not in self.uploaded_ids:
                    # Check if it matches shorts preference
                    is_short = classify_as_short(video)
                    if prefer_shorts and not is_short:
                        continue
                    if not prefer_shorts and is_short:
                        continue
                    
                    available.append(video)
        
        return available
    
    def download_video(self, video_info: Dict) -> Optional[str]:
        """Download a video from its URL."""
        video_url = video_info.get('video_url')
        if not video_url:
            print(f"No video URL for {video_info.get('id')}")
            return None
        
        video_id = video_info.get('id', 'unknown')
        output_path = DOWNLOADS_DIR / f"{video_id}.mp4"
        
        # Skip if already downloaded
        if output_path.exists():
            print(f"Already downloaded: {video_id}")
            return str(output_path)
        
        try:
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
            
            print(f"Downloading: {video_info.get('title', video_id)[:50]}...")
            
            response = requests.get(video_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rDownload progress: {progress:.1f}%", end='', flush=True)
            
            print(f"\nDownloaded: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"Error downloading video: {e}")
            if output_path.exists():
                os.remove(output_path)
            return None
    
    def process_single_video(self, video_info: Dict, 
                            schedule: bool = False) -> bool:
        """Process and upload a single video."""
        video_id = video_info.get('id')
        
        if video_id in self.uploaded_ids:
            print(f"Skipping already uploaded: {video_id}")
            return False
        
        # 1. Download the video
        video_path = self.download_video(video_info)
        if not video_path:
            return False
        
        # 2. Generate rebranded metadata
        is_short = classify_as_short(video_info)
        metadata = generate_rebranded_metadata(video_info, is_short)
        
        print(f"Rebranded title: {metadata['title']}")
        print(f"Is Short: {is_short}")
        
        # 3. Determine schedule time
        scheduled_time = None
        if schedule:
            scheduled_time = generate_schedule_time()
            metadata['privacy_status'] = 'private'  # Scheduled videos must be private first
            print(f"Scheduled for: {scheduled_time}")
        
        # 4. Upload to YouTube
        success, youtube_id = self.uploader.upload_video(
            video_path, metadata, scheduled_time
        )
        
        if success and youtube_id:
            # 5. Add to category playlist
            category = video_info.get('category', 'unknown')
            playlist_category = 'shorts' if is_short else category
            playlist_id = self.uploader.get_or_create_playlist(playlist_category)
            if playlist_id:
                self.uploader.add_to_playlist(youtube_id, playlist_id)
            
            # 6. Track in Sheets
            self.tracker.add_upload(video_info, youtube_id, metadata)
            
            # 7. Mark as uploaded
            self.uploaded_ids.add(video_id)
            self._save_uploaded_tracker()
            
            # 8. Clean up downloaded file (optional - save space)
            # os.remove(video_path)
            
            print(f"SUCCESS: Uploaded {metadata['title'][:50]}...")
            return True
        
        return False
    
    def run_batch(self, count: int = 1, category: Optional[str] = None,
                  prefer_shorts: bool = False, schedule: bool = True) -> int:
        """Run a batch upload of videos."""
        print(f"\n=== Starting batch upload: {count} videos ===")
        
        # Get available videos
        available = self.get_available_videos(category, prefer_shorts)
        random.shuffle(available)  # Randomize selection
        
        if not available:
            print("No videos available for upload!")
            return 0
        
        print(f"Found {len(available)} available videos")
        
        # Process up to 'count' videos
        uploaded = 0
        for video in available[:count]:
            try:
                if self.process_single_video(video, schedule):
                    uploaded += 1
                    
                    # Add delay between uploads to avoid rate limits
                    if uploaded < count:
                        delay = random.randint(30, 120)
                        print(f"Waiting {delay}s before next upload...")
                        time.sleep(delay)
                        
            except Exception as e:
                print(f"Error processing video: {e}")
                continue
        
        print(f"\n=== Batch complete: {uploaded}/{count} videos uploaded ===")
        return uploaded


def main():
    """Main entry point for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Video Upload Pipeline')
    parser.add_argument('--count', type=int, default=1, help='Number of videos to upload')
    parser.add_argument('--category', type=str, help='Specific category to upload from')
    parser.add_argument('--shorts', action='store_true', help='Prefer shorts (portrait videos)')
    parser.add_argument('--no-schedule', action='store_true', help='Upload immediately (no scheduling)')
    parser.add_argument('--spreadsheet-id', type=str, help='Existing spreadsheet ID')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = VideoPipeline()
    pipeline.initialize(args.spreadsheet_id)
    
    # Run batch upload
    uploaded = pipeline.run_batch(
        count=args.count,
        category=args.category,
        prefer_shorts=args.shorts,
        schedule=not args.no_schedule
    )
    
    print(f"\nTotal uploaded: {uploaded}")
    return uploaded


if __name__ == "__main__":
    main()
