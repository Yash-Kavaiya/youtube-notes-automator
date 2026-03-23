# config.py — Model and system configuration

CLAUDE_MODEL = "claude-opus-4-5"
CLAUDE_FALLBACK_MODEL = "claude-sonnet-4-5"
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"  # or "imagen-3.0-generate-002"
MAX_TOKENS = 8000
MAX_IMAGES = 8
OUTPUT_DIR = "images"
DEFAULT_OUTPUT_FILE = "notes.md"
DEFAULT_REPO_NAME = "youtube-notes"

MAX_PLAYLIST_VIDEOS = 50   # Max videos to pull from a playlist/channel
DEFAULT_PLAYLIST_LIMIT = 10  # Default limit when user doesn't specify --limit

NOTES_SYSTEM_PROMPT = """You are an expert note-taker and educator. Your job is to create comprehensive, detailed study notes from YouTube video transcripts.

Rules:
1. Be DETAILED and THOROUGH - explain every concept as if to someone learning for the first time
2. Use easy-to-understand language with real-world analogies
3. Structure with clear H1, H2, H3 headers
4. Use bullet points for lists, numbered lists for steps
5. Add Mermaid diagrams (```mermaid) ONLY when they genuinely help visualize flows, architectures, or relationships - not for everything
6. Add GitHub-flavored markdown LaTeX ($$...$$ for block, $...$ for inline) for ALL math equations, showing step-by-step derivations
7. Add markdown tables when comparing things or showing structured data
8. Add "> 💡 Key Insight: ..." blockquotes for important takeaways
9. Add "> ⚠️ Common Mistake: ..." blockquotes for pitfalls
10. At the top: add a "## 📋 Table of Contents" with anchor links
11. At the bottom: add "## 📚 Summary" and "## 🔑 Key Takeaways" sections
12. Add IMAGE_PLACEHOLDER tags like: <!-- IMAGE: "a vivid visual description for image generation" TOPIC: "topic name" -->
    Place these at relevant sections (2-4 per video, total max 8). These will be replaced with actual generated images.
13. Ground everything in the actual content - do not hallucinate facts not in the transcript
14. Start the document with a "# 📺 [Title]" H1 heading
"""
