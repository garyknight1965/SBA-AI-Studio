# SBA AI Studio Roadmap

Version: 2.1.0

Last refreshed: 2026-07-23. See `CHANGELOG.md` for the detailed, dated
history behind every item below, and `docs/Architecture.md` for the
Planning Engine / Resolve Builder boundary these milestones respect.

---

# Vision

Build the most capable AI-assisted workflow for DaVinci Resolve Studio.

The objective is not to replace editors.

The objective is to eliminate repetitive work so editors can focus on
storytelling.

---

# Milestone 1

Foundation

Status

Complete

Deliverables

- Resolve Connection
- Project Creation

---

# Milestone 2

Application Foundation

Status

Complete

Deliverables

- Bootstrap
- Connector
- Context
- Documentation
- Versioning
- Startup Architecture

---

# Milestone 3

Media Pool Management

Status

Substantially complete

Deliverables

- Synchronize Bins - done (Day > Camera bin organisation)
- Import Media - done
- Detect Missing Media - done (Project Database tracks missing/new/corrupted files across scans)
- Cleanup Duplicate Bins - not separately verified against current code, revisit if bin duplication is ever observed in practice
- Folder Mapping - not separately verified against current code

---

# Milestone 4

Timeline Builder

Status

Mostly complete - one timeline per ride day now shipped; real multicam clip creation still open

Deliverables

- Timeline Creation - done
- Video Tracks - done
- Audio Tracks - done
- Markers - done
- Clip Placement - done (real `TimelinePlacement` data, three layers of write verification)
- One Resolve timeline PER RIDE DAY - **done** (2026-07-23). Each day builds its own independent timeline (e.g. "Test Project Day 1 - 2026-07-01"), with placements and markers rebased to that day's own earliest clip rather than the whole project's. `PlanningResult` itself stays project-wide; the split happens in `RideDayGrouper` at the Resolve Builder boundary. A "<project> Master" timeline is then assembled automatically, nesting every day's timeline into it in order for final review/export.
- Multicam Support - partial: overlap window detection + separate tracks are done; real Resolve multicam *clip* creation is not yet built

Known gap (highest priority open item)

- **Real Resolve multicam clip creation.** Currently overlap windows get separate per-camera tracks, not an actual Resolve multicam clip.

---

# Milestone 5

AI Assistant

Status

In progress - direction deliberately narrowed from the original scope

Deliverables

- Transcript Processing - done (Transcript -> IntelliScript AI Editor)
- Scene Detection - done, but boundaries only (gap-based); semantic
  scene *labelling* ("Fuel Stop", "Coffee Stop") is not yet built and
  needs deterministic scene facts (stopped duration, movement distance,
  speed profile, nearby locations, camera mix, transcript density, GPS
  confidence) computed first, before any AI-generated label is attempted
- Story Suggestions - not started
- Highlight Detection - not started
- Automatic First Cut - **not the current product direction.** Real-world
  testing found audio cross-correlation sync unreliable even between
  same-brand cameras, so the shipped design is deliberately "never
  guess": auto-place only high-confidence clips, put everything else on
  a clearly named placeholder track with sync markers, and produce a
  sync report. Placeholder tracks are the expected common case, not a
  failure mode to eliminate. Fully automatic cutting stays a low
  priority until that philosophy is proven wrong in practice.

---

# Milestone 6

Rendering

Status

Not started

Goals

- Deliver Page Integration
- Render Queue
- YouTube Export
- TikTok Export
- Archive Management

---

# Milestone 7

Creator Platform

Status

Partial

Goals

- YouTube Publishing - metadata generation (title/description/tags/chapters) is done; actual publishing/upload automation is not started
- Thumbnail Generation - not started
- Description Generation - done, as part of YouTube metadata generation
- SEO - tag generation done; broader SEO work not started
- Social Media Integration - not started

---

# Long-Term Vision

SBA AI Studio becomes a complete production assistant for motorcycle
creators. The software prepares projects, organises media, assists
editing, manages exports and supports publishing while keeping the
creator in control of every creative decision.

---

# Current Near-Term Priorities

In order, per the most recent architecture review:

1. Regression reliability and environment diagnostics - **done** (`--core`/`--ui`/`--resolve` modes, GUI dependency preflight)
2. Documentation/version cleanup - **in progress** (this document, `CHANGELOG.md`, `pyproject.toml`, `requirements.txt` encoding all refreshed; retired the old `Master_Development_Roadmap.md` to `docs/ADR/` as historical)
3. One Resolve timeline per ride day (see Milestone 4 above)
4. Harden the unsynced-multicam placeholder workflow (track naming, markers, sync report)
5. Deterministic scene-fact extraction, as groundwork for future AI-generated scene labels (see Milestone 5 above)
