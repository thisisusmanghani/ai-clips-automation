"""
Metadata Rebranding Module.
Generates engaging YouTube-optimized titles, descriptions, and tags.
Completely removes any reference to the original source.
"""

import random
import re
from typing import Dict, List, Tuple

# Genre-based title templates (engaging, clickable, no source mention)
TITLE_TEMPLATES = {
    "music_video": [
        "{title} | Official Music Video",
        "{title} - Cinematic Visual Experience",
        "{title} | Visual Masterpiece",
        "{title} - Animated Music Journey",
        "{title} | HD Music Animation",
        "🎵 {title} | Music Video",
        "{title} - Epic Visual Story",
        "{title} | Cinematic Music Video"
    ],
    "character_vlog": [
        "{title} | AI Character Story",
        "{title} - Virtual Life Episode",
        "{title} | Digital Character Diary",
        "Meet {title} | Character Story",
        "{title} - Animated Vlog",
        "{title} | Virtual Being Story",
        "{title} - Character Animation"
    ],
    "script_to_video": [
        "{title} | Animated Story",
        "{title} - Visual Narrative",
        "{title} | Story Animation",
        "{title} - Cinematic Tale",
        "{title} | Short Film Animation",
        "{title} - Animated Short Story"
    ],
    "create_from_scratch": [
        "{title} | Creative Animation",
        "{title} - Artistic Vision",
        "{title} | Digital Art Animation",
        "{title} - Experimental Animation",
        "{title} | Visual Art Story"
    ],
    "asmr_video": [
        "{title} | Relaxing ASMR",
        "{title} - Soothing Visuals",
        "{title} | Calming Animation ASMR",
        "{title} - Sleep & Relaxation",
        "🎧 {title} | ASMR Experience"
    ]
}

