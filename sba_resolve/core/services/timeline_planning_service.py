"""
============================================================
SBA AI Studio
Timeline Planning Service
ML-011-009
Version : 2.0.0 Alpha
============================================================

Planning Engine orchestrator.

Final ML-011 workflow:

    MediaLibrary
        ↓
    TimelineSorter
        ↓
    DayDetector
        ↓
    RideDay[]
        ↓
    PlanningSegmentBuilder (per RideDay)
        ↓
    PlanningSegment[]
        ↓
    TimelinePlacementBuilder
        ↓
    TimelinePlacement[]
        ↓
    PlanningResult

No Resolve API code lives here. This service determines *what*
should happen; the Resolve Timeline Builder later decides *how*
to execute it.
"""

from __future__ import annotations

from sba_resolve.core.models.planning_result import PlanningResult
from sba_resolve.core.models.planning_statistics import PlanningStatistics
from sba_resolve.core.services.day_detector import DayDetector
from sba_resolve.core.services.multicam_detector import MulticamDetector
from sba_resolve.core.services.planning_segment_builder import (
    PlanningSegmentBuilder,
)
from sba_resolve.core.services.timeline_marker_generator import (
    TimelineMarkerGenerator,
)
from sba_resolve.core.services.timeline_placement_builder import (
    TimelinePlacementBuilder,
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
        segment_builder: PlanningSegmentBuilder | None = None,
        placement_builder: TimelinePlacementBuilder | None = None,
        multicam_detector: MulticamDetector | None = None,
        marker_generator: TimelineMarkerGenerator | None = None,
    ) -> None:

        self.timeline_sorter = timeline_sorter or TimelineSorter()
        self.day_detector = day_detector or DayDetector()
        self.segment_builder = segment_builder or PlanningSegmentBuilder()
        self.placement_builder = (
            placement_builder or TimelinePlacementBuilder()
        )
        self.multicam_detector = multicam_detector or MulticamDetector()
        self.marker_generator = (
            marker_generator or TimelineMarkerGenerator()
        )

    def plan(self, media_library) -> PlanningResult:
        """
        Execute Ride Reconstruction and return the complete
        Planning Engine output.
        """

        if media_library is None:
            raise ValueError("media_library cannot be None")

        # Future:
        # Project Validation Engine
        # Validate source media before planning.

        # Get MediaFiles from the MediaLibrary
        media_files = list(media_library)

        # Chronological ordering
        sorted_media = self.timeline_sorter.sort(media_files)

        # Detect ride days (gap-based grouping)
        ride_days = self.day_detector.detect(sorted_media)

        # Build planning segments, one RideDay at a time so each
        # segment is stamped with the correct ride_day index.
        segments = []

        for ride_day in ride_days:
            segments.extend(
                self.segment_builder.build(
                    ride_day.clips,
                    ride_day=ride_day.index,
                )
            )

        # Determine frame-accurate placements
        placements = self.placement_builder.build(segments)

        # Detect real overlapping-camera windows
        multicam_candidates = self.multicam_detector.detect(placements)

        # Flag segments that participate in a detected multicam
        # window (a segment is single-camera by construction, so
        # this marks it as "part of a synced moment", not that the
        # segment itself has multiple active cameras).
        multicam_clip_ids = {
            id(media)
            for candidate in multicam_candidates
            for media in candidate.clips
        }

        for segment in segments:
            segment.multicam_candidate = any(
                id(media) in multicam_clip_ids
                for media in segment.available_clips
            )

        # Generate ride-day and multicam markers
        markers = self.marker_generator.generate(
            placements,
            multicam_candidates,
        )

        # Assemble statistics
        statistics = self._build_statistics(
            ride_days=ride_days,
            sorted_media=sorted_media,
            segments=segments,
            placements=placements,
            markers=markers,
        )

        # Populate the Planning Engine output.
        # The derived TimelinePlan is populated in a later ML-011
        # slice once the Resolve Timeline Builder consumes this
        # result.
        return PlanningResult(
            segments=segments,
            placements=placements,
            markers=markers,
            multicam_candidates=multicam_candidates,
            statistics=statistics,
        )

    @staticmethod
    def _build_statistics(
        ride_days,
        sorted_media,
        segments,
        placements,
        markers,
    ) -> PlanningStatistics:

        cameras = {
            getattr(media, "camera_display_name", None)
            or getattr(media, "camera_model", None)
            or "Unknown"
            for media in sorted_media
        }

        # A segment is single-camera by construction, so this
        # counts segments flagged as participating in a detected
        # multicam window (see plan()), not segments that
        # themselves have multiple active cameras.
        multicam_segments = sum(
            1 for segment in segments if segment.multicam_candidate
        )

        transcript_segments = sum(
            1 for segment in segments if segment.transcript_available
        )

        timeline_frames = sum(
            placement.duration_frames for placement in placements
        )

        timeline_duration_seconds = 0.0

        for segment in segments:
            for media in segment.available_clips:
                try:
                    timeline_duration_seconds += float(media.duration)
                except (TypeError, ValueError):
                    continue

        return PlanningStatistics(
            ride_days=len(ride_days),
            total_clips=len(sorted_media),
            total_cameras=len(cameras),
            multicam_segments=multicam_segments,
            transcript_segments=transcript_segments,
            timeline_frames=timeline_frames,
            timeline_duration_seconds=timeline_duration_seconds,
            markers=len(markers),
        )
