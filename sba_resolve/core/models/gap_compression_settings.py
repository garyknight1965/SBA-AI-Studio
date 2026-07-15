"""
============================================================
SBA AI Studio
Gap Compression Settings
ML-012-001
Version : 1.0.0 Alpha
============================================================

Configuration for optional Gap Compression.

Gap Compression is OFF by default. When off, the Planning
Engine behaves exactly as before: clips are placed at their
real ride-time positions and every real gap is preserved in
full (this is what synced multicam / true ride-time
reconstruction depends on).

When enabled, any real-world gap longer than
`gap_threshold_seconds` is shortened to
`compressed_gap_seconds` on the timeline, while gaps shorter
than the threshold are left untouched. Clip order and clip
durations are never changed - only the dead space between
clips is affected.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GapCompressionSettings:
    """
    Configurable Gap Compression behaviour.
    """

    # Master switch. False reproduces the original, fully
    # gap-preserving placement behaviour.
    enabled: bool = False

    # Real-world gaps longer than this are compressed.
    # Gaps at or below this threshold are left exactly as they
    # were captured (e.g. natural pauses between clips of the
    # same stop shouldn't be chopped down).
    gap_threshold_seconds: float = 60.0

    # The length a compressed gap is shortened to. Must be
    # strictly less than gap_threshold_seconds or there is
    # nothing to compress.
    compressed_gap_seconds: float = 2.0

    def __post_init__(self) -> None:

        if self.gap_threshold_seconds < 0:
            raise ValueError("gap_threshold_seconds cannot be negative.")

        if self.compressed_gap_seconds < 0:
            raise ValueError("compressed_gap_seconds cannot be negative.")

        if self.compressed_gap_seconds > self.gap_threshold_seconds:
            raise ValueError(
                "compressed_gap_seconds cannot be greater than "
                "gap_threshold_seconds."
            )
