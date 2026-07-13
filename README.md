# SBA AI Studio

> Professional AI-assisted workflow for DaVinci Resolve Studio.

---

# Vision

SBA AI Studio is a modular automation platform for DaVinci Resolve.

The goal is to automate repetitive editing tasks while keeping the editor in full control of creative decisions.

Instead of replacing editors, SBA AI Studio acts as an intelligent assistant capable of preparing projects, organizing media, creating timelines, suggesting edits and eventually producing complete first cuts.

---

# Current Status

Version

2.1.0

Current Milestone

Project Foundation

---

# Features

Current

- Resolve Bootstrap
- Resolve Connector
- Shared Resolve Context
- Project Creation
- Media Pool Bin Synchronization
- Project Bridge JSON

Planned

- Media Import
- Duplicate Detection
- Timeline Builder
- Marker Management
- Transcript Processing
- AI Story Builder
- Render Queue
- YouTube Publishing

---

# Project Structure

```
SBA-AI-Studio
│
├── start.py
│
├── sba_resolve
│
├── projects
│
├── tools
│
├── tests
│
├── development
│
└── docs
```

---

# Startup

Open the DaVinci Resolve Python Console.

Run

```python
exec(open(r"D:\Projects\SBA-AI-Studio\start.py").read())
```

The application will

- configure Python
- bootstrap SBA AI Studio
- load the Bridge Project
- connect to Resolve
- execute the Resolve Connector

---

# Architecture

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

Every layer has a single responsibility.

---

# Development Workflow

Every milestone follows exactly the same process.

```
Design

↓

Implementation

↓

Compile

↓

Validation

↓

Resolve Demo

↓

Release
```

---

# Coding Standards

- One responsibility per file
- Complete file replacements only
- No snippets
- Type hints where appropriate
- PEP 8
- Production-first architecture

---

# Repository Status

Milestone 2.1

Project Foundation

Status

In Development

---

# Author

Gary Knight

Scottish Biker Abroad

The Netherlands