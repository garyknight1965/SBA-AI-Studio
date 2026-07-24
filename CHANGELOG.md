# Changelog

All notable changes to SBA AI Studio are documented here.
## 2026-07-23 (ML-064: thumbnail text style - Barlow Condensed ExtraBold + drop shadow)

### Changed
- Thumbnail overlay text now uses **Barlow Condensed ExtraBold** (bundled
  with the app under `assets/fonts/`, SIL Open Font License - see
  `assets/fonts/OFL.txt`) instead of a generic system bold font, with a
  **soft drop shadow** instead of the previous black stroke outline -
  a common, punchy real YouTube-thumbnail look, per Gary's request.
- The font is bundled the same way ExifTool already is: extracted fresh
  to `sys._MEIPASS` on every launch of the packaged `.exe`
  (`sba_ai_studio.spec` updated to include `assets/fonts/`), so it
  works identically whether running from source or the packaged app -
  no need for the font to be installed system-wide.
- Regression coverage added: the bundled font file exists and is a
  valid, loadable font; rendered text shows both pure white pixels and
  a blended gradient of shadow tones (proving a real soft shadow, not
  a hard-edged stroke).

## 2026-07-23 (ML-063: thumbnail overlay text auto-fit)

### Fixed
- Thumbnail overlay text ran off the right edge of the frame for
  longer suggested text (Gary hit this with "Motorcycle Touring
  Netherlands", which got cut off past the frame boundary in a real
  saved thumbnail) - the original code drew text at a fixed font size
  with no width check at all. Now: `ThumbnailComposer` shrinks the
  font size to fit the available width, and if the text still doesn't
  fit even at a reasonable minimum size, wraps it across up to 3 lines
  instead (truncating with an ellipsis only in the extreme case of a
  single word too long to fit at all).
- Regression coverage added specifically for this: long text stays
  within the frame's right edge (checked directly against real pixel
  data, not just "some text got drawn somewhere"), and extremely long
  text wraps across multiple lines rather than overflowing.

## 2026-07-23 (GUI-013: YouTube Metadata + Thumbnail tabbed together)

### Changed
- The YouTube Metadata and Thumbnail panels are now tabbed together in
  one dock slot, instead of splitting the bottom dock area into ever-
  narrower slivers alongside Transcript - same treatment already applied
  to Metadata/Statistics/Locations on the right side (GUI-011). Each
  panel now gets the full bottom-area height when its tab is active.
  Transcript stays a separate dock.

## 2026-07-23 (ML-062: Thumbnail panel scrollability fix)

### Fixed
- The Thumbnail panel (`thumbnail_widget.py`) ran off the bottom of the
  screen instead of scrolling, once 5 candidate frame previews plus the
  480-wide composited preview image were all shown at once - the same
  problem the Settings dialog and YouTube Metadata panel already hit and
  were fixed for. Fixed the same way: everything except the Suggest
  Frames button/status label now lives inside a `QScrollArea`.

## 2026-07-23 (ML-061 follow-up: Windows file-handle fix)

### Fixed
- `ThumbnailComposer._paste_logo()` opened the logo file via
  `Image.open(logo_path).convert("RGBA")` without ever explicitly
  closing the underlying file handle. Pillow lazy-loads image files, so
  the handle can stay open after use - Linux doesn't care when deleting
  such a file, but Windows refuses (`[WinError 32] The process cannot
  access the file because it is being used by another process`), which
  is exactly what Gary hit when his test's `TemporaryDirectory` tried
  to clean up. Fixed by opening the logo inside a `with Image.open(...)
  as logo_file:` block and using `.convert("RGBA")`'s independent copy
  afterward, so the file handle is always explicitly closed.
