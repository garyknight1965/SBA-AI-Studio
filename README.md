# SBA AI Studio

> AI-assisted Motorcycle Ride Reconstruction Engine for DaVinci Resolve Studio.

---

# Vision

SBA AI Studio is **not** a media importer.

It is an AI-assisted Ride Reconstruction Engine that understands the structure of a motorcycle trip - ride days, scenes, camera overlap - and prepares a DaVinci Resolve project that's ready to edit, instead of just a folder of imported clips.

The Planning Engine decides *what should happen*. The Resolve Builder executes it. The two are never mixed.

---

# Current Status

Version

0.7.0-alpha (update to match your latest `git tag` - see note below)

Current Milestone

Core Ride Reconstruction Pipeline - Complete

The full pipeline described in the project's architecture handover now exists end to end:

```
Scanner -> Source Media Validation -> Metadata -> Capture Time
        -> Media Library -> Timeline Sorter -> Ride Day Detection
        -> Scene Detection -> Multicam Detection -> Timeline Builder
        -> Resolve
```

---

# Features

Current

- Source Media Validation Engine (GoPro GX/GH, Insta360 `VID_` export, DJI Fly export accepted; images, sidecars, cache/proxy, cloud-trash markers rejected with an explained reason)
- Camera-aware timestamp resolution, including:
  - Insta360 filename-based capture time parsing
  - DJI Fly export naming support
  - GoPro multi-chapter timestamp correction (chapters 2+ no longer collide on chapter 1's timestamp)
  - Insta360 paired dual-view track separation
- Ride Day detection (gap-based)
- Scene Detection (finer-grained gap-based grouping within a day - boundaries only, not semantic labels)
- Multicam overlap window detection (real overlapping-camera windows, not naive single-clip grouping)
- Gap Compression, fully configurable via `config/settings.json` (off by default)
- Media Pool bins organized per Day > Camera
- Resolve Timeline Builder using real `TimelinePlacement` data, with three layers of write verification (count check, per-track append, actual-position verification against Resolve's own timeline state) - can be switched off entirely via `config/settings.json` (`enable_timeline_creation`) without touching any planning/placement code
- YouTube metadata generation (title/description/tags) from ride reconstruction data (ride days, scenes, duration, cameras, GPS-derived locations) via a local Ollama model - runs independently of Resolve (`generate_youtube_metadata.py`)
- Basic desktop GUI (PySide6): workspace tree, media browser, metadata panel, project statistics, and a local Day/Scene timeline preview - all Resolve-independent
- Resolve scripting module auto-located (env var / config / OS default paths), instead of depending on machine-wide setup outside this project
- Regression suite: 24+ tests, fully platform-independent (no hardcoded machine-specific paths)

Known gaps against the original architecture vision

- One Resolve timeline per Ride Day (currently one flat "Master" timeline per project)
- Real Resolve multicam *clip* creation (currently: overlap detection + separate tracks, no automatic multicam clip)
- Hero8 timestamp confidence scoring / sync-against-Hero13 (camera clock drift between GoPros is not yet corrected)
- Old `TimelineBuilderService` still present alongside the real `TimelinePlanningService` (tech debt, not yet retired)
- Scene *labelling* (e.g. "Fuel Stop", "Coffee Stop") - Scene Detection currently finds boundaries only; labelling needs a signal this project doesn't have yet (GPS route analysis, motion/audio analysis)

Known open issue

- One specific Insta360 paired-view track has, in one observed project, failed to place despite every diagnostic (count, position, per-track append, shared-object/path checks) reporting success. Parked pending a raw Resolve-console experiment isolating just those two files.

Planned (later, per the AI Roadmap)

- Thumbnail suggestions, SEO tags/chapters, story analysis, highlight detection
- Cloud AI as an optional alternative to local Ollama

---

# Project Structure

```
SBA-AI-Studio
│
├── start.py                        - GUI entry point
├── generate_youtube_metadata.py    - standalone YouTube metadata generator (no Resolve needed)
├── run_regression.py               - regression suite entry point
│
├── config
│   └── settings.json               - user-editable settings (Gap Compression, timeline creation toggle, Resolve module path, ExifTool path)
│
├── sba_resolve
│   ├── core                        - Planning Engine, models, metadata/timestamp resolution
│   ├── commands                    - Resolve Builder commands (create_timeline, sync_bins, etc.)
│   └── media_pool                  - Media Pool bin/import services
│
├── controllers                     - GUI <-> core glue (WorkspaceController)
├── ui                               - PySide6 desktop GUI (widgets, layout, windows)
├── regression                      - regression test framework and tests
├── tools                           - bundled ExifTool, dev utility scripts
└── docs
```

---

# Startup

Activate your virtual environment, then:

```powershell
python start.py
```

This launches the PySide6 desktop GUI. Scanning, validation, and Planning Engine steps run independently of Resolve; the Resolve connection (project creation, bin sync, media import, timeline creation) only happens when you trigger a Resolve import from the GUI, and only if `enable_timeline_creation` is `true` in `config/settings.json`.

For YouTube metadata generation only (no Resolve needed at all):

```powershell
python generate_youtube_metadata.py "D:\Movies\your-ride-folder"
```

Requires a local Ollama instance running (`ollama serve`) with a model pulled (`ollama pull llama3.2`).

---

# Architecture

```
start.py
      │
      ▼
Bootstrap
      │
      ▼
Workspace / WorkspaceController  ───────────────►  Planning Engine
      │                                             (Scanner, Validation, Metadata,
      ▼                                              Capture Time, Ride Day/Scene/
Resolve Connector (optional,                         Multicam Detection, Placement)
config-gated)                                              │
      │                                                    ▼
      ▼                                             PlanningResult
Resolve Context
      │
      ▼
Resolve Builder Commands
(create_timeline, sync_bins, ...)
```

The Planning Engine never calls the Resolve API. The Resolve Builder never contains business logic - it only executes what the Planning Engine decided.

---

# Development Workflow

Every change follows the same process, enforced by the regression suite:

```
Inspect existing code
      │
      ▼
Implement (complete files, not snippets)
      │
      ▼
Compile-check
      │
      ▼
Run full regression suite - must stay green
      │
      ▼
git commit (task-ID referenced in the message)
```

---

# Coding Standards

- One responsibility per file
- Complete file replacements only
- No snippets
- Type hints where appropriate
- PEP 8
- Regression tests required for new logic; mock external systems (Resolve API, network calls) rather than skip testing them
- Never perform major changes without a rollback point (commit + tag)

---

# Repository Status

Status

In active development - core Ride Reconstruction pipeline complete, structural Resolve-output work (per-day timelines, real multicam clips) still open.

Regression suite: run `python run_regression.py` before every commit.

---

# Author

Gary Knight

Scottish Biker Abroad

The Netherlands
