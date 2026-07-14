"""
============================================================
SBA AI Studio
Timeline Placement Builder
ML-011-014
Version : 3.2.0 Alpha
============================================================

Creates fully populated TimelinePlacement objects from
PlanningSegments.

This service calculates timeline placement information but
does not communicate with DaVinci Resolve.

Version 3.1 adds stable per-camera track assignment (the same
camera always lands on the same track across the whole
project) on top of the existing gap-preserving, real-ride-time
frame placement.

Version 3.2 accepts the real Resolve timeline frame rate at
construction time instead of always assuming a fixed 25fps.
Both record_frame (position) and duration_frames (length) now
use this same fps consistently - previously duration_frames
used each clip's own native capture fps, which is wrong: Resolve
conforms clips of differing native frame rates to play back at
normal speed on the timeline's own frame rate, so a clip's real
duration must be expressed in timeline frames to stay consistent
with its position.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sba_resolve.core.models.planning_segment import PlanningSegment
from sba_resolve.core.models.timeline_placement import TimelinePlacement
from sba_resolve.core.services.project_time_service import (
    ProjectTimeService,
)
from sba_resolve.core.services.timeline_fps import DEFAULT_PROJECT_FPS


class TimelinePlacementBuilder:
    """
    Builds TimelinePlacement objects from PlanningSegments.
    """

    # Kept as a class attribute (rather than only importing
    # DEFAULT_PROJECT_FPS directly) so existing references to
    # TimelinePlacementBuilder.DEFAULT_FPS keep working.
    # MulticamDetector uses the same shared constant so the two
    # services can't silently drift out of sync.
    DEFAULT_FPS = DEFAULT_PROJECT_FPS

    # Preferred, stable track order. Matches
    # CameraTrackBuilder.DEFAULT_ORDER so planning and Resolve
    # track assignment agree with each other.
    DEFAULT_CAMERA_ORDER = [
        "GoPro HERO13 Black",
        "GoPro HERO8 Black",
        "Insta360 X3",
        "DJI Flip",
        "Unknown Camera",
    ]

    def __init__(
        self,
        camera_order: list[str] | None = None,
        fps: float | None = None,
    ) -> None:

        self.camera_order = camera_order or list(self.DEFAULT_CAMERA_ORDER)

        # The real Resolve timeline frame rate, read at build time
        # in create_timeline.py and passed down through
        # TimelinePlanningService. Falls back to DEFAULT_FPS if not
        # provided (e.g. in tests, or before a timeline exists).
        self.fps = fps if fps and fps > 0 else self.DEFAULT_FPS

    def build(
        self,
        segments: Iterable[PlanningSegment],
    ) -> list[TimelinePlacement]:

        segments = list(segments)

        if not segments:
            return []

        media_files = []

        for segment in segments:
            media_files.extend(segment.available_clips)

        project_start = ProjectTimeService.project_start(media_files)

        # camera name -> track index, discovered as new cameras
        # appear. Stable for the lifetime of this build() call.
        track_index_by_camera: dict[str, int] = {}

        placements: list[TimelinePlacement] = []

        for segment in segments:

            for media in segment.available_clips:

                placement = TimelinePlacement(
                    media_file=media
                )

                placement.ride_day = segment.ride_day

                placement.camera_name = (
                    getattr(media, "camera_display_name", None)
                    or getattr(media, "camera_model", None)
                    or "Unknown"
                )

                placement.clip_name = getattr(
                    media,
                    "filename",
                    "",
                )

                placement.track_index = self._track_index_for(
                    placement.camera_name,
                    track_index_by_camera,
                )

                placement.record_frame = self._record_frame(
                    media,
                    project_start,
                )

                placement.duration_frames = self._duration_frames(
                    media
                )

                placements.append(placement)

        return placements

    def _track_index_for(
        self,
        camera_name: str,
        track_index_by_camera: dict[str, int],
    ) -> int:
        """
        Return a stable track index for a camera, assigning new
        indexes as previously-unseen cameras are encountered.
        """

        if camera_name in track_index_by_camera:
            return track_index_by_camera[camera_name]

        if camera_name in self.camera_order:
            index = self.camera_order.index(camera_name) + 1
        else:
            # Unrecognised camera: append after all known slots.
            unrecognised_already_assigned = [
                c for c in track_index_by_camera
                if c not in self.camera_order
            ]
            index = (
                len(self.camera_order)
                + len(unrecognised_already_assigned)
                + 1
            )

        track_index_by_camera[camera_name] = index

        return index

    def _record_frame(
        self,
        media,
        project_start: datetime | None,
    ) -> int:

        if project_start is None:
            return 0

        capture_time = (
            getattr(media, "capture_time", None)
            or getattr(media, "created", None)
        )

        if capture_time is None:
            return 0

        delta = (
            capture_time - project_start
        ).total_seconds()

        return round(delta * self.fps)

    def _duration_frames(
        self,
        media,
    ) -> int:

        duration = getattr(media, "duration", None)

        if duration is None:
            return 0

        try:
            return round(float(duration) * self.fps)
        except (TypeError, ValueError):
            return 0