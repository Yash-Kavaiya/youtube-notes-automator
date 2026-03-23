# YouTube Notes Automator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that takes YouTube URLs, fetches transcripts, generates detailed structured notes via Claude API, generates images via Gemini API, outputs a notes.md file, and pushes to GitHub.

**Architecture:** Pipeline-style CLI where each module handles one stage (fetch → generate notes → generate images → write markdown → push to GitHub). Modules communicate via plain Python dicts so they're independently testable and replaceable.

**Tech Stack:** Python 3.10+, youtube-transcript-api, yt-dlp, anthropic SDK, google-generativeai, argparse, gh CLI (subprocess)

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.py` | Constants, env var loading, model names |
| `fetcher.py` | Extract video_id from URL, fetch transcript text, get title via yt-dlp |
| `notes_generator.py` | Build Claude prompt from transcript dicts, call API, return markdown string |
| `image_generator.py` | Call Gemini image gen API for a topic string, save PNG, return file path |
| `github_pusher.py` | Create/verify GitHub repo via `gh` CLI, commit files, push |
| `main.py` | argparse CLI, orchestrate all modules, print progress |
| `requirements.txt` | All Python dependencies |
| `.env.example` | Template with required env var names |
| `README.md` | Setup and usage instructions |
| `tests/test_fetcher.py` | Unit tests for URL parsing and transcript fetch |
| `tests/test_notes_generator.py` | Unit tests for prompt building and API call |
| `tests/test_image_generator.py` | Unit tests for Gemini image call |
| `tests/test_github_pusher.py` | Unit tests for gh CLI calls |
| `tests/test_main.py` | Integration test for full pipeline |

---

## Task 1: Project Setup — requirements.txt, .env.example, config.py

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
youtube-transcript-api==0.6.2
yt-dlp>=2024.1.1
anthropic>=0.25.0
google-genai>=0.5.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

- [ ] **Step 3: Create config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"

CLAUDE_SYSTEM_PROMPT = """You are an expert note-taker and educator. Your job is to create comprehensive, detailed study notes from YouTube video transcripts.

Rules:
1. Be DETAILED and THOROUGH - explain every concept as if to someone learning for the first time
2. Use easy-to-understand language with real-world analogies
3. Structure with clear H1, H2, H3 headers
4. Use bullet points for lists, numbered lists for steps
5. Add Mermaid diagrams (```mermaid) ONLY when they genuinely help visualize flows, architectures, or relationships - not for everything
6. Add GitHub-flavored markdown LaTeX ($$...$$ for block, $...$  for inline) for ALL math equations, showing step-by-step derivations
7. Add markdown tables when comparing things or showing structured data
8. Add > blockquotes to highlight KEY INSIGHTS, warnings, or must-remember facts
9. At the end of each video's section add a ## Key Takeaways bullet list
10. If multiple videos are provided, add a ## Cross-Video Synthesis section at the very end connecting themes

Output ONLY valid GitHub-flavored markdown. No preamble, no explanation."""

DEFAULT_OUTPUT_FILE = "notes.md"
DEFAULT_REPO_NAME = "youtube-notes"
DEFAULT_URLS_FILE = "urls.txt"
IMAGES_DIR = "images"
```

- [ ] **Step 4: Create tests/__init__.py** (empty file)

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example config.py tests/__init__.py
git commit -m "feat: add project config, deps, and env template"
```

---

## Task 2: fetcher.py — Transcript + Metadata Fetching

**Files:**
- Create: `fetcher.py`
- Create: `tests/test_fetcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_fetcher.py
import pytest
from unittest.mock import patch, MagicMock
from fetcher import extract_video_id, fetch_transcript


class TestExtractVideoId:
    def test_standard_watch_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_youtu_be_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id("https://www.google.com")


class TestFetchTranscript:
    @patch("fetcher.subprocess.run")
    @patch("fetcher.YouTubeTranscriptApi.get_transcript")
    def test_returns_expected_dict(self, mock_transcript, mock_subprocess):
        mock_transcript.return_value = [
            {"text": "Hello world", "start": 0.0, "duration": 2.0},
            {"text": "How are you", "start": 2.0, "duration": 2.0},
        ]
        mock_subprocess.return_value = MagicMock(
            stdout='{"title": "Test Video Title"}', returncode=0
        )

        result = fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result["title"] == "Test Video Title"
        assert "Hello world" in result["transcript_text"]
        assert "How are you" in result["transcript_text"]

    @patch("fetcher.subprocess.run")
    @patch("fetcher.YouTubeTranscriptApi.get_transcript")
    def test_transcript_unavailable_returns_none(self, mock_transcript, mock_subprocess):
        from youtube_transcript_api._errors import TranscriptsDisabled
        mock_transcript.side_effect = TranscriptsDisabled("dQw4w9WgXcQ")
        mock_subprocess.return_value = MagicMock(
            stdout='{"title": "Test Video"}', returncode=0
        )

        result = fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_fetcher.py -v
```
Expected: ImportError or ModuleNotFoundError since `fetcher.py` doesn't exist yet.

- [ ] **Step 3: Implement fetcher.py**

```python
# fetcher.py
import re
import json
import subprocess
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

# Patterns ordered from most specific to least specific
_VIDEO_ID_PATTERNS = [
    r"youtu\.be/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    for pattern in _VIDEO_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def _get_title(url: str) -> str:
    """Use yt-dlp to fetch the video title."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("title", "Unknown Title")
    except Exception as e:
        logger.warning(f"Could not fetch title for {url}: {e}")
    return "Unknown Title"


