"""
Deduplication and Link Management.
Prevents duplicate scraping, downloading, and uploading.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, List

import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR, CATEGORY_DIR, UPLOADED_TRACKER_FILE


class DeduplicationManager:
    """Manages deduplication across the entire pipeline."""
    
    def __init__(self):
        self.scraped_ids: Set[str] = set()
        self.uploaded_ids: Set[str] = set()
        self.master_links_file = DATA_DIR / "community_links.json"
        self.dedup_log_file = DATA_DIR / "deduplication_log.json"
        
        self._load_all_ids()
    
    def _load_all_ids(self):
        """Load all known video IDs from various sources."""
        # Load from master links file
        if self.master_links_file.exists():
            with open(self.master_links_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                links = data.get('links', [])
                for link in links:
                    # Extract ID from URL
                    vid_id = link.rstrip('/').split('/')[-1]
                    self.scraped_ids.add(vid_id)
        
        # Load from uploaded tracker
        if UPLOADED_TRACKER_FILE.exists():
            with open(UPLOADED_TRACKER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.uploaded_ids = set(data.get('uploaded_ids', []))
        
        print(f"Loaded {len(self.scraped_ids)} scraped IDs")
        print(f"Loaded {len(self.uploaded_ids)} uploaded IDs")
    
    def merge_new_links(self, new_links: List[str]) -> Dict:
        """
        Merge new scraped links with existing ones, removing duplicates.
        Returns stats about what was merged.
        """
        new_ids = set()
        duplicate_ids = set()
        
        for link in new_links:
            vid_id = link.rstrip('/').split('/')[-1]
            if vid_id in self.scraped_ids:
                duplicate_ids.add(vid_id)
            else:
                new_ids.add(vid_id)
                self.scraped_ids.add(vid_id)
        
        stats = {
            'total_new_links': len(new_links),
            'unique_new': len(new_ids),
            'duplicates_skipped': len(duplicate_ids),
            'total_known': len(self.scraped_ids)
        }
        
        # Log deduplication
        self._log_dedup_event('merge_links', stats)
        
        return stats
    
    def get_unuploaded_videos(self) -> List[str]:
        """Get video IDs that have been scraped but not uploaded."""
        return list(self.scraped_ids - self.uploaded_ids)
    
    def mark_as_uploaded(self, video_id: str):
        """Mark a video as uploaded."""
        self.uploaded_ids.add(video_id)
        self._save_uploaded_ids()
    
    def _save_uploaded_ids(self):
        """Save uploaded IDs to file."""
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(UPLOADED_TRACKER_FILE, 'w') as f:
            json.dump({
                'uploaded_ids': list(self.uploaded_ids),
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.uploaded_ids)
            }, f, indent=2)
    
    def _log_dedup_event(self, event_type: str, stats: Dict):
        """Log deduplication events for tracking."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': event_type,
            'stats': stats
        }
        
        # Load existing log
        log_data = []
        if self.dedup_log_file.exists():
            try:
                with open(self.dedup_log_file, 'r') as f:
                    log_data = json.load(f)
            except:
                pass
        
        log_data.append(log_entry)
        
        # Keep only last 100 entries
        log_data = log_data[-100:]
        
        with open(self.dedup_log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics."""
        unuploaded = len(self.scraped_ids - self.uploaded_ids)
        return {
            'total_scraped': len(self.scraped_ids),
            'total_uploaded': len(self.uploaded_ids),
            'pending_upload': unuploaded,
            'upload_percentage': (len(self.uploaded_ids) / len(self.scraped_ids) * 100) if self.scraped_ids else 0
        }


def update_master_links(new_links_file: str) -> Dict:
    """
    Update master links file with new scraped links, deduplicating.
    Called after each scrape run.
    """
    manager = DeduplicationManager()
    
    # Load new links
    with open(new_links_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        new_links = data.get('links', [])
    
    # Merge and get stats
    stats = manager.merge_new_links(new_links)
    
    # Update master file with all unique links
    master_file = DATA_DIR / "community_links.json"
    
    # Load existing
    existing_links = []
    if master_file.exists():
        with open(master_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_links = existing_data.get('links', [])
    
    # Combine and dedupe
    all_links = list(set(existing_links + new_links))
    
    # Save updated master
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(all_links),
            'last_updated': datetime.now().isoformat(),
            'links': all_links
        }, f, indent=2)
    
    print(f"Master links updated: {len(all_links)} total")
    print(f"New unique links added: {stats['unique_new']}")
    print(f"Duplicates skipped: {stats['duplicates_skipped']}")
    
    return stats


if __name__ == "__main__":
    manager = DeduplicationManager()
    stats = manager.get_stats()
    print("\n=== Deduplication Stats ===")
    print(f"Total scraped: {stats['total_scraped']}")
    print(f"Total uploaded: {stats['total_uploaded']}")
    print(f"Pending upload: {stats['pending_upload']}")
    print(f"Upload progress: {stats['upload_percentage']:.1f}%")
