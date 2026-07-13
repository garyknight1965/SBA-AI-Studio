"""
============================================================
SBA AI Studio
Workspace
Version : 4.0.0 Alpha
Sprint : PW-001
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sba_resolve.core.models.media_library import MediaLibrary


@dataclass(slots=True)
class Workspace:
    """
    Root domain model for SBA AI Studio.
    """

    project_name: str
    project_root: Path

    media: MediaLibrary = field(default_factory=MediaLibrary)

    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)

    version: str = "4.0.0 Alpha"

    @property
    def is_empty(self) -> bool:
        return self.media.is_empty

    @property
    def total_files(self) -> int:
        return self.media.total_files

    def touch(self) -> None:
        self.modified = datetime.now()

    def clear(self) -> None:
        self.media.clear()
        self.touch()

    def statistics(self) -> dict:
        return {
            "project": self.project_name,
            "files": self.total_files,
            "created": self.created,
            "modified": self.modified,
            "version": self.version,
        }

    def __str__(self) -> str:
        return f"Workspace({self.project_name}, {self.total_files} files)"

    __repr__ = __str__
