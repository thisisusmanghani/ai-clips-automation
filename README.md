# OpenArt Community Video Scraper & Downloader

## Overview
Tools to scrape, analyze, and download videos from [OpenArt Story Community](https://openart.ai/story/create).

## Project Structure
```
ai clips/
├── README.md
├── scripts/
│   ├── scrape_links_live.py    # Scrape community links (with category filter)
│   ├── scan_video_info.py      # Scan video metadata without downloading
│   └── download_videos.py      # Download videos from links
├── data/
│   ├── community_links.json              # All 1,864 community links
│   ├── community_links_explainer_video.json  # Explainer-only links (269)
│   ├── community_video_info.json         # Full metadata for all videos
│   └── by_category/
│       ├── videos_music_video.json       # 1,099 videos | 105.4 GB
│       ├── videos_character_vlog.json    #   357 videos |   7.3 GB
│       ├── videos_script_to_video.json   #   269 videos |  10.1 GB
│       ├── videos_create_from_scratch.json #  125 videos |   6.3 GB
│       └── videos_asmr_video.json        #    14 videos |   0.3 GB
└── downloaded_videos/                    # Downloaded MP4 files
```

## Scripts

### 1. `scripts/scrape_links_live.py` — Scrape Community Links
Scrolls the MUI container div to trigger infinite scroll and collect all links.

```bash
python scripts/scrape_links_live.py                    # All categories
python scripts/scrape_links_live.py "Explainer video"  # Specific category
python scripts/scrape_links_live.py "Music video"
python scripts/scrape_links_live.py "Character vlog"
python scripts/scrape_links_live.py "ASMR video"
```

### 2. `scripts/scan_video_info.py` — Scan Video Metadata
Visits each page and extracts metadata from `__NEXT_DATA__` JSON. Supports resume.

```bash
python scripts/scan_video_info.py
```

### 3. `scripts/download_videos.py` — Download Videos

```bash
python scripts/download_videos.py --file data/community_links.json
python scripts/download_videos.py https://openart.ai/story/community/ID1 https://openart.ai/story/community/ID2
```

## Stats (Feb 2026)

| Category | Videos | Size | Landscape | Portrait |
|---|---|---|---|---|
| Music Video | 1,099 | 105.4 GB | 923 | 165 |
| Character Vlog | 357 | 7.3 GB | 242 | 115 |
| Explainer Video | 269 | 10.1 GB | 200 | 69 |
| Create From Scratch | 125 | 6.3 GB | 83 | 24 |
| ASMR Video | 14 | 0.3 GB | 9 | 5 |
| **Total** | **1,864** | **~129 GB** | **1,457** | **378** |

## How It Works

1. The community page uses a **MUI scrollable div** (not `window.scroll`) for infinite scroll
2. Each community page embeds video metadata in `<script id="__NEXT_DATA__">` JSON
3. Video URL: `props.pageProps.initShareStory.last_export_url`
4. Metadata: `props.pageProps.initShareStory.metadata` (width, height, duration, fps, size)
5. Videos hosted on `cdn.openart.ai` — direct GET download
