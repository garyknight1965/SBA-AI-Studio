# Changelog

All notable changes to SBA AI Studio are documented here.
## 2026-07-23

### Fixed
- `pyproject.toml` package version aligned to `2.1.0` (previously `0.1.0`,
  out of sync with README/Architecture.md).
- `requirements.txt` converted from UTF-16LE (with a BOM and NUL bytes,
  likely from Windows tooling) to plain UTF-8 - same package list, just
  a clean encoding.
- `docs/changelog.md` was empty; now redirects readers to the real,
  detailed history in the root `CHANGELOG.md`.
- Retired the stale `docs/Master_Development_Roadmap.md` (an early
  ChatGPT-era planning doc, tagged v0.4.0-alpha / Sprint ML-011) to
  `docs/ADR/historical-master-development-roadmap-v1.md`, clearly
  labelled as historical.
- Refreshed `docs/Roadmap.md` end to end: each milestone now reflects
  actually-verified current status instead of stale claims, the
  one-timeline-per-ride-day gap is called out as the top open item, and
  a "Current Near-Term Priorities" section tracks the active punch list.

## 2026-07-22

### Added
- Regression suite modes: `python run_regression.py --core / --ui / --resolve / --all`.
  `--core` runs everything that needs neither a real headless GUI
  nor a real Resolve connection; `--ui` runs only the real-PySide6-widget
  tests; `--resolve` is reserved for future Resolve-integration tests
  (none require it yet, since all Resolve API access in this suite is
  mocked). No flag = `--all`, matching prior behaviour.
- GUI dependency preflight (`regression/gui_preflight.py`): before running
  any test that constructs a real (offscreen) PySide6 widget, the runner
  tries to construct a `QApplication` once. If a native dependency such as
  `libGL.so.1` is missing, the affected tests are reported as **BLOCKED**
  (environment limitation) instead of **FAILED**, with the underlying
  reason printed once. Blocked tests do not affect the suite's exit code.
- `RegressionResult` gained a `blocked` field/state, and
  `BaseRegressionTest` gained `requires_gui` / `requires_resolve` flags
  used for mode filtering and preflight gating. The 5 tests that
  construct real PySide6 widgets (Locations UI, UI Widget Wiring,
  Transcript UI, YouTube Metadata UI, Resolve Import Corruption Skip)
  are now marked `requires_gui = True`.

## 2026-07-21

### Added
- **Groq AI provider** as an alternative to Ollama — cloud-based, no local hardware needed, noticeably faster. Configurable in Settings → AI Provider.
- **Editable IntelliScript prompt guidance** — the editorial instructions the AI uses for keep/cut decisions are now user-editable in Settings → IntelliScript Prompt, with a Reset to Default option.
- **Real road-following map routing** via OpenRouteService — replaces the straight pin-to-pin line with an actual road route when an API key is configured in Settings → Map. Falls back to the original straight-line behavior if no key is set or the route can't be fetched.
- Console output from Resolve import is now visible in the GUI via a "Show Details..." expander on the Import to Resolve dialog, instead of console-only.

### Fixed
- Ollama request timeout raised from 120s to 300s to accommodate longer transcript prompts.
- Media Browser columns no longer get squeezed unreadably when the dock is narrow — the Filename column now absorbs available space instead of the shorter columns.
- Settings dialog is now scrollable, so it no longer grows taller than the screen as more sections are added.
## [Unreleased]

### Added
- ML-054 Step 1: Insta360 X3 filename-pattern detection in
  CameraRecognitionEngine - real-world X3 files exported via
  Insta360 Studio carry no identifying Make/Model/handler
  metadata, so filename pattern (VID_YYYYMMDD_HHMMSS_NN_NNN,
  optional trailing 6-digit suffix) is now the primary detection
  signal for these files, checked ahead of the existing
  folder-path ("/360/") rule. Full regression coverage added
  (regression/tests/test_camera_recognition_engine.py).

## v2.1.0 (current baseline - retroactively documented 2026-07-19)

### Added
- ML-053: File menu UI simplification - "Scan & Import to
  Resolve" and "Load Transcript & Generate IntelliScript..."
  combined into single actions; "Save IntelliScript Script..."
  stays a separate, explicit action (no silent auto-save).
- ML-052: IntelliScriptChapterGenerator - real edited-video
  chapter timestamps computed from IntelliScript's own keep/cut
  decisions (cut segments contribute zero elapsed time), with an
  AI-generated short topic label per chapter and duration-based
  chapter consolidation (default minimum 60s per chapter).
  Supersedes ML-051's raw-footage-timing chapters.
- ML-051: YouTube metadata chapters section wired to chapter
  data whenever Planning/chapter data exists for a project
  (superseded by ML-052).

### Fixed
- ML-028 regression test fakes updated to accept the new
  chapter_days parameter introduced by ML-051.

## v0.5.0

### Added
- Transcript -> IntelliScript AI Editor: load a DaVinci Resolve
  transcript export, let a local Ollama model decide what to cut
  (dead air, filler, rambling asides) and how to group
  paragraphs, then get back a script ready for IntelliScript -
  every kept word stays verbatim, since the AI only ever returns
  keep/cut decisions, never rewritten text.
- Structural corruption detection: the Corruption Detector now
  walks the actual MP4/MOV box structure and catches the real
  failure signature a camera freeze or power loss leaves behind -
  a valid header and plausible file size, but no moov index at
  all. Corrupted files are now skipped automatically before
  Resolve import instead of failing there with no explanation.

### Fixed
- ML-031 timestamp/multicam confidence wiring
  (resolve_with_source, MulticamConfidenceScorer)
- RideSummaryBuilder.build_scenes() for per-scene
  duration/camera/multicam/HERO13-audio facts
- Project Database persistence for missing/new/corrupted file
  tracking across scans

---

Entries before v0.5.0 are not individually documented here yet.
The regression suite (`python run_regression.py`) and
`docs/ADR/` handoff documents are the best source for earlier
task history until this file is backfilled further.