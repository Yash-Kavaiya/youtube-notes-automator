# fetcher.py — YouTube transcript and metadata fetcher

import re
import json
import logging
import subprocess
import tempfile
import os
from pathlib import Path

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from config import MAX_PLAYLIST_VIDEOS

logger = logging.getLogger(__name__)


# ── URL type detection ─────────────────────────────────────────────────────────

def is_playlist_url(url: str) -> bool:
    """Return True if URL points to a YouTube playlist."""
    return ("list=" in url and "watch?v=" not in url) or (
        "list=" in url and "playlist" in url
    )


def is_channel_url(url: str) -> bool:
    """Return True if URL points to a YouTube channel."""
    patterns = [
        r"youtube\.com/@",
        r"youtube\.com/c/",
        r"youtube\.com/channel/",
        r"youtube\.com/user/",
    ]
    return any(re.search(p, url) for p in patterns)


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


# ── Playlist / channel expansion ──────────────────────────────────────────────

def expand_playlist_or_channel(url: str, limit: int = MAX_PLAYLIST_VIDEOS) -> list[str]:
    """
    Use yt-dlp to extract individual video URLs from a playlist or channel.
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

        urls = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("http"):
                urls.append(line)
            elif re.match(r"^[0-9A-Za-z_-]{11}$", line):
                urls.append(f"https://www.youtube.com/watch?v={line}")

        logger.info(f"Expanded to {len(urls)} video URL(s)")
        return urls

    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return []
    except Exception as e:
        logger.error(f"Failed to expand playlist/channel: {e}")
        return []


def resolve_urls(urls: list[str], limit: int = MAX_PLAYLIST_VIDEOS) -> list[str]:
    """
    Resolve a mixed list of URLs — expanding playlists/channels into individual videos.
    Deduplicates, preserves order.
    """
    resolved = []
    seen = set()

    for url in urls:
        if is_playlist_url(url) or is_channel_url(url):
            kind = "channel" if is_channel_url(url) else "playlist"
            print(f"  >> Expanding {kind}: {url}")
            expanded = expand_playlist_or_channel(url, limit=limit)
            print(f"     -> Found {len(expanded)} video(s)")
            for v in expanded:
                if v not in seen:
                    seen.add(v)
                    resolved.append(v)
        else:
            if url not in seen:
                seen.add(url)
                resolved.append(url)

    return resolved


# ── Transcript fetching ────────────────────────────────────────────────────────

def _fetch_transcript_ytdlp(video_id: str) -> str | None:
    """
    Fetch transcript using yt-dlp --write-auto-subs (more robust, avoids IP blocks).
    Returns plain text transcript or None.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--skip-download",
                    "--write-auto-subs",
                    "--write-subs",
                    "--sub-langs", "en.*",
                    "--sub-format", "json3",
                    "--output", os.path.join(tmpdir, "%(id)s.%(ext)s"),
                    "--no-warnings",
                    url,
                ],
                capture_output=True, text=True, timeout=60
            )

            # Find any .json3 subtitle file written
            subtitle_files = list(Path(tmpdir).glob("*.json3"))
            if not subtitle_files:
                # Try vtt as fallback
                result2 = subprocess.run(
                    [
                        "yt-dlp",
                        "--skip-download",
                        "--write-auto-subs",
                        "--write-subs",
                        "--sub-langs", "en.*",
                        "--sub-format", "vtt",
                        "--output", os.path.join(tmpdir, "%(id)s.%(ext)s"),
                        "--no-warnings",
                        url,
                    ],
                    capture_output=True, text=True, timeout=60
                )
                subtitle_files = list(Path(tmpdir).glob("*.vtt"))

            if not subtitle_files:
                return None

            subs_file = subtitle_files[0]
            raw = subs_file.read_text(encoding="utf-8", errors="replace")

            if subs_file.suffix == ".json3":
                return _parse_json3_transcript(raw)
            elif subs_file.suffix == ".vtt":
                return _parse_vtt_transcript(raw)

        except Exception as e:
            logger.debug(f"yt-dlp subtitle fetch failed for {video_id}: {e}")
            return None


def _parse_json3_transcript(raw: str) -> str:
    """Parse yt-dlp json3 subtitle format to plain text."""
    try:
        data = json.loads(raw)
        texts = []
        for event in data.get("events", []):
            for seg in event.get("segs", []):
                t = seg.get("utf8", "").strip()
                if t and t != "\n":
                    texts.append(t)
        return " ".join(texts)
    except Exception:
        return None


def _parse_vtt_transcript(raw: str) -> str:
    """Parse WebVTT subtitle format to plain text."""
    lines = raw.splitlines()
    texts = []
    for line in lines:
        line = line.strip()
        # Skip WEBVTT header, timestamps, NOTE lines, empty lines
        if (not line or line.startswith("WEBVTT") or line.startswith("NOTE")
                or "-->" in line or re.match(r"^\d+$", line)):
            continue
        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean:
            texts.append(clean)
    return " ".join(texts)


def _fetch_transcript_api(video_id: str) -> str | None:
    """
    Fetch transcript using youtube-transcript-api (v1.x instance-based).
    May be blocked by YouTube on cloud IPs.
    """
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        transcript = None
        try:
            transcript = transcript_list.find_transcript(["en"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(
                    [t.language_code for t in transcript_list]
                )
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break

        if transcript is None:
            return None

        fetched = transcript.fetch()
        return " ".join(snippet.text for snippet in fetched)

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.warning(f"No transcript for {video_id}: {e}")
        return None
    except Exception as e:
        logger.debug(f"youtube-transcript-api failed for {video_id}: {e}")
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

    Strategy:
    1. Try yt-dlp subtitle download (robust, avoids IP blocks)
    2. Fall back to youtube-transcript-api

    Returns:
        dict with keys: title, url, video_id, transcript_text
        None if transcript is unavailable.
    """
    video_id = extract_video_id(url)
    if not video_id:
        logger.error(f"Could not extract video ID from URL: {url}")
        return None

    logger.info(f"Fetching transcript for video ID: {video_id}")

    # Strategy 1: yt-dlp (avoids YouTube IP blocks on cloud servers)
    transcript_text = _fetch_transcript_ytdlp(video_id)

    if transcript_text:
        logger.info(f"Got transcript via yt-dlp for {video_id}")
    else:
        # Strategy 2: youtube-transcript-api
        logger.info(f"yt-dlp subtitles unavailable, trying youtube-transcript-api...")
        transcript_text = _fetch_transcript_api(video_id)

    if not transcript_text:
        logger.warning(f"Could not fetch transcript for {video_id}")
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
