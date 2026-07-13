"""
============================================================
SBA AI Studio
Duplicate Group
Version : 1.0.0
Sprint : ML-008B
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sba_resolve.core.models.media_file import MediaFile


@dataclass(slots=True)
class DuplicateGroup:
    """
    Represents one set of duplicate media.
    """

    key: str

    files: list[MediaFile] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def newest(self) -> MediaFile | None:
        if not self.files:
            return None

        return max(
            self.files,
            key=lambda m: (
                m.created is not None,
                m.created,
            ),
        )

    @property
    def oldest(self) -> MediaFile | None:
        if not self.files:
            return None

        return min(
            self.files,
            key=lambda m: (
                m.created is None,
                m.created,
            ),
        )