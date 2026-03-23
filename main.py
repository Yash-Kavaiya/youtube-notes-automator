#!/usr/bin/env python3
# main.py — YouTube Notes Automator entry point

import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding for UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load .env before importing modules that need API keys
load_dotenv()

from fetcher import fetch_transcript, load_urls_from_file, resolve_urls
from notes_generator import generate_notes
from image_generator import generate_images
from github_pusher import push_to_github
from config import DEFAULT_OUTPUT_FILE, DEFAULT_REPO_NAME, OUTPUT_DIR, DEFAULT_PLAYLIST_LIMIT

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="YouTube Notes Automator — fetch transcripts, generate rich notes, push to GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --urls "https://youtu.be/abc123"
  python main.py --urls "https://youtube.com/watch?v=abc" "https://youtu.be/xyz"
  python main.py --urls "https://www.youtube.com/playlist?list=PLxxxxxx"
  python main.py --urls "https://www.youtube.com/@SomeChannel" --limit 5
  python main.py --urls-file my_videos.txt --repo my-study-notes
  python main.py --urls "https://youtu.be/abc" --no-push --no-images
        """
    )
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument(
        "--urls", nargs="+", metavar="URL",
        help="One or more YouTube URLs (videos, playlists, or channels)"
    )
    url_group.add_argument(
        "--urls-file", metavar="FILE", default=None,
        help="Text file with one YouTube URL per line (default: urls.txt)"
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_FILE,
        help=f"Output notes filename (default: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO_NAME,
        help=f"GitHub repo name to push to (default: {DEFAULT_REPO_NAME})"
    )
    parser.add_argument(
        "--no-push", action="store_true",
        help="Skip GitHub push"
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Skip image generation"
    )
    parser.add_argument(
        "--images-dir", default=OUTPUT_DIR,
        help=f"Directory to save generated images (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_PLAYLIST_LIMIT,
        help=f"Max videos to pull from a playlist/channel (default: {DEFAULT_PLAYLIST_LIMIT})"
    )
    return parser.parse_args()


def check_env(no_images: bool) -> tuple:
    """Validate required environment variables."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    gemini_key = os.getenv("GEMINI_API_KEY") if not no_images else None

    if not anthropic_key and not aws_key:
        print("ERROR: No Claude credentials found.")
        print("  Set ANTHROPIC_API_KEY or AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY")
        sys.exit(1)

    if aws_key:
        print("  [Bedrock] Using AWS Bedrock for Claude")
    else:
        print("  [API] Using Anthropic API directly")

    if not no_images and not gemini_key:
        print("WARNING: GEMINI_API_KEY is not set. Images will be skipped.")
        gemini_key = None

    return anthropic_key, gemini_key


def main():
    args = parse_args()
    anthropic_key, gemini_key = check_env(args.no_images)

    # ── Step 1: Collect URLs ──────────────────────────────────────────────────
    if args.urls:
        raw_urls = args.urls
    else:
        urls_file = args.urls_file or "urls.txt"
        raw_urls = load_urls_from_file(urls_file)
        if not raw_urls:
            print(f"ERROR: No URLs found in {urls_file}")
            sys.exit(1)

    print(f"\n[*] Resolving {len(raw_urls)} input URL(s)...")
    urls = resolve_urls(raw_urls, limit=args.limit)

    if not urls:
        print("ERROR: No video URLs could be resolved. Exiting.")
        sys.exit(1)

    print(f"\n[+] Processing {len(urls)} video(s)...\n")

    # ── Step 2: Fetch transcripts ─────────────────────────────────────────────
    transcripts = []
    for url in urls:
        print(f"  >> Fetching: {url}")
        data = fetch_transcript(url)
        if data:
            word_count = len(data["transcript_text"].split())
            print(f"     OK: \"{data['title']}\" ({word_count:,} words)")
            transcripts.append(data)
        else:
            print(f"     SKIP: Could not fetch transcript")

    if not transcripts:
        print("\nERROR: No transcripts could be fetched. Exiting.")
        sys.exit(1)

    # ── Step 3: Generate notes ────────────────────────────────────────────────
    print(f"\n[*] Generating notes with Claude ({len(transcripts)} transcript(s))...")
    try:
        notes_markdown = generate_notes(transcripts, api_key=anthropic_key)
        print(f"  OK: Notes generated ({len(notes_markdown):,} characters)")
    except Exception as e:
        print(f"ERROR: Notes generation failed: {e}")
        sys.exit(1)

    # ── Step 4: Generate images ───────────────────────────────────────────────
    if not args.no_images and gemini_key:
        print(f"\n[*] Generating images with Gemini...")
        notes_markdown = generate_images(notes_markdown, args.images_dir, gemini_key)
        print(f"  OK: Images embedded")
    else:
        reason = "--no-images" if args.no_images else "no GEMINI_API_KEY"
        print(f"\n[~] Image generation skipped ({reason})")

    # ── Step 5: Write notes.md ────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(notes_markdown, encoding="utf-8")
    print(f"\n[+] Notes written to: {output_path.resolve()}")

    # ── Step 6: Push to GitHub ────────────────────────────────────────────────
    if not args.no_push:
        print(f"\n[*] Pushing to GitHub repo: {args.repo}...")
        try:
            local_dir = str(Path(".").resolve())
            repo_url = push_to_github(local_dir, args.repo, args.output)
            print(f"  OK: Pushed! View at: {repo_url}")
        except Exception as e:
            print(f"  WARNING: GitHub push failed: {e}")
            print(f"  TIP: Run manually: gh repo create {args.repo} --public --source=. --push")
    else:
        print("\n[~] GitHub push skipped (--no-push)")

    print(f"\n[DONE] Notes saved to {args.output}\n")


if __name__ == "__main__":
    main()