# Description templates (SEO optimized, no source mention)
DESCRIPTION_TEMPLATES = {
    "music_video": [
        """🎵 {title}

Experience this stunning visual journey set to music. A cinematic masterpiece that combines beautiful animation with powerful musical storytelling.

▶️ Don't forget to LIKE and SUBSCRIBE for more amazing content!

#MusicVideo #Animation #Cinematic #VisualArt #MusicAnimation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© All rights reserved. For business inquiries, contact us.
""",
        """✨ {title}

Dive into this breathtaking animated music video experience. Every frame is crafted to perfection.

🔔 Subscribe and hit the bell for the latest releases!

#MusicVideo #DigitalArt #Animation #Cinematic #ArtisticVideo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Enjoy responsibly. Share the love!
"""
    ],
    "character_vlog": [
        """👤 {title}

Follow this unique character's journey through life, emotions, and adventures. A glimpse into the world of digital storytelling.

💫 Like & Subscribe for more character stories!

#CharacterAnimation #VirtualCharacter #DigitalStorytelling #Animation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
New episodes coming soon!
"""
    ],
    "script_to_video": [
        """📖 {title}

A beautifully animated story that brings imagination to life. Watch as this narrative unfolds through stunning visuals.

🎬 Subscribe for more animated stories!

#AnimatedStory #ShortFilm #Animation #VisualNarrative #Storytelling

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    ],
    "create_from_scratch": [
        """🎨 {title}

Pure creative expression through animation. An artistic journey that pushes the boundaries of visual storytelling.

✨ Support creativity - Like & Subscribe!

#DigitalArt #CreativeAnimation #ArtisticVideo #Experimental #Animation
"""
    ],
    "asmr_video": [
        """🎧 {title}

Relax and unwind with this calming ASMR animation experience. Perfect for sleep, study, or meditation.

😌 Subscribe for more relaxing content!

#ASMR #Relaxing #Calming #SleepAid #Meditation #RelaxingAnimation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Best enjoyed with headphones 🎧
"""
    ]
}

# Tags by category (SEO optimized)
TAGS = {
    "music_video": [
        "music video", "animation", "cinematic", "visual music", "animated music video",
        "hd music video", "music animation", "artistic video", "visual art", "musical journey",
        "cinematic music", "epic music video", "beautiful animation", "music storytelling"
    ],
    "character_vlog": [
        "character animation", "virtual character", "ai character", "animated vlog",
        "digital character", "character story", "virtual being", "animated story",
        "character diary", "digital storytelling", "animated character"
    ],
    "script_to_video": [
        "animated story", "short film", "animation", "visual narrative", "story animation",
        "animated short", "cinematic story", "visual storytelling", "narrative animation"
    ],
    "create_from_scratch": [
        "creative animation", "digital art", "artistic animation", "experimental video",
        "visual art", "creative video", "artistic expression", "animation art"
    ],
    "asmr_video": [
        "asmr", "relaxing", "calming", "sleep", "meditation", "relaxing animation",
        "asmr animation", "soothing", "ambient", "peaceful", "sleep aid", "stress relief"
    ]
}

# Shorts-specific additions
SHORTS_TITLE_SUFFIX = [" #Shorts", " | Shorts", ""]
SHORTS_TAGS_EXTRA = ["shorts", "youtube shorts", "short video", "viral", "trending"]


def clean_title(title: str) -> str:
    """Clean and improve the original title."""
    # Remove any source-specific text patterns
    patterns_to_remove = [
        r'\bopenart\b', r'\bopen\s*art\b', r'\bai\s*generated\b',
        r'\bstory\s*art\b', r'\bcommunity\b', r'—\s*$', r'-\s*$'
    ]
    
    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra spaces and punctuation
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'^[—\-:|\s]+', '', cleaned)
    cleaned = re.sub(r'[—\-:|\s]+$', '', cleaned)
    
    # Capitalize properly
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
    
    return cleaned or "Amazing Animation"


def generate_rebranded_metadata(video_info: Dict, is_short: bool = False) -> Dict:
    """
    Generate completely rebranded metadata for YouTube upload.
    No mention of original source anywhere.
    """
    category = video_info.get("category", "music_video")
    original_title = video_info.get("title", "Untitled")
    
    # Clean the title
    clean = clean_title(original_title)
    
    # Select template
    templates = TITLE_TEMPLATES.get(category, TITLE_TEMPLATES["music_video"])
    title_template = random.choice(templates)
    
    # Generate title
    new_title = title_template.format(title=clean)
    
    # Add shorts suffix if applicable
    if is_short:
        new_title = new_title + random.choice(SHORTS_TITLE_SUFFIX)
    
    # Ensure title is under YouTube's limit (100 chars)
    if len(new_title) > 100:
        new_title = clean[:90] + "..."
    
    # Generate description
    desc_templates = DESCRIPTION_TEMPLATES.get(category, DESCRIPTION_TEMPLATES["music_video"])
    new_description = random.choice(desc_templates).format(title=clean)
    
    # Ensure description is under limit (5000 chars)
    new_description = new_description[:4900]
    
    # Generate tags
    base_tags = TAGS.get(category, TAGS["music_video"]).copy()
    if is_short:
        base_tags.extend(SHORTS_TAGS_EXTRA)
    
    # Add title words as tags
    title_words = [w for w in clean.lower().split() if len(w) > 3]
    base_tags.extend(title_words[:5])
    
    # Dedupe and limit tags
    unique_tags = list(dict.fromkeys(base_tags))[:30]  # YouTube allows up to 500 chars total
    
    return {
        "title": new_title,
        "description": new_description,
        "tags": unique_tags,
        "category_id": get_youtube_category_id(category),
        "privacy_status": "public",
        "is_short": is_short,
        "original_id": video_info.get("id"),
        "original_category": category
    }


def get_youtube_category_id(category: str) -> str:
    """Map our categories to YouTube category IDs."""
    # YouTube category IDs
    # 1: Film & Animation
    # 10: Music
    # 22: People & Blogs
    # 24: Entertainment
    
    mapping = {
        "music_video": "10",  # Music
        "character_vlog": "22",  # People & Blogs
        "script_to_video": "1",  # Film & Animation
        "create_from_scratch": "1",  # Film & Animation
        "asmr_video": "24"  # Entertainment
    }
    return mapping.get(category, "24")


def classify_as_short(video_info: Dict) -> bool:
    """Determine if video should be uploaded as a YouTube Short."""
    width = video_info.get("width", 1920)
    height = video_info.get("height", 1080)
    duration = video_info.get("duration_sec", 999)
    
    # Portrait orientation (9:16 or similar)
    is_portrait = height > width
    
    # Under 60 seconds is ideal for shorts, up to 3 min allowed
    short_duration = duration <= 60  # Ideal shorts length
    
    # Must be portrait AND short duration
    return is_portrait and short_duration


if __name__ == "__main__":
    # Test the rebranding
    test_video = {
        "id": "test123",
        "title": "Ashes, Heart, and Horizon — OpenArt Community",
        "category": "music_video",
        "width": 1920,
        "height": 1080,
        "duration_sec": 180
    }
    
    result = generate_rebranded_metadata(test_video)
    print("=== REBRANDED METADATA ===")
    print(f"Title: {result['title']}")
    print(f"Description:\n{result['description']}")
    print(f"Tags: {', '.join(result['tags'][:10])}...")
    print(f"Is Short: {result['is_short']}")
