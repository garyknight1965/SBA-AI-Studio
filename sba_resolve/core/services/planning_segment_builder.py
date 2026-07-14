"""
============================================================
SBA AI Studio
Planning Segment Builder
ML-011-012B
Version : 2.0.0 Alpha
============================================================

Creates PlanningSegment objects from chronologically
sorted MediaFile objects.

Version 2 groups consecutive clips recorded by the
same camera.

Future versions will merge clips based on timestamp
overlap and active camera sets.
"""

from __future__ import annotations

from typing import Iterable

from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.models.planning_segment import PlanningSegment


class PlanningSegmentBuilder:
    """
    Builds PlanningSegment objects.

    Version 2 groups consecutive clips belonging to the
    same camera.
    """

    def build(
        self,
        media_files: Iterable[MediaFile],
    ) -> list[PlanningSegment]:

        media = list(media_files)

        if not media:
            return []

        segments: list[PlanningSegment] = []

        current_segment = PlanningSegment()

        current_camera = self._camera_signature(media[0])

        for clip in media:

            camera = self._camera_signature(clip)

            if camera != current_camera:

                segments.append(current_segment)

                current_segment = PlanningSegment()

                current_camera = camera

            current_segment.add_clip(clip)

        segments.append(current_segment)

        return segments

    @staticmethod
    def _camera_signature(media: MediaFile) -> str:
        """
        Returns the logical camera identity.

        Future versions may include:
            - Audio source
            - 360 camera
            - Drone
            - Transcript availability
        """

        return (
            getattr(media, "camera_display_name", None)
            or getattr(media, "camera_model", None)
            or "Unknown"
        )