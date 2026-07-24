# SBA AI Studio

> AI-assisted Motorcycle Ride Reconstruction Engine for DaVinci Resolve Studio.

---

# Vision

SBA AI Studio is **not** a media importer.

It is an AI-assisted Ride Reconstruction Engine that understands the structure of a motorcycle trip - ride days, scenes, camera overlap - and prepares a DaVinci Resolve project that's ready to edit, instead of just a folder of imported clips.

The Planning Engine decides *what should happen*. The Resolve Builder executes it. The two are never mixed.

---

# Current Status

v2.4.0: Groq migration, ML-066 transcript extrapolation, ML-067 max_tokens/reasoning_effort fixes, dead-code cleanup

Current Milestone

Core Ride Reconstruction Pipeline - Complete, Publishing Metadata + Multi-Camera Sync in progress

The full pipeline described in the project's architecture handover exists end to end:

See `CHANGELOG.md` for detailed release history.

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
- Transcript -> IntelliScript AI Editor: local Ollama model decides keep/cut and paragraph grouping from a Resolve transcript export, verbatim wording always preserved
- IntelliScript-based chapter generation: real edited-video chapter timestamps (not raw-footage timing) with AI-generated topic labels and duration-based consolidation
- YouTube metadata generation (title/description/tags/chapters) from ride reconstruction data (ride days, scenes, duration, cameras, GPS-derived locations) via a local Ollama model - runs independently of Resolve
- Basic desktop GUI (PySide6): workspace tree, media browser, metadata panel, project statistics, and a local Day/Scene timeline preview - all Resolve-independent, with simplified combined Scan+Import and Transcript+IntelliScript File menu actions
- Resolve scripting module auto-located (env var / config / OS default paths), instead of depending on machine-wide setup outside this project
- One Resolve timeline PER RIDE DAY (e.g. "Test Project Day 1 - 2026-07-01"), instead of one flat "Master" timeline for the whole project - each day's clips, tracks, and markers are rebased to that day's own timeline independently
- A "<project> Master" timeline is then assembled automatically, nesting every day's timeline into it in order as a single combined review/export sequence
- Regression suite: 42+ tests, fully platform-independent (no hardcoded machine-specific paths)

In progress

- ML-054: Multi-camera timeline generation with audio-based sync (GoPro HERO13/HERO8 + Insta360 X3). Step 1 complete: Insta360 X3 filename-pattern detection (real X3 files carry no identifying embedded metadata after Insta360 Studio export, so filename pattern is now the primary detection signal). Audio cross-correlation sync (engine/road noise across frequency bands) tested against real multi-camera footage and found unreliable in practice (4/4 real test pairs weak, including a same-brand GoPro-to-GoPro control) - the feature now targets a "never guess" design where successfully-synced clips are auto-placed and unsynced clips get a named empty placeholder track with filename markers for manual sync in Resolve, with the placeholder path expected to be the common real-world outcome rather than an edge case.

Known gaps against the original architecture vision

- Real Resolve multicam *clip* creation (currently: overlap detection + separate tracks, no automatic multicam clip)
- Hero8 timestamp confidence scoring / sync-against-Hero13 (camera clock drift between GoPros is not yet corrected)
- Old `TimelineBuilderService` still present alongside the real `TimelinePlanningService` (tech debt, not yet retired)
- Scene *labelling* (e.g. "Fuel Stop", "Coffee Stop") - Scene Detection currently finds boundaries only; labelling needs a signal this project doesn't have yet (GPS route analysis, motion/audio analysis)

Known open issue

- One specific Insta360 paired-view track has, in one observed project, failed to place despite every diagnostic (count, position, per-track append, shared-object/path checks) reporting success. Parked pending a raw Resolve-console experiment isolating just those two files.

Planned (later, per the AI Roadmap)

