# SBA AI Studio Architecture

Version: 2.1.0

---

# Overview

SBA AI Studio is a modular automation platform built around DaVinci Resolve Studio.

Its purpose is to automate repetitive editing tasks while keeping the editor in complete creative control.

The application is built as a layered architecture where every component has a single responsibility.

---

# High Level Architecture

```
start.py
      │
      ▼
Bootstrap
      │
      ▼
Bridge
      │
      ▼
Resolve Connector
      │
      ▼
Resolve Context
      │
      ▼
Commands
```

---

# Layer Responsibilities

## start.py

Application entry point.

Responsible for:

- configuring Python
- starting SBA AI Studio

---

## bootstrap.py

Responsible for:

- locating the project
- configuring Python paths
- preparing the runtime environment

---

## run_bridge.py

Responsible for:

- loading the Bridge JSON
- creating the connector
- starting execution

---

## connector.py

Responsible for orchestrating commands.

The connector contains **no business logic**.

---

## context.py

Shared runtime state.

All commands receive exactly one object:

```python
context
```

---

## Commands

Every Resolve action is implemented as a command.

Example:

```
create_project()

sync_bins()

import_media()

create_timeline()
```

Commands never communicate with each other directly.

They only use the shared ResolveContext.

---

# Design Principles

- Single Responsibility Principle
- Layered Architecture
- Complete file replacements
- Milestone-based development
- Production-first design

---

# Future Milestones

Milestone 3

Media Pool Management

Milestone 4

Timeline Builder

Milestone 5

AI Editing Engine

Milestone 6

Rendering Pipeline