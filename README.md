# GTA6 Viral Shorts Studio

An automated full-stack AI video editing studio that converts any **GTA 6 YouTube Livestream** (live in progress via `--live-from-start` rolling buffer or recorded VOD) into **15-to-30-second viral Gen-Z vertical Shorts (9:16, 1080×1920 @ 60fps)** with After Effects / Premiere Pro-grade Remotion motion graphics, `librosa` beat-synced VFX, copyright-free BGM discovery, sidechain audio ducking, meme overlays, and an 8K HDR color-graded finish.

---

## Architecture & Tech Stack

| Layer | Technology |
| --- | --- |
| **Frontend & Motion Graphics** | Next.js 15 (App Router, TypeScript, Tailwind CSS) + **Remotion 4** (`@remotion/cli`, `@remotion/player`, `@remotion/renderer`, `@remotion/bundler`) |
| **Backend & Live Telemetry** | Python 3.11+ + **FastAPI** + WebSockets (`/ws/jobs/{job_id}`) |
| **Stream Ingestion** | `yt-dlp` (`--live-from-start` rolling buffer + max resolution `1080p60`/`4K` VOD) + OpenCV scene-change & Haar facecam corner detection |
| **AI Creative Director** | `faster-whisper` (word-level timestamps) + **Google Gemini API** (`google-genai` Interactions API using `gemini-4-hydrogen`*) |
| **Music & Beat Sync** | Pixabay Music API + `yt-dlp` NCS/CC fallback + local `assets/royalty_free_bgm/` + **`librosa`** beat & sub-bass drop extractor |
| **8K HDR & Audio Engine** | **FFmpeg** (`cas=strength=0.45`, `unsharp=5:5:0.8:5:5:0.0`, Vice City HDR `eq` + `colorbalance` + `vignette`, `minterpolate` optical-flow `0.45x` slow-mo, `sidechaincompress` audio ducking, H.264 High Profile `CRF 16`, `24 Mbps`, `60fps`, `yuv420p`) |

> \*Note: Deprecated `gemini-2.5-*` models have been upgraded to `gemini-4-hydrogen` via the official `google-genai` Interactions API (configurable via `GEMINI_MODEL`).

---

## Project Structure

```text
gta6-viral-shorts-studio/
├── frontend/                              # Next.js 15 + Remotion Studio
│   ├── src/
│   │   ├── app/page.tsx                   # URL Input, Quantity Selector, Live Progress & Preview UI
│   │   ├── components/
│   │   │   ├── StudioHeader.tsx
│   │   │   ├── UrlAndQuantityCard.tsx     # Step 1: URL + Quantity (1,3,5,10,Custom) + Presets
│   │   │   ├── PipelineTracker.tsx        # Step 2: 6-Stage Real-Time WebSocket Tracker
│   │   │   └── ShortsGalleryPreview.tsx   # Step 3: Interactive Remotion Player + MP4/ZIP Export
│   │   └── remotion/
│   │       ├── index.ts
│   │       ├── Root.tsx
│   │       ├── ViralShortComposition.tsx  # Master 1080x1920 @ 60fps 9:16 Composition
│   │       ├── render-cli.mjs             # Programmatic @remotion/renderer CLI
│   │       └── components/
│   │           ├── TopHookBanner.tsx      # ~240px white bar + bold tight-tracking black text
│   │           ├── BeatSyncCamera.tsx     # ±12px/±1.5deg Shake, 1.85x Flash & 1.12x Punch-Zoom
│   │           ├── GlowingCaptions.tsx    # Word-level spring() neon captions
│   │           ├── NarrativeNote.tsx      # Firefly-style *ACTION ANNOTATIONS*
│   │           └── MemeOverlayLayer.tsx   # WASTED, Vine Boom, 5-Star Siren & Freeze Frames
├── backend/                               # Python FastAPI Pipeline
│   ├── main.py                            # REST + WebSocket Server + ZIP Exporter
│   ├── models.py                          # Shared Pydantic Schemas
│   ├── pipeline/
│   │   ├── stream_ingestor.py             # yt-dlp Live/VOD Downloader + Peak & Facecam Detector
│   │   ├── viral_director.py              # Faster-Whisper + Google Gemini Multimodal Director
│   │   ├── music_fetcher.py               # Pixabay / NCS / Local Royalty-Free BGM Searcher
│   │   ├── beat_analyzer.py               # librosa Beat & Bass-Drop Extractor
│   │   ├── video_enhancer.py              # FFmpeg 8K CAS/HDR, Optical Slow-Mo & Sidechain Ducking
│   │   └── remotion_renderer.py           # Invokes Remotion Renderer (with FFmpeg fallback)
│   └── assets/
│       ├── memes/triggers.json            # Pre-wired GTA Meme trigger definitions
│       ├── sfx/                           # Pre-wired SFX (vine_boom, whoosh, bruh, wasted_hit)
│       └── royalty_free_bgm/              # Auto-populated & user-extensible BGM library
└── .env.example
```

---

## Prerequisites

- **Node.js** 20+ (`npm`)
- **Python** 3.11+
- **FFmpeg** (with `libx264`, `libmp3lame`, `cas`, `minterpolate`, `sidechaincompress` filters) available on `PATH`

---

## Quick Setup & Run

### 1. Configure Environment Variables

Copy `.env.example` to `backend/.env` and add your keys:

```bash
cp .env.example backend/.env
```

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-4-hydrogen
PIXABAY_API_KEY=
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=int8
LIVE_BUFFER_SECONDS=180
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_ORIGIN=http://localhost:3000
PUBLIC_BACKEND_URL=http://localhost:8000
ENABLE_REMOTION_RENDER=true
RENDER_CONCURRENCY=2
```

> **Out-of-the-box ready:** Even before setting `GEMINI_API_KEY` or `PIXABAY_API_KEY`, the backend automatically generates playable royalty-free SFX (`vine_boom.mp3`, `whoosh.mp3`, `bruh.mp3`, `wasted_hit.mp3`) and BGM tracks, and falls back cleanly to peak-energy viral detection so you can test immediately.

### 2. Start the FastAPI Backend (Port 8000)

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn main:app --reload --port 8000
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Start the Next.js 15 + Remotion Frontend (Port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser!

- Paste any **YouTube VOD or active Livestream URL** to unlock the quantity prompt (`1`, `3`, `5`, `10`, or custom) and editing style preset, OR click **"Instant GTA 6 Demo"** to watch the full 6-stage WebSocket pipeline, Remotion 9:16 60fps Player, and MP4/ZIP exporter in action immediately.
- To open the dedicated Remotion Studio timeline editor:
  ```bash
  cd frontend
  npm run remotion:studio
  ```
