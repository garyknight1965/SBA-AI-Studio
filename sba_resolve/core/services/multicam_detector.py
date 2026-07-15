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
from sba_resolve.core.services.gap_compressor import GapCompressionMap
from sba_resolve.core.services.timeline_fps import DEFAULT_PROJECT_FPS


class MulticamDetector:
    """
    Detects overlapping-camera windows from TimelinePlacements.
    """

    def __init__(self, fps: float | None = None) -> None:

        # Must match whatever fps TimelinePlacementBuilder used to
        # compute record_frame, or the anchor-based frame
        # conversion below will disagree with the actual timeline.
        self.fps = fps if fps and fps > 0 else DEFAULT_PROJECT_FPS

    def detect(
        self,
        placements: Iterable[TimelinePlacement],
        gap_map: GapCompressionMap | None = None,
    ) -> list[MulticamCandidate]:
        """
        Parameters
        ----------
        placements
            TimelinePlacements to scan for overlapping-camera
            windows.
        gap_map
            Optional GapCompressionMap. Must be the SAME
            instance used to build `placements` (via
            TimelinePlacementBuilder), or the anchor-based
            frame conversion below will disagree with the
            actual timeline. Defaults to an identity map (no
            compression), matching the original behaviour.
        """

        placements = list(placements)

        if not placements:
            return []

        gap_map = gap_map or GapCompressionMap()

        # Every placement shares the same project_start, the same
        # DEFAULT_PROJECT_FPS, and the same gap_map (see
        # TimelinePlacementBuilder), so any single placement's
        # (created, record_frame) pair anchors the same real-time
        # -> frame mapping for the whole project (piecewise-linear
        # when Gap Compression is enabled, linear otherwise). Used
        # to convert overlap-window boundaries (computed in real
        # time) back to frames.
        anchor = placements[0]

        by_day: dict[int, list[TimelinePlacement]] = defaultdict(list)

        for placement in placements:
            by_day[placement.ride_day].append(placement)

        candidates: list[MulticamCandidate] = []

        for ride_day in sorted(by_day):
            candidates.extend(
                self._detect_for_day(by_day[ride_day], anchor, gap_map)
            )

        return candidates

    def _frame_for_time(
        self,
        time: datetime,
        anchor: TimelinePlacement,
        gap_map: GapCompressionMap,
    ) -> int:

        # With an identity gap_map (Gap Compression disabled),
        # effective_time(t) == t, so this is exactly the original
        # linear real-time -> frame formula.
        effective_time = gap_map.effective_time(time)
        effective_anchor_time = gap_map.effective_time(
            anchor.media_file.created
        )

        offset_seconds = (
            effective_time - effective_anchor_time
        ).total_seconds()

        return anchor.record_frame + round(
            offset_seconds * self.fps
        )

    def _detect_for_day(
        self,
        day_placements: list[TimelinePlacement],
        anchor: TimelinePlacement,
        gap_map: GapCompressionMap,
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
                start_frame=self._frame_for_time(
                    window_start, anchor, gap_map
                ),
                end_frame=self._frame_for_time(
                    window_end, anchor, gap_map
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
