"""
SBA AI Studio
Capture Time Models

Defines the data structures used by the Capture Time Resolver.

Author: SBA AI Studio
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class TimestampCandidate:
    """
    Represents a possible capture timestamp discovered from metadata.
    """

    timestamp: datetime
    source: str
    confidence: int
    valid: bool = True


@dataclass(slots=True)
class CaptureTimeResult:
    """
    Final result returned by the Capture Time Resolver.
    """

    resolved_time: datetime | None = None
    source: str | None = None
    confidence: int = 0
    candidates: list[TimestampCandidate] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        """
        Returns True when a valid timestamp has been resolved.
        """
        return self.resolved_time is not None