# ADR-001 – SBA AI Studio Project Architecture

Status: Accepted

Date: 2026-07-11

---

# Context

SBA AI Studio is evolving from a collection of automation scripts into a modular software platform for DaVinci Resolve Studio.

The project requires a long-term architecture capable of supporting media management, timeline creation, AI-assisted editing, rendering and publishing without major refactoring.

---

# Decision

The application will follow a layered, domain-driven architecture.

```
start.py

↓

Core

↓

Managers

↓

Services

↓

Commands

↓

DaVinci Resolve API
```

Business functionality is organised by domain rather than by technical type.

---

# Core

Responsible for:

- Bootstrap
- Application lifecycle
- Resolve connection
- Shared context
- Reporting

---

# Business Domains

Each domain owns its own:

- manager
- services
- commands
- models
- validators

Examples:

- Media Pool
- Timeline
- Render
- AI
- Publish

---

# Commands

Commands perform exactly one Resolve operation.

Examples:

- sync_bins()
- import_media()
- verify_media()
- create_timeline()

---

# Managers

Managers orchestrate commands.

Managers never call the Resolve API directly.

---

# Services

Services contain business logic.

Services coordinate multiple commands.

---

# Resolve Context

ResolveContext contains Resolve runtime state only.

Business data belongs inside domain models.

---

# Principles

1. One responsibility per file.
2. One business domain per folder.
3. Managers orchestrate.
4. Services contain business logic.
5. Commands perform one Resolve action.
6. Resolve API access is isolated to commands.
7. Core never depends on business domains.
8. Business domains may depend on Core.

---

# Consequences

This architecture enables SBA AI Studio to grow into a professional editing platform while keeping each feature isolated, testable and maintainable.

Future milestones will migrate toward this structure incrementally rather than through large-scale rewrites.