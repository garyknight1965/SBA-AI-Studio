"""
============================================================
SBA AI Studio
Planning Segment Builder
ML-011-015A
Version : 3.0.0 Alpha
============================================================

Creates PlanningSegment objects from RideDay objects.

Each RideDay is converted into one or more PlanningSegments.

Version 3 groups consecutive clips recorded by the same
camera within each ride day.

Future versions will merge clips based on timestamp overlap
and active camera sets.
"""

from __future__ import annotations

from typing import Iterable

from sba_resolve.core.models.planning_segment import PlanningSegment
from sba_resolve.core.models.ride_day import RideDay


class PlanningSegmentBuilder:
    """
    Builds PlanningSegment objects from RideDay objects.
    """

    def build(
        self,
        ride_days: Iterable[RideDay],
    ) -> list[PlanningSegment]:

        segments: list[PlanningSegment] = []

        for ride_day in ride_days:

            current_segment: PlanningSegment | None = None
            current_camera: str | None = None

            for media in ride_day.clips:

                camera = self._camera_signature(media)

                if (
                    current_segment is None
                    or camera != current_camera
                ):

                    current_segment = PlanningSegment(
                        ride_day=ride_day.index
                    )

                    segments.append(current_segment)

                    current_camera = camera

                current_segment.add_clip(media)

        return segments

    @staticmethod
    def _camera_signature(media) -> str:
        """
        Return the logical camera identity.

        Future versions may expand this to include:
        - Audio source
        - Drone
        - 360 camera
        - Transcript availability
        """

        return (
            getattr(media, "camera_display_name", None)
            or getattr(media, "camera_model", None)
            or "Unknown"
        )