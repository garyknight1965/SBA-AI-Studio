"""
============================================================
SBA AI Studio
Gap Compressor
ML-012-002
Version : 1.0.0 Alpha
============================================================

Builds a real-time -> effective-time mapping used to
optionally compress long real-world gaps between clips.

This is a pure Planning Engine concern: it decides *what*
the effective timeline time of every moment should be. It
never touches Resolve.

TimelinePlacementBuilder and MulticamDetector both convert
real capture time to timeline frames. To agree with each
other under Gap Compression, they must both go through the
same GapCompressionMap instance for a given plan() call
(built once by TimelinePlanningService and passed to both).

When Gap Compression is disabled, build_map() returns an
identity mapping (no breakpoints), so effective_time(t) == t
and every existing gap-preserving calculation is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable

from sba_resolve.core.models.gap_compression_settings import (
    GapCompressionSettings,
)


@dataclass(slots=True)
class GapCompressionMap:
    """
    Piecewise real-time -> effective-time mapping.

    breakpoints is a chronologically ordered list of
    (boundary_time, cumulative_offset) pairs. cumulative_offset
    is the total amount of real time removed by every
    compressed gap up to and including `boundary_time`.
    """

    breakpoints: list[tuple[datetime, timedelta]] = field(
        default_factory=list
    )

    def effective_time(self, real_time: datetime) -> datetime:
        """
        Convert a real capture timestamp into its effective
        (possibly gap-compressed) timeline timestamp.
        """

        offset = timedelta(0)

        for boundary, cumulative in self.breakpoints:

            if real_time < boundary:
                break

            offset = cumulative

        return real_time - offset


class GapCompressor:
    """
    Builds a GapCompressionMap from a collection of MediaFiles.
    """

    def __init__(
        self,
        settings: GapCompressionSettings | None = None,
    ) -> None:

        self.settings = settings or GapCompressionSettings()

    def build_map(self, media_files: Iterable) -> GapCompressionMap:
        """
        Build the real-time -> effective-time mapping for the
        given media files.

        Returns an identity map (no breakpoints) when Gap
        Compression is disabled, or when there are fewer than
        two timestamped clips to compress a gap between.
        """

        if not self.settings.enabled:
            return GapCompressionMap()

        intervals = []

        for media in media_files:

            start = (
                getattr(media, "capture_time", None)
                or getattr(media, "created", None)
            )

            if start is None:
                continue

            end = start + timedelta(
                seconds=self._duration_seconds(media)
            )

            intervals.append((start, end))

        if len(intervals) < 2:
            return GapCompressionMap()

        intervals.sort(key=lambda interval: interval[0])

        threshold = timedelta(
            seconds=self.settings.gap_threshold_seconds
        )

        replacement = timedelta(
            seconds=self.settings.compressed_gap_seconds
        )

        breakpoints: list[tuple[datetime, timedelta]] = []

        cumulative = timedelta(0)

        # Tracks the latest clip end seen so far, not just the
        # previous clip's end, so overlapping/out-of-order
        # clips (e.g. a second camera starting mid-clip) don't
        # produce a false gap.
        latest_end = intervals[0][1]

        for start, end in intervals[1:]:

            gap = start - latest_end

            if gap > threshold:

                removed = gap - replacement

                cumulative += removed

                breakpoints.append((start, cumulative))

            if end > latest_end:
                latest_end = end

        return GapCompressionMap(breakpoints=breakpoints)

    @staticmethod
    def _duration_seconds(media) -> float:

        raw_duration = getattr(media, "duration", "")

        try:
            return float(raw_duration)
        except (TypeError, ValueError):
            return 0.0
