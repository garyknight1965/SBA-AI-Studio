"""
============================================================
SBA AI Studio
Library Statistics
Version : 4.0.0 Alpha
Sprint : ML-005
============================================================
"""

from __future__ import annotations

from collections import Counter

from sba_resolve.core.models.media_library import MediaLibrary


class LibraryStatistics:

    def __init__(self, library: MediaLibrary) -> None:
        self._library = library

    @property
    def total_files(self) -> int:
        return len(self._library)

    @property
    def total_size(self) -> int:
        return sum(m.size for m in self._library)

    @property
    def camera_counts(self) -> dict[str, int]:
        return dict(Counter(m.camera_model for m in self._library))

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(Counter(m.category for m in self._library))

    @property
    def extension_counts(self) -> dict[str, int]:
        return dict(Counter(m.extension.lower() for m in self._library))

    @property
    def resolution_counts(self) -> dict[str, int]:
        return dict(
            Counter(f"{m.width}x{m.height}" for m in self._library)
        )
