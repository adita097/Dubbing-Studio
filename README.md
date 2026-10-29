# DubStudio — AI Video Translation and Dubbing MVP

DubStudio is a full-stack, subtitle-driven video translation and dubbing web application. It takes an existing video alongside its subtitles (or plain transcript / embedded subtitle stream), translates the text into a target language, generates synchronized AI speech, and composes a dubbed MP4 video.

---

## Features
- **Video Ingestion**: Upload MP4, MOV, or WebM video with validation and metadata extraction.
- **Subtitle Input Options**:
  - Upload SRT or WebVTT files (preserves millisecond timing and segments).
  - Paste plain-text transcript (segmentation for untimed sequential narration).
  - Extract embedded subtitle streams directly from uploaded video files via FFprobe / FFmpeg.
- **AI Translation**:
  - Segment-by-segment translation preserving segment IDs, timing, numbers, names, and tone.
  - Pluggable provider architecture (OpenAI or deterministic Mock Mode).
- **Interactive Subtitle Editor**:
  - Side-by-side comparison of original and translated text.
  - Full inline editing with instant updates before audio synthesis.
- **AI Voice Generation**:
  - Target-language voice options and tone selection.
  - Timed segment placement with overflow prevention and sequential narration fallback.
  - In-browser audio preview player.
- **Video Composition & Export**:
  - **Mode A (Replace)**: Completely replaces original audio with translated speech.
  - **Mode B (Mix/Duck)**: Retains original audio at a reduced background volume under the voiceover.
  - Subprocess-safe FFmpeg composition with stream verification before download.
- **Zero-Cost Mock Mode**:
  - 100% offline development and testing support without requiring paid API keys.

---

## Tech Stack
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide React icons.
- **Backend**: Python 3.12, FastAPI, Pydantic v2, FFmpeg / FFprobe.
- **AI Providers**: Configurable adapters (OpenAI LLM & TTS, Mock Provider).
- **Storage**: Local filesystem-based project and asset storage.

---

## Project Structure
```text
DubStudio/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # REST API endpoints (health, projects, subtitles, etc.)
│   │   ├── core/            # Configuration & settings
│   │   ├── jobs/            # Background job management
│   │   ├── providers/       # Translation & Speech provider adapters (OpenAI, Mock)
│   │   ├── schemas/         # Pydantic models for projects, subtitles, jobs
│   │   ├── services/        # Parsers, media processor, exporter, translation
│   │   ├── storage/         # Local file storage manager
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Comprehensive pytest suite
│   ├── storage/             # Generated media assets (uploads, voiceover, output)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/                 # React components, state, API clients, styles
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```
