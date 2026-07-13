"""
SBA AI Studio

Scanner Statistics
ML-006A
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter


@dataclass(slots=True)
class ScannerStatistics:
    """
    Runtime statistics collected during a scan.
    """

    folders_scanned: int = 0
    files_scanned: int = 0
    media_found: int = 0
    folders_skipped: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    _started: float = field(default_factory=perf_counter)

    @property
    def elapsed(self) -> float:
        return perf_counter() - self._started

    @property
    def successful(self) -> bool:
        return len(self.errors) == 0

    def reset(self) -> None:
        self.folders_scanned = 0
        self.files_scanned = 0
        self.media_found = 0
        self.folders_skipped = 0
        self.files_skipped = 0
        self.errors.clear()
        self._started = perf_counter()