"""
============================================================
SBA AI Studio
Media Validation Report
ML-014-001
Version : 1.0.0 Alpha
============================================================

Output of the Source Media Validation Engine.

Only original camera footage should enter the Planning Engine.
Everything else (images, sidecar files, cache/proxy leftovers,
audio-only files, or rendered/exported video) is rejected here,
with a human-readable reason, so it never silently pollutes the
Media Pool or the timeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RejectedMedia:
    """
    One file the Source Media Validation Engine refused to
    accept, and why.
    """

    full_path: Path
    filename: str
    reason: str


@dataclass(slots=True)
class MediaValidationReport:
    """
    Result of validating a batch of scanned files.
    """

    accepted: list = field(default_factory=list)
    rejected: list[RejectedMedia] = field(default_factory=list)

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    def rejected_by_reason(self) -> dict[str, int]:
        """
        Count of rejected files grouped by reason, for a
        compact summary.
        """

        counts: dict[str, int] = {}

        for item in self.rejected:
            counts[item.reason] = counts.get(item.reason, 0) + 1

        return counts

    def summary(self) -> str:
        """
        A short, human-readable summary line.
        """

        return (
            f"Source Media Validation: {self.accepted_count} "
            f"accepted, {self.rejected_count} rejected"
        )

    def print_report(self, max_examples: int = 10) -> None:
        """
        Print the validation report to stdout: a summary line,
        a per-reason breakdown, and a capped list of examples.
        """

        print(self.summary())

        if not self.rejected:
            return

        print("Rejected, by reason:")

        for reason, count in sorted(
            self.rejected_by_reason().items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(f"  {count:>4}  {reason}")

        print()
        print("Rejected files:")

        for item in self.rejected[:max_examples]:
            print(f"  - {item.filename} ({item.reason})")

        remaining = len(self.rejected) - max_examples

        if remaining > 0:
            print(f"  ... and {remaining} more")
