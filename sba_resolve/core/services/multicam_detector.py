"""
============================================================
SBA AI Studio
Multicam Detector
ML-011-017
Version : 1.0.0 Alpha
============================================================

Detects periods where two or more cameras were recording at
the same real-world time (a "multicam candidate") - the
prerequisite for later automatic multicam clip creation in
Resolve.

Detection runs on real capture timestamps (MediaFile.created +
duration), not on timeline frames, so it isn't affected by any
frame-rate assumptions made elsewhere in the pipeline. The
resulting MulticamCandidate's frame numbers are read back from
the already-computed TimelinePlacements, so they stay
consistent with wherever those clips actually land on the
Resolve timeline.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable

from sba_resolve.core.models.multicam_candidate import MulticamCandidate
from sba_resolve.core.models.timeline_placement import TimelinePlacement


class MulticamDetector:
    """
    Detects overlapping-camera windows from TimelinePlacements.
    """

    def detect(
        self,
        placements: Iterable[TimelinePlacement],
    ) -> list[MulticamCandidate]:

        placements = list(placements)

        if not placements:
            return []

        by_day: dict[int, list[TimelinePlacement]] = defaultdict(list)

        for placement in placements:
            by_day[placement.ride_day].append(placement)

        candidates: list[MulticamCandidate] = []

        for ride_day in sorted(by_day):
            candidates.extend(self._detect_for_day(by_day[ride_day]))

        return candidates

    def _detect_for_day(
        self,
        day_placements: list[TimelinePlacement],
    ) -> list[MulticamCandidate]:

        intervals = []

        for placement in day_placements:

            start = getattr(placement.media_file, "created", None)

            if start is None:
                continue

            end = start + timedelta(
                seconds=self._duration_seconds(placement.media_file)
            )

            if end <= start:
                continue

            intervals.append((start, end, placement))

        if len(intervals) < 2:
            return []

        # ------------------------------------------------
        # Sweep: find maximal real-time ranges where 2+
        # distinct cameras are simultaneously active.
        # ------------------------------------------------

        events = []

        for start, end, placement in intervals:
            events.append((start, 0, placement.camera_name))  # start
            events.append((end, 1, placement.camera_name))  # end

        # Sort by time; process ends (1) before starts (0) at the
        # same instant so touching-but-not-overlapping clips don't
        # falsely register as overlapping.
        events.sort(key=lambda event: (event[0], event[1]))

        active_counts: dict[str, int] = defaultdict(int)

        windows: list[tuple[datetime, datetime]] = []

        window_start: datetime | None = None

        for time, kind, camera in events:

            distinct_before = sum(
                1 for count in active_counts.values() if count > 0
            )

            if kind == 0:
                active_counts[camera] += 1
            else:
                active_counts[camera] -= 1

            distinct_after = sum(
                1 for count in active_counts.values() if count > 0
            )

            if distinct_before < 2 and distinct_after >= 2:
                window_start = time

            elif distinct_before >= 2 and distinct_after < 2:
                if window_start is not None:
                    windows.append((window_start, time))
                    window_start = None

        if not windows:
            return []

        # ------------------------------------------------
        # For each window, gather every clip whose real-world
        # interval intersects it, and translate to the frame
        # numbers already computed for the timeline.
        # ------------------------------------------------

        candidates: list[MulticamCandidate] = []

        for window_start, window_end in windows:

            window_placements = [
                placement
                for start, end, placement in intervals
                if start < window_end and end > window_start
            ]

            if len({p.camera_name for p in window_placements}) < 2:
                continue

            candidate = MulticamCandidate(
                start_frame=min(
                    p.record_frame for p in window_placements
                ),
                end_frame=max(
                    p.record_frame + p.duration_frames
                    for p in window_placements
                ),
                confidence=1.0,
                reason=(
                    "Overlapping capture: "
                    + ", ".join(
                        sorted(
                            {p.camera_name for p in window_placements}
                        )
                    )
                ),
            )

            for placement in window_placements:
                candidate.add_clip(placement.media_file)

            candidates.append(candidate)

        return candidates

    @staticmethod
    def _duration_seconds(media) -> float:

        raw_duration = getattr(media, "duration", "")

        try:
            return float(raw_duration)
        except (TypeError, ValueError):
            return 0.0
