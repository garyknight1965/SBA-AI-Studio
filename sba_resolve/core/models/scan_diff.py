"""
============================================================
SBA AI Studio
Scan Diff
Version : 1.0.0
Sprint  : ML-030
============================================================

Result of comparing the Project Database from a previous scan
against the current scan: what appeared, what went missing, and
what is currently flagged corrupted.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScanDiff:
    """
    Difference between two Project Database snapshots.
    """

    new_files: list[str] = field(default_factory=list)

    missing_files: list[str] = field(default_factory=list)

    corrupted_files: list[str] = field(default_factory=list)

    newly_corrupted: list[str] = field(default_factory=list)

    unchanged_count: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_files
            or self.missing_files
            or self.corrupted_files
        )

    def summary(self) -> str:

        return (
            f"Project Database: {self.unchanged_count} unchanged, "
            f"{len(self.new_files)} new, "
            f"{len(self.missing_files)} missing, "
            f"{len(self.corrupted_files)} corrupted"
        )

    def print_report(self, max_examples: int = 10) -> None:
        """
        Print a short, human-readable report to stdout.
        """

        print(self.summary())

        if self.missing_files:
            print("Missing (previously scanned, not found now):")
            for path in self.missing_files[:max_examples]:
                print(f"  - {path}")
            remaining = len(self.missing_files) - max_examples
            if remaining > 0:
                print(f"  ... and {remaining} more")

        if self.corrupted_files:
            print("Corrupted:")
            for path in self.corrupted_files[:max_examples]:
                print(f"  - {path}")
            remaining = len(self.corrupted_files) - max_examples
            if remaining > 0:
                print(f"  ... and {remaining} more")

        if self.newly_corrupted:
            print(
                f"  ({len(self.newly_corrupted)} of these are "
                f"newly corrupted since the last scan)"
            )
