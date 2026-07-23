# Historical: Master Development Roadmap v1.0

**Status: superseded and retired (2026-07-23).** This document is kept for
history only. It was an early ChatGPT-era planning document (tagged
`v0.4.0-alpha`, `Sprint ML-011`), and no longer reflects the current
state of the project. For current status and milestones, see
`docs/Roadmap.md`. For architecture, see `docs/Architecture.md`. For
detailed release history, see the root `CHANGELOG.md`.

---

I think the roadmap is the right idea, but I'm going to improve it in one important way.

Instead of being a chat summary, it will become a **software engineering specification**. It will be version-controlled alongside the code and updated after every completed task.

I recommend creating:

```text
D:\Projects\SBA-AI-Studio\docs\
    Master_Development_Roadmap.md
```

instead of keeping it only in ChatGPT.

## Why?

If six months from now someone clones your GitHub repository, they should be able to understand the project **without reading our chats**.

---

# SBA AI Studio — Master Development Roadmap v1.0

## Project Information

| Item              | Value              |
| ----------------- | ------------------ |
| Project           | SBA AI Studio      |
| Current Version   | v0.4.0-alpha       |
| Current Sprint    | ML-011             |
| Development Model | Vertical Slice     |
| Status            | Active Development |

---

# Vision

Build a professional desktop application that assists motorcycle content creators from media import through final publication.

Pipeline:

```text
Media Import
      │
      ▼
Metadata Extraction
      │
      ▼
Ride Reconstruction
      │
      ▼
Planning Engine
      │
      ▼
Timeline Builder
      │
      ▼
Resolve Integration
      │
      ▼
Creator Assistant
      │
      ▼
AI Editing
```

---

# Development Principles

### The application must always work.

After every completed task:

```powershell
python start.py

python run_regression.py
```

Both must succeed.

No exceptions.

---

### One feature per task

Never mix multiple business responsibilities.

One feature.

One regression.

One commit.

---

### Complete files only

Never partial edits.

Never snippets.

Every implementation task contains complete replacement files.

---

### Inspect before building

Before introducing any class or service:

1. Inspect existing code.
2. Extend existing architecture if possible.
3. Only create new code when justified.

---

### Domain ownership

| Model            | Responsibility                |
| ---------------- | ----------------------------- |
| MediaFile        | Media metadata                |
| CameraProfile    | Camera identity               |
| CameraAssignment | Project-specific camera usage |
| RideDay          | Ride segmentation             |
| TimelinePlan     | Planned edit structure        |

Services orchestrate.

Models own business data.

---

# Completed Work

## Foundation

* Project Scanner
* Metadata Engine
* ExifTool Engine
* Metadata Mapper
* Metadata Normalizer
* Media Library
* Duplicate Detection

Status:

✅ Complete

---

## Resolve Integration

* Resolve Connector
* Project Creation
* Media Import
* Timeline Creation

Status:

✅ Operational

---

## Planning Engine

Completed:

* DayDetector
* PlanningStep
* PlanningPipeline
* CameraAssignment
* CameraAssignmentRepository

Status:

🟡 In Progress

---

## Regression

Completed:

* Unified regression framework
* ExifTool regression
* Metadata regression
* Scanner regression

Status:

✅ Stable

---

# Current Architecture

```text
MediaLibrary
        │
        ▼
MediaFile
        │
        ▼
CameraProfile
        │
        ▼
CameraAssignment
        │
        ▼
PlanningPipeline
        │
        ▼
TimelineBuilderService
        │
        ▼
TimelinePlan
        │
        ▼
Resolve
```

---

# Technical Debt

## High Priority

* Replace TimelineBuilderService incrementally with PlanningPipeline.
* Eliminate remaining duplicate logic.
* Add regression tests for new planning components.

## Medium Priority

* Remove unused placeholder files.
* Standardize service interfaces.

## Low Priority

* Documentation cleanup.

---

# Backlog

## INF-001

Portable Application

Status:

Backlog

---

## UI-001

Camera Profiles UI

Status:

Backlog

---

## AI-001

AI Gateway

Status:

Backlog

---

## AI-002

Creator Assistant

Status:

Backlog

---

## AI-003

AI Editing

Status:

Backlog

---

# Current Sprint

Sprint:

ML-011

Completed:

* ML-011A
* ML-011B
* ML-011C
* ML-011D

Remaining:

* ML-011E
* ML-011F

---

# Development Workflow

```text
Inspect

↓

Design

↓

Approve

↓

Implement

↓

Test

↓

Regression

↓

Commit

↓

Update Roadmap
```

---

# Git Workflow

Every completed feature:

```text
Feature

↓

python start.py

↓

python run_regression.py

↓

Git Commit

↓

Update Roadmap
```

---

# Current Checkpoint

Latest completed milestone:

```text
CORE-011C
CameraAssignmentRepository

PlanningPipeline

Regression Green
```

Application Status:

🟢 Stable

---

# Next Task

**ML-011E**

Integrate the Planning Pipeline into the existing timeline workflow while preserving the current behavior of `TimelineBuilderService`.

No new services.

No duplicate logic.

One file.

One commit.

---

## One final recommendation

I recommend we keep this roadmap under version control and update it **at the end of every completed task**.

That way:

* Git records the code changes.
* The roadmap records the architectural intent.
* Any future ChatGPT conversation can start by reading **one document** instead of reconstructing weeks of development history.

I think this will make SBA AI Studio much easier to maintain as it grows into the production tool you've envisioned.