- The regression test itself had the same pattern (`Image.open(
  output_path)` without closing, while checking the saved file's size)
  - fixed the same way.

## 2026-07-23 (ML-061: thumbnail generation from real footage)

### Added
- New **Thumbnail** panel: pulls a handful of candidate still frames
  from this project's own footage (evenly spread across the clips,
  deterministic selection - not an AI guess at which frame "looks
  best", since that's a judgement call best left to a human), lets
  Gary click one to preview, composites it live with overlay text and
  the channel logo, and saves the result as a 1280x720 PNG ready for
  YouTube.
- Overlay text is pre-filled from YouTubeMetadataGenerator's own
  `thumbnail_text` suggestion (ML-059) when available, but stays fully
  editable - typing updates the live preview instantly.
- New Settings section: "Thumbnail", with a logo image path (file
  picker, filtered to image files) composited into the bottom-right
  corner of every generated thumbnail, sized so an oversized logo file
  can never swamp the frame underneath it.
- New backend service `thumbnail_generator.py`
  (`ThumbnailFrameExtractor` + `ThumbnailComposer`) - frame extraction
  reads directly from source media files via cv2 (already a project
  dependency), so this works without any Resolve connection. Text/logo
  compositing uses Pillow (newly added dependency) for proper
  anti-aliased TrueType text rendering, cover-fit resizing to exact
  YouTube dimensions regardless of source aspect ratio, and safe
  handling of a missing/invalid logo path (image comes back unchanged,
  never raises).
- New `ThumbnailSuggestionWorker` runs frame extraction on a background
  thread (video decoding can take a moment), same pattern as every
  other AI/network-touching worker in this project.
- Regression coverage: `test_thumbnail_generator.py` (frame spacing/
  duration filtering/failed-read handling, cover-fit cropping for both
  PIL and raw numpy/cv2 BGR input, text/logo compositing, graceful
  missing-logo handling, save-to-disk, settings loader) and
  `test_thumbnail_ui.py` (candidate selection/preview logic, text
  pre-fill-only-if-empty behaviour, DockManager wiring).

## 2026-07-23 (ML-057 follow-up 3: one-day projects skip the Master timeline)

### Changed
- `create_timeline()` now only assembles a "<project> Master" timeline
  when there are 2+ ride days. A one-day project used to still get a
  redundant Master timeline nesting its only day's timeline - Gary
  pointed out that's an unnecessary second timeline to manage (and cut
  gaps out of twice) when there's nothing actually being combined. The
  day's own timeline is now returned directly in that case.
- New regression test: `Single Day Skips Master Timeline (ML-057)` in
  `test_ride_day_timelines.py` - confirms exactly one timeline is
  created for a one-day project, it's not named as a Master, and it's
  both the return value and the project's final current timeline.

## 2026-07-23 (ML-060: YouTube Metadata panel scrollability fix)

### Fixed
- The YouTube Metadata panel (`youtube_metadata_widget.py`) grew taller
  than its dock area once every ML-059 field was added, causing it to
  overflow/overlap into whatever panel sits below it instead of
  scrolling - Gary spotted this in a screenshot showing another panel's
  status text bleeding through the bottom of the YouTube Metadata dock.
  Fixed the same way the Settings dialog was fixed for the same problem
  (GUI-010 backlog item 5): everything except the notes field / Generate
  button / status label now lives inside a `QScrollArea`, so the form
  scrolls internally instead of overflowing into neighbouring docks.

## 2026-07-23 (ML-059: rich SEO-expert YouTube metadata output)

### Added
- Generated YouTube metadata is now much richer, per Gary's own
  SEO-expert prompt template:
  - **5 title options** instead of 1 (each under 70 characters).
    `"title"` is still returned as a single string - the first/best
    pick - so existing code keeps working; the full list is in the
    new `"titles"` field.
  - **Description structure** explicitly guided: hook opening, clear
    explanation of the video, natural use of every place name (not
    just a list), the editing credit worked in naturally, a
    Like/Comment/Share/Subscribe call to action, and 10-15 hashtags
    at the end.
  - **15 SEO tags** instead of a handful.
  - **Suggested filename** for the exported video (filesystem-safe).
  - **Pinned comment** suggestion to boost engagement.
  - **Thumbnail text** suggestion (3-6 words).
- `youtube_metadata_widget.py`: new fields for the above - "Other
  title options", "Suggested filename", "Pinned comment", "Thumbnail
  text" - all correctly cleared on `parse_error` and by `clear()`, same
  as the existing fields.
- `generate_youtube_metadata.py` (the standalone, no-Resolve-needed
  CLI script) now prints all of the above too.
- Regression coverage extended in both
  `test_youtube_metadata_generator.py` (parsing every new field,
  correct fallback behaviour on parse_error) and
  `test_youtube_metadata_ui.py` (widget fields populate and clear
  correctly).

## 2026-07-23 (ML-058 v2: natural, editable editing credit - replaces the fixed line)

### Changed
- Reverted the deterministically-appended `EDITOR_CREDIT` fixed line
  from the previous entry - Gary wanted the SBA AI Studio/DaVinci
  Resolve mention woven naturally into the AI's own writing instead of
  a bolted-on sentence, and wanted the ability to tune the brand-voice
  guidance himself.
- The YouTube metadata prompt's brand-voice/style guidance (channel
  tone, title/description style - previously the hardcoded
  `BRAND_VOICE_GUIDANCE` constant) is now user-editable via
  `app_settings.load_youtube_metadata_guidance()` /
  `DEFAULT_YOUTUBE_METADATA_GUIDANCE`, the same pattern already used
  for IntelliScript's editable prompt guidance. New Settings dialog
  section: "YouTube Metadata Prompt", with a multi-line text box and a
  Reset to Default button.
