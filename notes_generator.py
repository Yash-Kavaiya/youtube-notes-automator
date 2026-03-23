# notes_generator.py — Generate structured notes using Claude API

import time
import logging
import anthropic
from config import CLAUDE_MODEL, CLAUDE_FALLBACK_MODEL, MAX_TOKENS, NOTES_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def build_user_prompt(transcripts: list[dict]) -> str:
    """Build the user prompt combining all transcripts."""
    parts = []
    for i, t in enumerate(transcripts, 1):
        parts.append(
            f"## VIDEO {i}: {t['title']}\n"
            f"URL: {t['url']}\n\n"
            f"TRANSCRIPT:\n{t['transcript_text']}\n"
        )
    combined = "\n\n---\n\n".join(parts)

    if len(transcripts) == 1:
        intro = "Create comprehensive, detailed notes from the following YouTube video transcript."
    else:
        intro = (
            f"Create comprehensive, detailed notes from the following {len(transcripts)} "
            "YouTube video transcripts. Combine them into ONE cohesive notes document, "
            "grouping related topics together under clear sections."
        )

    return f"{intro}\n\n{combined}"


def generate_notes(transcripts: list[dict], api_key: str) -> str:
    """
    Generate structured markdown notes from a list of transcript dicts.

    Args:
        transcripts: List of dicts with keys: title, url, video_id, transcript_text
        api_key: Anthropic API key

    Returns:
        Markdown string with notes content
    """
    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_user_prompt(transcripts)

    for attempt in range(3):
        model = CLAUDE_MODEL if attempt < 2 else CLAUDE_FALLBACK_MODEL
        try:
            logger.info(f"Generating notes with {model} (attempt {attempt + 1})")
            response = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=NOTES_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** attempt * 5
            logger.warning(f"Rate limited. Waiting {wait}s before retry...")
            time.sleep(wait)
        except anthropic.APIError as e:
            logger.error(f"API error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                raise
            time.sleep(2 ** attempt * 2)

    raise RuntimeError("Failed to generate notes after 3 attempts")
