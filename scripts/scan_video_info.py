"""
Scan all community links and collect video metadata (dimensions, duration, fps, etc.)
WITHOUT downloading the videos. Saves results to community_video_info.json in real-time.

Usage: python scan_video_info.py
"""

import json
import os
import time
import re
from playwright.sync_api import sync_playwright

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INPUT_FILE = os.path.join(DATA_DIR, "community_links.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "community_video_info.json")


def save_results(results):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def scan():
    # Load links
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    links = data["links"] if isinstance(data, dict) else data

    print(f"Scanning {len(links)} links for video metadata...")

    results = {
        "total_scanned": 0,
        "total_links": len(links),
        "videos": [],
        "dimensions_summary": {},
    }

    # Check for existing progress
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
            if existing.get("videos"):
                scanned_ids = {v["id"] for v in existing["videos"]}
                results["videos"] = existing["videos"]
                results["total_scanned"] = len(results["videos"])
                print(f"Resuming from {results['total_scanned']} already scanned...")
            else:
                scanned_ids = set()
    except (FileNotFoundError, json.JSONDecodeError):
        scanned_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        for i, link in enumerate(links, 1):
            community_id = link.rstrip("/").split("/")[-1]

            # Skip already scanned
            if community_id in scanned_ids:
                continue

            try:
                page.goto(link, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

                content = page.content()
                match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content)

                if match:
                    data = json.loads(match.group(1))
                    story = data.get("props", {}).get("pageProps", {}).get("initShareStory", {})

                    meta = story.get("metadata", {})
                    video_url = story.get("last_export_url", "")
                    title = story.get("title", "")
                    category = story.get("category_id", "")
                    width = meta.get("width", 0)
                    height = meta.get("height", 0)
                    duration = meta.get("duration", 0)
                    fps = meta.get("fps", 0)
                    frames = meta.get("frames", 0)
                    file_size = meta.get("size", 0)  # in bytes if available

                    # Aspect ratio
                    if width and height:
                        from math import gcd
                        g = gcd(width, height)
                        aspect = f"{width // g}:{height // g}"
                        dim_key = f"{width}x{height}"
                    else:
                        aspect = "unknown"
                        dim_key = "unknown"

                    info = {
                        "id": community_id,
                        "title": title,
                        "category": category,
                        "width": width,
                        "height": height,
                        "aspect_ratio": aspect,
                        "duration_sec": round(duration, 1),
                        "fps": fps,
                        "frames": frames,
                        "file_size_mb": round(file_size / (1024 * 1024), 1) if file_size else None,
                        "video_url": video_url,
                        "page_url": link,
                    }

                    results["videos"].append(info)
                    results["total_scanned"] = len(results["videos"])

                    # Track dimension distribution
                    results["dimensions_summary"][dim_key] = results["dimensions_summary"].get(dim_key, 0) + 1

                    # Save every 10 videos
                    if len(results["videos"]) % 10 == 0:
                        save_results(results)

                    print(f"  [{i}/{len(links)}] {dim_key:12s} {aspect:8s} {duration:6.1f}s {fps:3d}fps  {title[:40]}")
                else:
                    print(f"  [{i}/{len(links)}] SKIP - no data for {community_id}")

            except Exception as e:
                print(f"  [{i}/{len(links)}] ERROR {community_id}: {str(e)[:60]}")

        browser.close()

    # Final save with sorted summary
    results["dimensions_summary"] = dict(
        sorted(results["dimensions_summary"].items(), key=lambda x: -x[1])
    )
    save_results(results)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Scanned {results['total_scanned']}/{len(links)} videos")
    print(f"\nDimension distribution:")
    for dim, count in results["dimensions_summary"].items():
        print(f"  {dim:15s}: {count} videos")
    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    scan()