- The default guidance now instructs the model to (a) make full,
  natural use of every place name given, weaving them into the story
  rather than just listing them, and (b) naturally mention somewhere
  in the flow that the video was edited with the help of SBA AI Studio
  and DaVinci Resolve - phrased however fits the surrounding tone,
  not as an isolated final sentence.
- Regression coverage updated: the default guidance's instructions
  reach the prompt sent to the model; a settings.json-configured
  override actually reaches the prompt (proving the editable-guidance
  wiring works end to end); and the credit is confirmed to come from
  the model's own response rather than being appended in code.

## 2026-07-23 (ML-058: editor credit in YouTube descriptions)

### Added
- Every generated YouTube description now includes a short, fixed
  credit line - "Edited with the help of my own custom-built app, SBA
  AI Studio, alongside DaVinci Resolve." - per Gary's request. This is
  appended deterministically in code (`EDITOR_CREDIT` in
  `youtube_metadata_generator.py`), the same reliable way the chapters
  section is appended - not left to the model's discretion, so it's
  guaranteed to appear with consistent wording every time, including
  when the model's own JSON response fails to parse. Appears before
  any chapters section. Tune the wording directly in that constant if
  Gary wants to adjust it later.
- Regression coverage added: credit line present in the normal case,
  present in the parse_error/raw_response fallback, and correctly
  ordered before the chapters section when both are present.

## 2026-07-23 (ML-057 follow-up 2: timelines were landing in the wrong bin)

### Fixed
- Every timeline `create_timeline()` builds (each ride day's, and the
  assembled Master) now points the Media Pool's current folder at the
  ROOT bin before calling `CreateEmptyTimeline()`. Previously, new
  timelines landed wherever the current folder happened to be left by
  the earlier bin-sync step - in practice, buried deep inside a random
  Day/Camera media bin (e.g. "Day 4/DJI Flip") instead of the clean,
  predictable top-level bin (Resolve's root bin is named "Master" by
  default) - exactly what Gary found in a real project.
- `test_ride_day_timelines.py` extended to prove this: every timeline
  created in that test must be preceded by a `SetCurrentFolder()` call
  targeting the root folder, not whatever bin was previously active.

## 2026-07-23 (ML-057 follow-up: Master timeline assembly)

### Added
- `create_timeline()` now also assembles a "<project> Master" timeline
  after building every ride day's own timeline - each day's timeline is
  nested into it, in ride-day order, as a single combined review/export
  sequence. Every Resolve Timeline also exists as a Media Pool item once
  created, so nesting reuses the ordinary `AppendToTimeline` mechanism -
  no special "nest a timeline" API call is needed. No `recordFrame` is
  supplied for these appends; Resolve places each one at the end of the
  track's existing content in call order, so no frame math is guessed
  for the Master's assembly (in keeping with the project's "never
  guess" philosophy).
- `create_timeline()` now returns the assembled Master timeline (rather
  than the last day timeline built), since that's the sequence intended
  for final review/export.
- Regression coverage extended: `test_ride_day_timelines.py` now also
  verifies the Master timeline is created, correctly named, and nests
  both day timelines in the right order.

## 2026-07-23 (ML-057: One Resolve timeline per ride day)

### Added
- `create_timeline()` now builds one independent Resolve timeline PER
  RIDE DAY (e.g. "Test Project Day 1 - 2026-07-01"), instead of one flat
  "Master" timeline for the whole project. Each day's clips, tracks, and
  markers are rebased to that day's own timeline independently - Day 2's
  clips no longer carry Day 1's multi-day project-wide frame offset onto
  their own timeline.
- New `sba_resolve/core/services/ride_day_grouper.py`
  (`RideDayGrouper`/`RideDayTimelinePlan`): splits the Planning Engine's
  project-wide `PlanningResult` into one rebased plan per ride day.
  `PlanningResult` itself is unchanged and stays project-wide (still
  correct for multicam detection and statistics) - the per-day split is
  business logic that lives here, at the Resolve Builder boundary, per
  the architecture rule that Resolve command code never contains
  business rules.
- `TimelineMarker` and `UnsyncedClip` both gained a `ride_day` field so
  markers and unsynced-clip reports can be grouped onto the correct
  day's timeline.
- `create_timeline()` now reads the project's configured timeline frame
  rate once via `Project.GetSetting("timelineFrameRate")`, rather than
  from a specific timeline - necessary since no timeline exists yet
  before the very first one is built.
- Two new regression tests: `test_ride_day_grouper.py` (rebasing math)
  and `test_ride_day_timelines.py` (full end-to-end proof against the
  fake Resolve API - 2 real timelines, correctly named, correctly
  rebased, no marker/clip cross-contamination between days).
- `ui/windows/main_window.py`'s `timeline_name` no longer appends
  " Master", since the single-master-timeline concept is retired.

## 2026-07-23 (doc/version cleanup)

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