def fetch_transcript(url: str) -> dict | None:
    """
    Fetch transcript and metadata for a YouTube video.

    Returns dict with keys: video_id, url, title, transcript_text
    Returns None if transcript is unavailable.
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        logger.error(str(e))
        return None

    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(seg["text"] for seg in segments)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.warning(f"Transcript not available for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching transcript for {url}: {e}")
        return None

    title = _get_title(url)

    return {
        "video_id": video_id,
        "url": url,
        "title": title,
        "transcript_text": transcript_text,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_fetcher.py -v
```
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: add transcript fetcher with URL parsing and yt-dlp title lookup"
```

---

## Task 3: notes_generator.py — Claude API Notes Generation

**Files:**
- Create: `notes_generator.py`
- Create: `tests/test_notes_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_notes_generator.py
import pytest
from unittest.mock import patch, MagicMock
from notes_generator import build_prompt, generate_notes


SAMPLE_TRANSCRIPTS = [
    {
        "video_id": "abc123",
        "url": "https://www.youtube.com/watch?v=abc123",
        "title": "Introduction to Python",
        "transcript_text": "Python is a programming language. It is easy to learn.",
    },
    {
        "video_id": "def456",
        "url": "https://www.youtube.com/watch?v=def456",
        "title": "Python Functions",
        "transcript_text": "Functions are reusable blocks of code. def keyword defines them.",
    },
]


class TestBuildPrompt:
    def test_contains_all_titles(self):
        prompt = build_prompt(SAMPLE_TRANSCRIPTS)
        assert "Introduction to Python" in prompt
        assert "Python Functions" in prompt

    def test_contains_all_transcripts(self):
        prompt = build_prompt(SAMPLE_TRANSCRIPTS)
        assert "Python is a programming language" in prompt
        assert "Functions are reusable blocks of code" in prompt

    def test_contains_video_urls(self):
        prompt = build_prompt(SAMPLE_TRANSCRIPTS)
        assert "https://www.youtube.com/watch?v=abc123" in prompt

    def test_single_video_prompt(self):
        prompt = build_prompt([SAMPLE_TRANSCRIPTS[0]])
        assert "Introduction to Python" in prompt
        assert len(prompt) > 50


class TestGenerateNotes:
    @patch("notes_generator.anthropic.Anthropic")
    def test_returns_markdown_string(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="# Notes\n\nSome content here")]
        )

        result = generate_notes(SAMPLE_TRANSCRIPTS)

        assert isinstance(result, str)
        assert "# Notes" in result
        mock_client.messages.create.assert_called_once()

    @patch("notes_generator.anthropic.Anthropic")
    def test_passes_system_prompt(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="# Notes")]
        )

        generate_notes(SAMPLE_TRANSCRIPTS)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_notes_generator.py -v
```
Expected: ImportError since `notes_generator.py` doesn't exist.

- [ ] **Step 3: Implement notes_generator.py**

```python
# notes_generator.py
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_SYSTEM_PROMPT


def build_prompt(transcripts: list[dict]) -> str:
    """Build a single comprehensive prompt for all videos."""
    sections = []
    for i, t in enumerate(transcripts, 1):
        sections.append(
            f"## Video {i}: {t['title']}\n"
            f"URL: {t['url']}\n\n"
            f"TRANSCRIPT:\n{t['transcript_text']}"
        )

    videos_block = "\n\n---\n\n".join(sections)

    return (
        f"I have {len(transcripts)} YouTube video transcript(s) for you to turn into "
        f"comprehensive study notes.\n\n"
        f"{videos_block}\n\n"
        f"Please generate detailed, well-structured notes covering ALL videos above. "
        f"Follow all rules from your system prompt exactly."
    )


def generate_notes(transcripts: list[dict]) -> str:
    """
    Generate comprehensive markdown notes for all transcripts.

    Args:
        transcripts: List of dicts from fetcher.fetch_transcript()

    Returns:
        Markdown string with complete notes.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = build_prompt(transcripts)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8096,
        system=CLAUDE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_notes_generator.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add notes_generator.py tests/test_notes_generator.py
