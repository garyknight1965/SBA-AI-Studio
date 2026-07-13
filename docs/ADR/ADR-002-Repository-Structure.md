# ADR-002 – Repository Structure

Status: Accepted

Date: 2026-07-11

---

# Context

SBA AI Studio is expected to grow into a large software platform supporting
multiple business domains.

The repository structure must scale without becoming difficult to navigate.

---

# Decision

The repository is organised around business domains rather than technical layers.

```
SBA-AI-Studio
│
├── start.py
│
├── config/
│
├── sba_resolve/
│   ├── core/
│   ├── media_pool/
│   ├── timeline/
│   ├── render/
│   ├── ai/
│   ├── publish/
│   └── shared/
│
├── bridge/
│
├── docs/
│
├── tests/
│
├── development/
│
├── tools/
│
└── assets/
```

---

# Domain Responsibilities

## core

Application lifecycle.

## media_pool

Everything related to Resolve Media Pool management.

## timeline

Timeline creation and editing.

## render

Deliver page and rendering.

## ai

AI-assisted editing and automation.

## publish

Publishing to external platforms.

## shared

Reusable utilities shared between domains.

---

# Repository Principles

1. Business domains own their implementation.
2. Cross-domain dependencies are minimised.
3. Shared functionality belongs in `shared`.
4. Experimental code belongs in `development`.
5. Documentation lives in `docs`.
6. Tests mirror the production structure.

---

# Migration Strategy

The current repository will migrate incrementally.

Existing code remains functional while new features are introduced using the target structure.

Large-scale rewrites are avoided.

---

# Consequences

The repository remains understandable as it grows from a few dozen files to several hundred.

Future contributors can locate functionality by business domain rather than by implementation detail.