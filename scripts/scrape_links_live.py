"""
Scrape community links from OpenArt with real-time JSON output.
Scrolls the correct MUI container (not window) to trigger infinite scroll.

Usage:
  python scrape_links_live.py                      # Scrape "All" (default)
  python scrape_links_live.py "Explainer video"    # Scrape specific category
  python scrape_links_live.py "Music video"
  python scrape_links_live.py "Character vlog"
  python scrape_links_live.py "ASMR video"
"""

import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "All"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, f"community_links_{CATEGORY.lower().replace(' ', '_')}.json")


def save_links(links_list):
    """Save links to JSON file immediately."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"total": len(links_list), "category": CATEGORY, "links": links_list}, f, indent=2)


def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        print("Opening page...")
        page.goto("https://openart.ai/story/create", timeout=120000, wait_until="domcontentloaded")
        time.sleep(10)

        # Click the category chip if not "All"
        if CATEGORY != "All":
            print(f"Selecting category: {CATEGORY}")
            chip = page.locator(f'div[role="button"] span.MuiChip-label:has-text("{CATEGORY}")')
            chip.click()
            time.sleep(5)  # Wait for filtered content to load
            print(f"Category '{CATEGORY}' selected.")

        all_links = []
        seen = set()
        no_new = 0
        max_no_new = 20
        scroll_num = 0

        # Initial grab
        hrefs = page.evaluate("""() => {
            return [...new Set(
                [...document.querySelectorAll('a[href*="/community/"]')]
                .map(a => a.href)
                .filter(h => h.match(/\\/community\\/[A-Za-z0-9]+/))
            )];
        }""")
        for h in hrefs:
            if h not in seen:
                seen.add(h)
                all_links.append(h)
        save_links(all_links)
        print(f"Initial: {len(all_links)} links")

        while no_new < max_no_new:
            scroll_num += 1

            # KEY FIX: Scroll the MUI container div (overflow-y: auto), NOT the window!
            page.evaluate("""() => {
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    const style = getComputedStyle(el);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll')
                        && el.scrollHeight > el.clientHeight + 10
                        && el.querySelectorAll('a[href*="/community/"]').length > 0) {
                        el.scrollTop = el.scrollHeight;
                        break;
                    }
                }
            }""")

            time.sleep(4)

            # Grab current links
            hrefs = page.evaluate("""() => {
                return [...new Set(
                    [...document.querySelectorAll('a[href*="/community/"]')]
                    .map(a => a.href)
                    .filter(h => h.match(/\\/community\\/[A-Za-z0-9]+/))
                )];
            }""")

            new_count = 0
            for h in hrefs:
                if h not in seen:
                    seen.add(h)
                    all_links.append(h)
                    new_count += 1

            if new_count > 0:
                no_new = 0
                save_links(all_links)
                print(f"  Scroll #{scroll_num}: +{new_count} new (total: {len(all_links)})")
            else:
                no_new += 1
                time.sleep(2)
                print(f"  Scroll #{scroll_num}: no new ({no_new}/{max_no_new})")

        browser.close()

    save_links(all_links)
    print(f"\nDone! {len(all_links)} links saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape()