- Thumbnail suggestions, SEO tags/chapters, story analysis, highlight detection
- Cloud AI as an optional alternative to local Ollama
- Single-executable packaging (PyInstaller, bundle ExifTool; Resolve/Ollama stay separate installs)
- ML-047: Auto-cut preview from IntelliScript decisions (reviewable list of proposed cuts/timecodes, preview-only before any Resolve API auto-cutting)

---

# Project Structure
---SBA-AI-Studio
|
+-- start.py                        - GUI entry point
+-- generate_youtube_metadata.py    - standalone YouTube metadata generator (no Resolve needed)
+-- run_regression.py               - regression suite entry point
|
+-- config
|   +-- settings.json               - user-editable settings (Gap Compression, timeline creation toggle, Resolve module path, ExifTool path)
|
+-- sba_resolve
|   +-- core                        - Planning Engine, models, metadata/timestamp resolution, services
|   +-- commands                    - Resolve Builder commands (create_timeline, sync_bins, etc.)
|   +-- media_pool                  - Media Pool bin/import services
|   +-- ui                          - background workers
|   +-- tools                       - feature-specific test/diagnostic scripts
|
+-- controllers                     - GUI <-> core glue (WorkspaceController)
+-- ui                              - PySide6 desktop GUI (widgets, layout, windows)
+-- regression                      - regression test framework and tests
+-- tools                           - bundled ExifTool, dev utility scripts, audio sync diagnostics
+-- docs                            - ADR handoff documents
+-- CHANGELOG.md                    - detailed release history

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
The Planning Engine never calls the Resolve API. The Resolve Builder never contains business logic - it only executes what the Planning Engine decided.

start.py
|
v
Bootstrap
|
v
Workspace / WorkspaceController  -------------->  Planning Engine
|                                            (Scanner, Validation, Metadata,
v                                             Capture Time, Ride Day/Scene/
Resolve Connector (optional,                        Multicam Detection, Placement)
config-gated)                                             |
|                                                   v
v                                            PlanningResult
Resolve Context
|
v
Resolve Builder Commands
(create_timeline, sync_bins, ...)

---

# Development Workflow

Every change follows the same process, enforced by the regression suite:
SBA-AI-Studio
Inspect existing code
|
v
Implement (complete files, not snippets)
|
v
Compile-check
|
v
Run full regression suite - must stay green
|
v
git commit (task-ID referenced in the message)
|
+-- start.py                        - GUI entry point
+-- generate_youtube_metadata.py    - standalone YouTube metadata generator (no Resolve needed)
+-- run_regression.py               - regression suite entry point
|
+-- config
|   +-- settings.json               - user-editable settings (Gap Compression, timeline creation toggle, Resolve module path, ExifTool path)
|
+-- sba_resolve
|   +-- core                        - Planning Engine, models, metadata/timestamp resolution, services
|   +-- commands                    - Resolve Builder commands (create_timeline, sync_bins, etc.)
|   +-- media_pool                  - Media Pool bin/import services
|   +-- ui                          - background workers
|   +-- tools                       - feature-specific test/diagnostic scripts
|
+-- controllers                     - GUI <-> core glue (WorkspaceController)
+-- ui                              - PySide6 desktop GUI (widgets, layout, windows)
+-- regression                      - regression test framework and tests
+-- tools                           - bundled ExifTool, dev utility scripts, audio sync diagnostics
+-- docs                            - ADR handoff documents
+-- CHANGELOG.md                    - detailed release history

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

In active development - core Ride Reconstruction pipeline complete, structural Resolve-output work (per-day timelines, real multicam clips) still open, multi-camera audio-sync (ML-054) in progress.

Regression suite: run `python run_regression.py` before every commit
(`--core` / `--ui` / `--resolve` / `--all` modes available; GUI-dependent
tests report as BLOCKED rather than FAILED if the environment is missing
a native GUI dependency such as `libGL.so.1`).

---

# Author

Gary Knight

Scottish Biker Abroad

The Netherlands
