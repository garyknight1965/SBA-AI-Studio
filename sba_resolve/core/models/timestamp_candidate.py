"""
============================================================
SBA AI Studio
Timestamp Candidate
Version : 1.0.0
Sprint  : MI-002A
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, order=True)
class TimestampCandidate:
    """
    Represents a possible capture timestamp discovered from metadata.

    Higher confidence values indicate a more trustworthy source.
    """

    confidence: int
    timestamp: datetime
    source: str

    @property
    def valid(self) -> bool:
        """Always True for a constructed candidate."""
        return True

    def __str__(self) -> str:
        return (
            f"{self.source}: "
            f"{self.timestamp.isoformat(sep=' ')} "
            f"(confidence={self.confidence})"
        )