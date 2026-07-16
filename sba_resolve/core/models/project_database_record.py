"""
============================================================
SBA AI Studio
Project Database Record
Version : 1.0.0
Sprint  : ML-030
============================================================

One persisted fingerprint of a media file inside a project's
Project Database (see core/database/project_database.py).

This is deliberately lighter than MediaFile - it only stores
what's needed to detect a file going missing, appearing new,
or being flagged corrupted between scans. It is JSON-serialisable
as-is (dataclasses.asdict + json.dumps), so it has no Path,
datetime, or other non-primitive fields.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProjectDatabaseRecord:
    """
    Persisted, per-file entry in the Project Database.
    """

    relative_path: str

    size: int

    modified: str = ""

    corrupted: bool = False

    corruption_reason: str = ""

    first_seen: str = ""

    last_seen: str = ""
