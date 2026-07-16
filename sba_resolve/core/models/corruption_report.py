"""
============================================================
SBA AI Studio
Corruption Report
Version : 1.0.0
Sprint  : ML-030
============================================================

Output of the Corruption Detector service
(core/services/corruption_detector.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CorruptedMedia:
    """
    One file the Corruption Detector flagged, and why.
    """

    full_path: Path
    relative_path: str
    filename: str
    reason: str


@dataclass(slots=True)
class CorruptionReport:
    """
    Result of running the Corruption Detector over a batch of
    scanned files.
    """

    checked: int = 0

    corrupted: list[CorruptedMedia] = field(default_factory=list)

    @property
    def corrupted_count(self) -> int:
        return len(self.corrupted)

    def summary(self) -> str:

        return (
            f"Corruption Detector: {self.checked} checked, "
            f"{self.corrupted_count} corrupted"
        )

    def print_report(self, max_examples: int = 10) -> None:

        print(self.summary())

        if not self.corrupted:
            return

        print("Corrupted files:")

        for item in self.corrupted[:max_examples]:
            print(f"  - {item.filename} ({item.reason})")

        remaining = len(self.corrupted) - max_examples

        if remaining > 0:
            print(f"  ... and {remaining} more")
