"""
============================================================
SBA AI Studio
Timeline Marker Generator
ML-011-018
Version : 1.0.0 Alpha
============================================================

Generates TimelineMarker objects for a reconstructed ride:
one marker at the start of each ride day, and one at the start
of each detected multicam window.

Future versions may add markers for transcript-available
segments, favourite/highlight clips, or AI-suggested chapter
points.
"""

from __future__ import annotations

from typing import Iterable

from sba_resolve.core.models.multicam_candidate import MulticamCandidate
from sba_resolve.core.models.timeline_marker import TimelineMarker
from sba_resolve.core.models.timeline_placement import TimelinePlacement


class TimelineMarkerGenerator:
    """
    Builds TimelineMarkers from placements and multicam candidates.
    """

    RIDE_DAY_COLOUR = "Blue"

    MULTICAM_COLOUR = "Purple"

    def generate(
        self,
        placements: Iterable[TimelinePlacement],
        multicam_candidates: Iterable[MulticamCandidate],
    ) -> list[TimelineMarker]:

        placements = list(placements)
        multicam_candidates = list(multicam_candidates)

        markers: list[TimelineMarker] = []

        markers.extend(self._ride_day_markers(placements))
        markers.extend(self._multicam_markers(multicam_candidates))

        markers.sort(key=lambda marker: marker.frame)

        return markers

    @staticmethod
    def _ride_day_markers(
        placements: list[TimelinePlacement],
    ) -> list[TimelineMarker]:

        earliest_frame_by_day: dict[int, int] = {}

        for placement in placements:

            current = earliest_frame_by_day.get(placement.ride_day)

            if current is None or placement.record_frame < current:
                earliest_frame_by_day[placement.ride_day] = (
                    placement.record_frame
                )

        markers = []

        for ride_day in sorted(earliest_frame_by_day):

            markers.append(
                TimelineMarker(
                    frame=earliest_frame_by_day[ride_day],
                    title=f"Ride Day {ride_day}",
                    description="",
                    colour=TimelineMarkerGenerator.RIDE_DAY_COLOUR,
                    category="Ride Day",
                    generated=True,
                )
            )

        return markers

    @staticmethod
    def _multicam_markers(
        multicam_candidates: list[MulticamCandidate],
    ) -> list[TimelineMarker]:

        markers = []

        for candidate in multicam_candidates:

            markers.append(
                TimelineMarker(
                    frame=candidate.start_frame,
                    title=f"Multicam ({candidate.camera_count} cameras)",
                    description=candidate.reason,
                    colour=TimelineMarkerGenerator.MULTICAM_COLOUR,
                    category="Multicam",
                    generated=True,
                )
            )

        return markers
