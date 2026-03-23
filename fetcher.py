# fetcher.py — YouTube transcript and metadata fetcher

import re
import logging
import subprocess
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from config import MAX_PLAYLIST_VIDEOS

logger = logging.getLogger(__name__)


# ── URL type detection ─────────────────────────────────────────────────────────

def is_playlist_url(url: str) -> bool:
    """Return True if URL points to a YouTube playlist."""
    return "list=" in url and "watch?v=" not in url or (
        "list=" in url and "playlist" in url
    )


def is_channel_url(url: str) -> bool:
    """Return True if URL points to a YouTube channel (/@handle, /c/, /channel/, /user/)."""
    patterns = [
        r"youtube\.com/@",
        r"youtube\.com/c/",
        r"youtube\.com/channel/",
        r"youtube\.com/user/",
    ]
    return any(re.search(p, url) for p in patterns)


def expand_playlist_or_channel(url: str, limit: int = MAX_PLAYLIST_VIDEOS) -> list[str]:
    """
    Use yt-dlp to extract individual video URLs from a playlist or channel.

    Args:
        url: Playlist or channel URL
        limit: Maximum number of videos to extract

    Returns:
        List of individual YouTube video URLs
    """
    logger.info(f"Expanding URL (limit={limit}): {url}")
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--print", "url",
                "--playlist-end", str(limit),
                "--no-warnings",
                url,
            ],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            logger.error(f"yt-dlp error: {result.stderr.strip()}")
            return []

        urls = [
            line.strip() for line in result.stdout.splitlines()
            if line.strip() and "youtube.com" in line or "youtu.be" in line
        ]

        # yt-dlp sometimes returns bare IDs — normalize them
        normalized = []
        for u in urls:
            if u.startswith("http"):
                normalized.append(u)
            elif re.match(r"^[0-9A-Za-z_-]{11}$", u):
                normalized.append(f"https://www.youtube.com/watch?v={u}")

        logger.info(f"Expanded to {len(normalized)} video URL(s)")
        return normalized

    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return []
    except Exception as e:
        logger.error(f"Failed to expand playlist/channel: {e}")
        return []


def resolve_urls(urls: list[str], limit: int = MAX_PLAYLIST_VIDEOS) -> list[str]:
    """
    Resolve a mixed list of URLs — expanding playlists/channels into individual videos.

    Args:
        urls: List of URLs (can be a mix of videos, playlists, channels)
        limit: Max videos to pull from each playlist/channel

    Returns:
        Flat list of individual video URLs (deduplicated, order preserved)
    """
    resolved = []
    seen = set()

    for url in urls:
        if is_playlist_url(url) or is_channel_url(url):
            kind = "channel" if is_channel_url(url) else "playlist"
            print(f"  📂 Expanding {kind}: {url}")
            expanded = expand_playlist_or_channel(url, limit=limit)
            print(f"     → Found {len(expanded)} video(s)")
            for v in expanded:
                if v not in seen:
                    seen.add(v)
                    resolved.append(v)
        else:
            if url not in seen:
                seen.add(url)
                resolved.append(url)

    return resolved


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
