"""
============================================================
SBA AI Studio
Timeline Planning Service
ML-011-009
Version : 1.0.0 Alpha
============================================================

Planning Engine orchestrator.

Current workflow:

    MediaLibrary
        ↓
    TimelineSorter
        ↓
    PlanningSegmentBuilder
        ↓
    TimelinePlan
"""

from __future__ import annotations

from sba_resolve.core.models.timeline_plan import TimelinePlan
from sba_resolve.core.services.camera_track_allocator import (
    CameraTrackAllocator,
)
from sba_resolve.core.services.day_detector import DayDetector
from sba_resolve.core.services.planning_segment_builder import (
    PlanningSegmentBuilder,
)
from sba_resolve.core.services.timeline_sorter import TimelineSorter


class TimelinePlanningService:
    """
    Coordinates the Ride Reconstruction pipeline.
    """

    def __init__(
        self,
        timeline_sorter: TimelineSorter | None = None,
        day_detector: DayDetector | None = None,
        camera_allocator: CameraTrackAllocator | None = None,
        segment_builder: PlanningSegmentBuilder | None = None,
    ) -> None:

        self.timeline_sorter = timeline_sorter or TimelineSorter()
        self.day_detector = day_detector or DayDetector()
        self.camera_allocator = (
            camera_allocator or CameraTrackAllocator()
        )
        self.segment_builder = (
            segment_builder or PlanningSegmentBuilder()
        )

    def plan(self, media_library) -> TimelinePlan:
        """
        Execute the first stage of Ride Reconstruction.
        """

        if media_library is None:
            raise ValueError("media_library cannot be None")

        # Future:
        # Project Validation Engine
        # Validate source media before planning.

        # Get MediaFiles from the MediaLibrary
        media_files = list(media_library.media_files)

        # Chronological ordering
        sorted_media = self.timeline_sorter.sort(media_files)

        # Build planning segments
        segments = self.segment_builder.build(sorted_media)

        # Create the output plan
        plan = TimelinePlan()

        # Placeholder until TimelinePlan is extended
        # in later ML-011 slices.
        plan.planning_segments = segments

        return plan