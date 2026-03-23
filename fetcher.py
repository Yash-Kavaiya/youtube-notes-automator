# fetcher.py — YouTube transcript and metadata fetcher

import re
import logging
import subprocess
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
        r"embed\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_title(video_id: str) -> str:
    """Fetch video title using yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "title", "--no-playlist",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=30
        )
        title = result.stdout.strip()
        if title:
            return title
    except Exception as e:
        logger.warning(f"yt-dlp title fetch failed for {video_id}: {e}")
    return f"Video {video_id}"


def fetch_transcript(url: str) -> dict | None:
    """
    Fetch transcript and metadata for a YouTube video.

    Returns:
        dict with keys: title, url, video_id, transcript_text
        None if transcript is unavailable.
    """
    video_id = extract_video_id(url)
    if not video_id:
        logger.error(f"Could not extract video ID from URL: {url}")
        return None

    logger.info(f"Fetching transcript for video ID: {video_id}")

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(entry["text"] for entry in transcript_list)
    except TranscriptsDisabled:
        logger.warning(f"Transcripts disabled for {video_id}")
        return None
    except NoTranscriptFound:
        # Try any available language
        try:
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcripts.find_generated_transcript(
                [t.language_code for t in transcripts]
            )
            entries = transcript.fetch()
            transcript_text = " ".join(e["text"] for e in entries)
        except Exception as e:
            logger.warning(f"No transcript found for {video_id}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error fetching transcript for {video_id}: {e}")
        return None

    title = get_video_title(video_id)

    return {
        "title": title,
        "url": url,
        "video_id": video_id,
        "transcript_text": transcript_text,
    }


def load_urls_from_file(filepath: str) -> list[str]:
    """Load YouTube URLs from a text file (one per line, # for comments)."""
    urls = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    except FileNotFoundError:
        logger.error(f"URLs file not found: {filepath}")
    return urls
