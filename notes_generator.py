# notes_generator.py — Generate structured notes using Claude via Anthropic or AWS Bedrock

import os
import time
import logging
import anthropic
from config import CLAUDE_MODEL, CLAUDE_FALLBACK_MODEL, MAX_TOKENS, NOTES_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Bedrock model IDs
BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-6-v1:0"
BEDROCK_FALLBACK = "us.anthropic.claude-haiku-3-5-v1:0"


def get_client():
    """
    Return the appropriate Anthropic client.
    Priority:
    1. ANTHROPIC_API_KEY (direct Anthropic API)
    2. AWS_BEARER_TOKEN_BEDROCK (pre-signed Bedrock URL via bearer token)
    3. AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (standard Bedrock)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        logger.info("Using direct Anthropic API")
        return anthropic.Anthropic(api_key=api_key), False

    bearer_url = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    if bearer_url:
        logger.info("Using AWS Bedrock via bearer token")
        # Extract bearer token from pre-signed URL for use with AnthropicBedrock
        # The bearer URL itself is the token passed via aws_session_token workaround
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        return anthropic.AnthropicBedrock(
            aws_access_key="dummy",
            aws_secret_key="dummy",
            aws_session_token=bearer_url,
            aws_region=aws_region,
        ), True

    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    if aws_key and aws_secret:
        logger.info("Using AWS Bedrock for Claude")
        return anthropic.AnthropicBedrock(
            aws_access_key=aws_key,
            aws_secret_key=aws_secret,
            aws_region=aws_region,
        ), True

    raise RuntimeError(
        "No Claude credentials found. Set one of:\n"
        "  - ANTHROPIC_API_KEY (direct Anthropic), or\n"
        "  - AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (Bedrock)"
    )


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


def generate_notes(transcripts: list[dict], api_key: str = None) -> str:
    """
    Generate structured markdown notes from a list of transcript dicts.

    Args:
        transcripts: List of dicts with keys: title, url, video_id, transcript_text
        api_key: Anthropic API key (optional if using Bedrock via env vars)

    Returns:
        Markdown string with notes content
    """
    client, is_bedrock = get_client()
    prompt = build_user_prompt(transcripts)

    models = (
        [BEDROCK_MODEL, BEDROCK_FALLBACK] if is_bedrock
        else [CLAUDE_MODEL, CLAUDE_FALLBACK_MODEL]
    )

    for attempt in range(3):
        model = models[min(attempt, len(models) - 1)]
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
