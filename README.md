# 🎬 YouTube Notes Automator

Automatically generate rich, detailed study notes from YouTube videos — complete with Mermaid diagrams, LaTeX equations, tables, AI-generated images, and auto-pushed to GitHub.

## ✨ What It Does

```
YouTube URLs
     │
     ▼
📥 Fetch Transcripts       (youtube-transcript-api + yt-dlp)
     │
     ▼
🧠 Generate Detailed Notes  (Claude API — structured markdown)
     │
     ▼
🎨 Generate Images          (Gemini — topic-relevant visuals)
     │
     ▼
📝 Write notes.md           (single file, images embedded)
     │
     ▼
🚀 Push to GitHub           (gh CLI — auto-creates repo)
```

**Notes include:**
- 📋 Table of Contents with anchor links
- 🗂️ Structured H1/H2/H3 headings
- 💡 Key Insight callouts
- ⚠️ Common Mistake warnings
- 📊 Mermaid diagrams (where genuinely helpful)
- 🔢 LaTeX math equations (step-by-step)
- 📋 Comparison tables
- 🖼️ AI-generated topic images
- 📚 Summary + Key Takeaways at the end

---

## 🛠️ Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.10+ | Runtime | [python.org](https://python.org) |
| `gh` CLI | GitHub push | [cli.github.com](https://cli.github.com) |
| `git` | Version control | [git-scm.com](https://git-scm.com) |
| `yt-dlp` | Video metadata | `pip install yt-dlp` |

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/your-username/youtube-notes-automator
cd youtube-notes-automator
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

- Get Anthropic key: [console.anthropic.com](https://console.anthropic.com)
- Get Gemini key: [aistudio.google.com](https://aistudio.google.com)

### 3. Authenticate GitHub CLI

```bash
gh auth login
```

---

## 🚀 Usage

### Single video
```bash
python main.py --urls "https://youtu.be/dQw4w9WgXcQ"
```

### Multiple videos (combined into one notes doc)
```bash
python main.py --urls "https://youtu.be/abc" "https://youtube.com/watch?v=xyz"
```

### Entire playlist
```bash
python main.py --urls "https://www.youtube.com/playlist?list=PLxxxxxx"
```

### Entire YouTube channel (last 10 videos by default)
```bash
python main.py --urls "https://www.youtube.com/@3blue1brown"
```

### Channel with custom video limit
```bash
python main.py --urls "https://www.youtube.com/@3blue1brown" --limit 25
```

### Mix of videos, playlists, and channels
```bash
python main.py --urls \
  "https://youtu.be/abc" \
  "https://www.youtube.com/playlist?list=PLxxxxxx" \
  "https://www.youtube.com/@SomeChannel"
```

### From a URLs file (can contain videos, playlists, channels)
Add URLs to `urls.txt` (one per line) then:
```bash
python main.py --urls-file urls.txt
```

### Custom repo name
```bash
python main.py --urls "https://youtu.be/abc" --repo my-ml-notes
```

### Skip GitHub push (local only)
```bash
python main.py --urls "https://youtu.be/abc" --no-push
```

### Skip image generation
```bash
python main.py --urls "https://youtu.be/abc" --no-images
```

### All options
```
Options:
  --urls URL [URL ...]     One or more URLs (videos, playlists, channels)
  --urls-file FILE         Text file with URLs (one per line)
  --output FILE            Output filename (default: notes.md)
  --repo NAME              GitHub repo name (default: youtube-notes)
  --limit N                Max videos from each playlist/channel (default: 10)
  --no-push                Skip GitHub push
  --no-images              Skip Gemini image generation
  --images-dir DIR         Images output directory (default: images)
```

---

## 📁 Output Structure

```
youtube-notes-automator/
├── notes.md          ← Your rich notes document
└── images/
    ├── 20240315-1-neural-networks.png
    ├── 20240315-2-backpropagation.png
    └── ...
```

---

## 🔧 Troubleshooting

**`TranscriptsDisabled` error**
- The video has transcripts disabled by the creator
- Try a different video or add captions manually

**`ANTHROPIC_API_KEY not set`**
- Check your `.env` file exists and has the correct key
- Run `echo $ANTHROPIC_API_KEY` to verify it's loaded

**`gh: command not found`**
- Install GitHub CLI: [cli.github.com](https://cli.github.com)
- Or use `--no-push` and push manually

**Image generation fails**
- Check `GEMINI_API_KEY` is valid
- Gemini image generation may have quota limits on free tier
- Use `--no-images` to skip and still get text notes

**`yt-dlp` title fetch fails**
- This is non-fatal — the video ID is used as the title instead
- Make sure `yt-dlp` is installed: `pip install yt-dlp`

---

## 🤖 How Notes Are Generated

Claude is prompted with strict rules to:
1. **Never hallucinate** — only explain what's in the transcript
2. **Use Mermaid diagrams only when genuinely helpful** (not decorative)
3. **Show all math step-by-step** with proper LaTeX
4. **Add image placeholder tags** that Gemini then fills in
5. **Ground explanations** in real-world analogies

---

## 📄 License

MIT