git commit -m "feat: add Claude-powered notes generator with structured prompt"
```

---

## Task 4: image_generator.py — Gemini Image Generation

**Files:**
- Create: `image_generator.py`
- Create: `tests/test_image_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_image_generator.py
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from image_generator import generate_image_for_topic, generate_images_for_notes


class TestGenerateImageForTopic:
    @patch("image_generator.genai.Client")
    def test_returns_file_path(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Simulate image bytes response
        fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data.data = fake_image_bytes
        mock_part.inline_data.mime_type = "image/png"
        mock_response.parts = [mock_part]
        mock_client.models.generate_content.return_value = mock_response

        output_dir = str(tmp_path)
        result = generate_image_for_topic("Python programming concepts", output_dir, "image_0")

        assert result is not None
        assert result.endswith(".png")
        assert os.path.exists(result)

    @patch("image_generator.genai.Client")
    def test_returns_none_on_error(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        result = generate_image_for_topic("test topic", str(tmp_path), "image_0")
        assert result is None


class TestGenerateImagesForNotes:
    @patch("image_generator.generate_image_for_topic")
    def test_returns_dict_of_paths(self, mock_gen, tmp_path):
        mock_gen.return_value = str(tmp_path / "image_0.png")

        topics = ["Python basics", "Functions in Python"]
        result = generate_images_for_notes(topics, str(tmp_path))

        assert isinstance(result, dict)
        assert len(result) == 2
        assert mock_gen.call_count == 2

    @patch("image_generator.generate_image_for_topic")
    def test_skips_failed_images(self, mock_gen, tmp_path):
        mock_gen.side_effect = [str(tmp_path / "image_0.png"), None]

        topics = ["topic 1", "topic 2"]
        result = generate_images_for_notes(topics, str(tmp_path))

        # Only the successful one is in result
        assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_generator.py -v
```
Expected: ImportError since `image_generator.py` doesn't exist.

- [ ] **Step 3: Implement image_generator.py**

```python
# image_generator.py
import os
import logging
from pathlib import Path
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL, IMAGES_DIR

logger = logging.getLogger(__name__)


def generate_image_for_topic(topic: str, output_dir: str, filename_stem: str) -> str | None:
    """
    Generate a single image for a topic using Gemini.

    Args:
        topic: Text description of what to illustrate
        output_dir: Directory to save the image
        filename_stem: Base filename without extension

    Returns:
        Absolute path to saved PNG, or None on failure.
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=f"Create a clear, educational diagram or illustration for: {topic}. "
                     f"Style: clean, minimal, technical, suitable for study notes.",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            ),
        )

        for part in response.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith("image/"):
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                output_path = os.path.join(output_dir, f"{filename_stem}.png")
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                logger.info(f"Saved image: {output_path}")
                return output_path

        logger.warning(f"No image in Gemini response for topic: {topic}")
        return None

    except Exception as e:
        logger.error(f"Failed to generate image for '{topic}': {e}")
        return None


def generate_images_for_notes(topics: list[str], output_dir: str) -> dict[str, str]:
    """
    Generate images for a list of topics.

    Args:
        topics: List of topic strings to illustrate
        output_dir: Directory to save images

    Returns:
        Dict mapping topic -> file_path for successful generations.
    """
    results = {}
    for i, topic in enumerate(topics):
        path = generate_image_for_topic(topic, output_dir, f"image_{i:02d}")
        if path:
            results[topic] = path
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_generator.py -v
```
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add image_generator.py tests/test_image_generator.py
git commit -m "feat: add Gemini image generator for topic illustrations"
```

---

## Task 5: github_pusher.py — GitHub Repo Creation and Push

**Files:**
- Create: `github_pusher.py`
- Create: `tests/test_github_pusher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_github_pusher.py
import pytest
from unittest.mock import patch, MagicMock, call
from github_pusher import repo_exists, create_repo, push_to_github


class TestRepoExists:
    @patch("github_pusher.subprocess.run")
    def test_returns_true_when_repo_exists(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert repo_exists("my-repo") is True

    @patch("github_pusher.subprocess.run")
    def test_returns_false_when_repo_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert repo_exists("nonexistent-repo") is False


class TestCreateRepo:
    @patch("github_pusher.subprocess.run")
    def test_calls_gh_repo_create(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        create_repo("my-repo", private=True)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "repo" in call_args
        assert "create" in call_args
        assert "my-repo" in call_args

    @patch("github_pusher.subprocess.run")
    def test_raises_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        with pytest.raises(RuntimeError, match="Failed to create repo"):
            create_repo("my-repo")


class TestPushToGithub:
    @patch("github_pusher.repo_exists")
    @patch("github_pusher.create_repo")
    @patch("github_pusher.subprocess.run")
    def test_creates_repo_if_not_exists(self, mock_run, mock_create, mock_exists):
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)

        push_to_github("my-repo", ["notes.md"], "/tmp/workdir")

        mock_create.assert_called_once_with("my-repo", private=False)

    @patch("github_pusher.repo_exists")
    @patch("github_pusher.create_repo")
    @patch("github_pusher.subprocess.run")
    def test_skips_create_if_repo_exists(self, mock_run, mock_create, mock_exists):
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        push_to_github("my-repo", ["notes.md"], "/tmp/workdir")

        mock_create.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_github_pusher.py -v
```
Expected: ImportError since `github_pusher.py` doesn't exist.

- [ ] **Step 3: Implement github_pusher.py**

```python
# github_pusher.py
import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def repo_exists(repo_name: str) -> bool:
    """Check if a GitHub repo exists for the authenticated user."""
    result = subprocess.run(
        ["gh", "repo", "view", repo_name],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_repo(repo_name: str, private: bool = False) -> None:
    """Create a new GitHub repository."""
    args = ["gh", "repo", "create", repo_name, "--source=.", "--push"]
    if private:
        args.append("--private")
    else:
        args.append("--public")

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create repo '{repo_name}': {result.stderr}")
    logger.info(f"Created GitHub repo: {repo_name}")


def push_to_github(repo_name: str, files: list[str], workdir: str, private: bool = False) -> str:
    """
    Commit files and push to GitHub repo.

    Args:
        repo_name: GitHub repo name (owner/name or just name)
        files: List of file paths to add and commit
        workdir: Working directory for git operations
        private: Whether to create as private repo

    Returns:
        URL of the GitHub repo.
    """
    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
        return result

    # Ensure git is initialized
    if not os.path.exists(os.path.join(workdir, ".git")):
        run(["git", "init"])
        run(["git", "branch", "-M", "main"])

    # Stage files
    for f in files:
        run(["git", "add", f])

    # Commit
    run(["git", "commit", "-m", "feat: add youtube notes"])

    if not repo_exists(repo_name):
        create_repo(repo_name, private=private)
    else:
        # Repo exists — set remote and push
        result = subprocess.run(
            ["gh", "repo", "view", repo_name, "--json", "url", "-q", ".url"],
            capture_output=True, text=True,
        )
        remote_url = result.stdout.strip()
        run(["git", "remote", "add", "origin", remote_url])
        run(["git", "push", "-u", "origin", "main"])

    # Get repo URL
    result = subprocess.run(
        ["gh", "repo", "view", repo_name, "--json", "url", "-q", ".url"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_github_pusher.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add github_pusher.py tests/test_github_pusher.py
git commit -m "feat: add GitHub pusher using gh CLI"
```

---

## Task 6: main.py — CLI Orchestration

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_main.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os


class TestMainCLI:
    @patch("main.push_to_github")
    @patch("main.generate_images_for_notes")
    @patch("main.generate_notes")
    @patch("main.fetch_transcript")
    def test_full_pipeline_with_url(
        self, mock_fetch, mock_notes, mock_images, mock_push, tmp_path, capsys
    ):
        mock_fetch.return_value = {
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
            "title": "Test Video",
            "transcript_text": "This is a test transcript.",
        }
        mock_notes.return_value = "# Test Notes\n\nSome content."
        mock_images.return_value = {}
        mock_push.return_value = "https://github.com/user/youtube-notes"

        output_file = str(tmp_path / "notes.md")

        from main import run
        run(
            urls=["https://www.youtube.com/watch?v=abc123"],
            output=output_file,
            repo="youtube-notes",
            no_push=True,
            no_images=True,
            images_dir=str(tmp_path / "images"),
        )

        assert os.path.exists(output_file)
        content = Path(output_file).read_text()
        assert "# Test Notes" in content

    @patch("main.fetch_transcript")
    def test_skips_failed_transcripts(self, mock_fetch, tmp_path):
        mock_fetch.return_value = None  # Transcript unavailable

        from main import run
        with pytest.raises(SystemExit) as exc_info:
            run(
                urls=["https://www.youtube.com/watch?v=abc123"],
                output=str(tmp_path / "notes.md"),
                repo="youtube-notes",
                no_push=True,
                no_images=True,
                images_dir=str(tmp_path / "images"),
            )
        assert exc_info.value.code == 1


class TestParseUrlsFile:
    def test_reads_urls_from_file(self, tmp_path):
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "https://www.youtube.com/watch?v=abc123\n"
            "# This is a comment\n"
            "https://youtu.be/def456\n"
            "\n"
        )

        from main import parse_urls_file
        urls = parse_urls_file(str(urls_file))
        assert len(urls) == 2
        assert "https://www.youtube.com/watch?v=abc123" in urls
        assert "https://youtu.be/def456" in urls
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py -v
```
Expected: ImportError since `main.py` doesn't exist.

- [ ] **Step 3: Implement main.py**

```python
# main.py
import argparse
import os
import sys
import logging
from pathlib import Path

from fetcher import fetch_transcript
from notes_generator import generate_notes
from image_generator import generate_images_for_notes
from github_pusher import push_to_github
from config import DEFAULT_OUTPUT_FILE, DEFAULT_REPO_NAME, DEFAULT_URLS_FILE, IMAGES_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_urls_file(path: str) -> list[str]:
    """Read URLs from a text file, skipping comments and blank lines."""
    urls = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def run(
    urls: list[str],
    output: str,
    repo: str,
    no_push: bool,
    no_images: bool,
    images_dir: str,
) -> None:
    """Core pipeline: fetch → notes → images → write → push."""

    # 1. Fetch transcripts
    print(f"🎬 Fetching transcripts for {len(urls)} video(s)...")
    transcripts = []
    for url in urls:
        print(f"   Fetching: {url}")
        result = fetch_transcript(url)
        if result:
            transcripts.append(result)
            print(f"   ✅ {result['title']}")
        else:
            print(f"   ⚠️  Skipped (transcript unavailable): {url}")

    if not transcripts:
        print("❌ No transcripts available. Exiting.")
        sys.exit(1)

    # 2. Generate notes
    print(f"\n🧠 Generating notes for {len(transcripts)} video(s) via Claude...")
    notes_markdown = generate_notes(transcripts)
    print("   ✅ Notes generated.")

    # 3. Generate images
    image_map = {}
    if not no_images:
        topics = [t["title"] for t in transcripts]
        print(f"\n🎨 Generating {len(topics)} image(s) via Gemini...")
        image_map = generate_images_for_notes(topics, images_dir)
        print(f"   ✅ {len(image_map)} image(s) saved to {images_dir}/")

    # 4. Write notes.md
    print(f"\n📝 Writing {output}...")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepend image references if we have images
    image_section = ""
    if image_map:
        image_section = "\n## Generated Illustrations\n\n"
        for topic, path in image_map.items():
            rel_path = os.path.relpath(path, start=str(output_path.parent))
            image_section += f"### {topic}\n\n![{topic}]({rel_path})\n\n"
        image_section += "---\n\n"

    output_path.write_text(image_section + notes_markdown, encoding="utf-8")
    print(f"   ✅ Saved: {output}")

    # 5. Push to GitHub
    if not no_push:
        files_to_push = [output]
        if image_map:
            files_to_push.extend(image_map.values())

        print(f"\n🚀 Pushing to GitHub repo '{repo}'...")
        repo_url = push_to_github(repo, files_to_push, workdir=str(output_path.parent))
        print(f"   ✅ Published: {repo_url}")
    else:
        print("\n⏭️  Skipping GitHub push (--no-push).")

    print("\n✨ Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Generate rich study notes from YouTube videos using Claude + Gemini."
    )

    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument(
        "--urls", nargs="+", metavar="URL", help="One or more YouTube URLs"
    )
    url_group.add_argument(
        "--urls-file",
        metavar="PATH",
        help=f"Path to a text file with one URL per line (default: {DEFAULT_URLS_FILE})",
    )

    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_FILE, help=f"Output markdown file (default: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO_NAME, help=f"GitHub repo name (default: {DEFAULT_REPO_NAME})"
    )
    parser.add_argument(
        "--no-push", action="store_true", help="Skip pushing to GitHub"
    )
    parser.add_argument(
        "--no-images", action="store_true", help="Skip Gemini image generation"
    )
    parser.add_argument(
        "--images-dir", default=IMAGES_DIR, help=f"Directory to save images (default: {IMAGES_DIR})"
    )

    args = parser.parse_args()

    if args.urls_file:
        if not os.path.exists(args.urls_file):
            print(f"❌ URLs file not found: {args.urls_file}")
            sys.exit(1)
        urls = parse_urls_file(args.urls_file)
    else:
        urls = args.urls

    if not urls:
        print("❌ No URLs provided.")
        sys.exit(1)

    run(
        urls=urls,
        output=args.output,
        repo=args.repo,
        no_push=args.no_push,
        no_images=args.no_images,
        images_dir=args.images_dir,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py -v
```
Expected: All 3 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add CLI orchestrator with full pipeline"
```

---

## Task 7: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# YouTube Notes Automator

Generate rich, detailed study notes from YouTube videos using **Claude** (Anthropic) for notes and **Gemini** for illustrations — all in one command.

## Features

- Accepts YouTube URLs via CLI args or a `urls.txt` file
- Fetches full video transcripts automatically
- Generates detailed, structured markdown notes via Claude (with Mermaid diagrams, LaTeX math, tables)
- Generates topic illustrations via Gemini's image generation model
- Pushes the output to a GitHub repo automatically via `gh` CLI

## Prerequisites

- Python 3.10+
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed and on PATH
- [`gh` CLI](https://cli.github.com/) installed and authenticated (`gh auth login`)
- Anthropic API key
- Google Gemini API key

## Setup

1. Clone this repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

## Usage

### From CLI URLs

```bash
python main.py --urls https://youtu.be/VIDEO_ID1 https://youtu.be/VIDEO_ID2
```

### From a urls.txt file

Create a `urls.txt` file (one URL per line, `#` for comments):

```
# Python tutorials
https://www.youtube.com/watch?v=VIDEO_ID1
https://youtu.be/VIDEO_ID2
```

Then run:

```bash
python main.py --urls-file urls.txt
```

### All Options

```
--urls URL [URL ...]       One or more YouTube URLs
--urls-file PATH           Path to URLs file (default: urls.txt)
--output FILE              Output markdown file (default: notes.md)
--repo NAME                GitHub repo name (default: youtube-notes)
--no-push                  Skip GitHub push
--no-images                Skip Gemini image generation
--images-dir DIR           Directory for images (default: images)
```

### Example

```bash
python main.py \
  --urls https://youtu.be/dQw4w9WgXcQ \
  --output my-notes.md \
  --repo my-youtube-notes \
  --no-images
```

## Output

A `notes.md` file containing:

- H1/H2/H3 structured sections per video
- Mermaid diagrams for architectures/flows
- LaTeX math equations with step-by-step derivations
- Comparison tables
- Key insight blockquotes
- Key Takeaways per video
- Cross-Video Synthesis section (for multiple videos)
- Embedded images (unless `--no-images`)

## Running Tests

```bash
pytest tests/ -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add setup and usage README"
```

---

## Task 8: Final Validation

- [ ] **Step 1: Run full test suite one final time**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests PASS, 0 failures.

- [ ] **Step 2: Verify file structure matches spec**

```bash
ls -la
```
Expected files: `main.py`, `fetcher.py`, `notes_generator.py`, `image_generator.py`, `github_pusher.py`, `config.py`, `requirements.txt`, `.env.example`, `README.md`, `tests/`

- [ ] **Step 3: Smoke test help output**

```bash
python main.py --help
```
Expected: argparse help with all documented flags shown.

- [ ] **Step 4: Final commit (if any last changes)**

```bash
git add -A
git status  # verify only expected files
git commit -m "chore: final cleanup and validation"
```
