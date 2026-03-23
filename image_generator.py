# image_generator.py — Generate topic images using Gemini and embed in markdown

import os
import re
import time
import logging
from datetime import datetime
from pathlib import Path

try:
    from slugify import slugify
except ImportError:
    def slugify(text):
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

from google import genai
from google.genai import types
from config import GEMINI_IMAGE_MODEL, MAX_IMAGES

logger = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(
    r'<!--\s*IMAGE:\s*"([^"]+)"\s*TOPIC:\s*"([^"]+)"\s*-->'
)


def generate_image(prompt: str, filepath: str, api_key: str) -> bool:
    """
    Generate a single image using Gemini and save to filepath.

    Returns True on success, False on failure.
    """
    client = genai.Client(api_key=api_key)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(part.inline_data.data)
                    logger.info(f"Saved image: {filepath}")
                    return True
            logger.warning(f"No image in response for prompt: {prompt[:60]}")
            return False
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 2 ** attempt * 10
                logger.warning(f"Rate limited on image gen. Waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Image generation error (attempt {attempt+1}): {e}")
                if attempt == 2:
                    return False
                time.sleep(2)

    return False


def generate_images(markdown_content: str, output_dir: str, api_key: str) -> str:
    """
    Find IMAGE_PLACEHOLDER comments in markdown, generate images, replace with img tags.

    Args:
        markdown_content: The full notes markdown string
        output_dir: Directory to save images (e.g. "images")
        api_key: Gemini API key

    Returns:
        Updated markdown with images embedded
    """
    placeholders = PLACEHOLDER_RE.findall(markdown_content)

    if not placeholders:
        logger.info("No image placeholders found in notes.")
        return markdown_content

    placeholders = placeholders[:MAX_IMAGES]
    logger.info(f"Found {len(placeholders)} image placeholders to generate")

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    counter = {"n": 0}

    def replace_placeholder(match):
        description = match.group(1)
        topic = match.group(2)
        idx = counter["n"]
        counter["n"] += 1

        if idx >= MAX_IMAGES:
            return f"> 🖼️ *Image: {topic}*"

        slug = slugify(topic)[:40]
        filename = f"{timestamp}-{idx+1:02d}-{slug}.png"
        filepath = os.path.join(output_dir, filename)

        print(f"  🎨 Generating image {idx+1}: {topic[:50]}...")
        success = generate_image(description, filepath, api_key)

        if success:
            rel_path = f"{output_dir}/{filename}".replace("\\", "/")
            return f"![{topic}]({rel_path})\n*{topic}*"
        else:
            return f"> 🖼️ *Image placeholder: {topic}* (generation failed)"

    updated = PLACEHOLDER_RE.sub(replace_placeholder, markdown_content)
    return updated
