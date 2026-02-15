"""
Download videos from OpenArt community links.

Usage:
  1. Put community links in community_links.txt (one per line)
  2. Run: python download_videos.py
  
  Or pass links as arguments:
    python download_videos.py https://openart.ai/story/community/ID1 https://openart.ai/story/community/ID2

  Or use --file to specify a different input file:
    python download_videos.py --file my_links.txt

Videos are saved to the 'downloaded_videos' folder.
"""

import os
import re
import sys
import json
import time
import requests
from playwright.sync_api import sync_playwright


ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(ROOT_DIR, "downloaded_videos")
LINKS_FILE = os.path.join(ROOT_DIR, "data", "community_links.json")


def extract_video_url(page, url):
    """Visit a community page and extract the main video URL from __NEXT_DATA__."""
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(2)

        content = page.content()

        # Method 1: Extract from __NEXT_DATA__ JSON (most reliable)
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content)
        if match:
            data = json.loads(match.group(1))
            story = data.get("props", {}).get("pageProps", {}).get("initShareStory", {})
            video_url = story.get("last_export_url", "")
            title = story.get("title", "")
            if video_url and video_url.endswith(".mp4"):
                return video_url, title

        # Method 2: Fallback - find the first production video MP4 in source
        mp4_links = re.findall(
            r'https://cdn\.openart\.ai/production/[^\s"\'<>]+/video_[^\s"\'<>]+\.mp4',
            content,
        )
        if mp4_links:
            return mp4_links[0], ""

        return None, ""
    except Exception as e:
        print(f"  ERROR loading {url}: {e}")
        return None, ""


def sanitize_filename(name, max_len=80):
    """Make a string safe for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name[:max_len] if name else ""


def download_video(video_url, save_path):
    """Download a video file with progress display."""
    try:
        r = requests.get(video_url, stream=True, timeout=120)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  Downloading: {pct:.1f}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)", end="")
        print()
        return True
    except Exception as e:
        print(f"\n  Download ERROR: {e}")
        return False


def load_links(args):
    """Load community links from args or file."""
    links = []

    # Check for --file argument
    file_path = LINKS_FILE
    direct_links = []
    i = 0
    while i < len(args):
        if args[i] == "--file" and i + 1 < len(args):
            file_path = args[i + 1]
            i += 2
        else:
            direct_links.append(args[i])
            i += 1

    # If links passed as arguments, use those
    if direct_links:
        links = [l.strip() for l in direct_links if "/community/" in l]
    # Otherwise read from file
    elif os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip() and "/community/" in line]
    else:
        print(f"No links provided. Either:")
        print(f"  1. Create '{file_path}' with one link per line")
        print(f"  2. Pass links as arguments: python download_videos.py <link1> <link2> ...")
        sys.exit(1)

    return links


def main():
    links = load_links(sys.argv[1:])
    if not links:
        print("No valid community links found.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Found {len(links)} community links to process.")
    print(f"Videos will be saved to: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)

    # Track results
    success = 0
    failed = 0
    skipped = 0
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        for i, link in enumerate(links, 1):
            # Extract community ID from URL
            community_id = link.rstrip("/").split("/")[-1]
            print(f"\n[{i}/{len(links)}] {link}")

            # Check if already downloaded
            existing = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(community_id)]
            if existing:
                print(f"  SKIPPED: Already downloaded as {existing[0]}")
                skipped += 1
                results.append({"link": link, "status": "skipped", "file": existing[0]})
                continue

            # Extract video URL
            video_url, title = extract_video_url(page, link)
            if not video_url:
                print(f"  FAILED: Could not find video URL")
                failed += 1
                results.append({"link": link, "status": "failed", "error": "no video URL found"})
                continue

            print(f"  Title: {title or '(untitled)'}")
            print(f"  Video: {video_url}")

            # Build filename
            safe_title = sanitize_filename(title)
            if safe_title:
                filename = f"{community_id}_{safe_title}.mp4"
            else:
                filename = f"{community_id}.mp4"
            save_path = os.path.join(OUTPUT_DIR, filename)

            # Download
            if download_video(video_url, save_path):
                size_mb = os.path.getsize(save_path) / (1024 * 1024)
                print(f"  SAVED: {filename} ({size_mb:.1f} MB)")
                success += 1
                results.append({"link": link, "status": "success", "file": filename, "size_mb": round(size_mb, 1)})
            else:
                failed += 1
                results.append({"link": link, "status": "failed", "error": "download error"})

            # Small delay between pages
            time.sleep(1)

        browser.close()

    # Summary
    print("\n" + "=" * 60)
    print(f"DONE! Processed {len(links)} links:")
    print(f"  Success:  {success}")
    print(f"  Failed:   {failed}")
    print(f"  Skipped:  {skipped}")
    print(f"\nVideos saved to: {os.path.abspath(OUTPUT_DIR)}")

    # Save results log
    log_path = os.path.join(OUTPUT_DIR, "download_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Download log saved to: {log_path}")


if __name__ == "__main__":
    main()
