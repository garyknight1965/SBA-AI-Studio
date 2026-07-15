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

from sba_resolve.core.models.gap_compression_settings import (
    GapCompressionSettings,
)
from sba_resolve.core.models.planning_result import PlanningResult
from sba_resolve.core.models.planning_statistics import PlanningStatistics
from sba_resolve.core.services.day_detector import DayDetector
from sba_resolve.core.services.gap_compressor import GapCompressor
from sba_resolve.core.services.multicam_detector import MulticamDetector
from sba_resolve.core.services.planning_segment_builder import (
    PlanningSegmentBuilder,
)
from sba_resolve.core.services.scene_detector import SceneDetector
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
        scene_detector: SceneDetector | None = None,
        segment_builder: PlanningSegmentBuilder | None = None,
        placement_builder: TimelinePlacementBuilder | None = None,
        multicam_detector: MulticamDetector | None = None,
        marker_generator: TimelineMarkerGenerator | None = None,
        fps: float | None = None,
        gap_compression: GapCompressionSettings | None = None,
    ) -> None:

        # The real Resolve timeline frame rate, if known at call
        # time (read from Resolve in create_timeline.py). Passed
        # to both the placement builder and multicam detector so
        # they can't disagree with each other. Ignored for any
        # service passed in explicitly (assumed pre-configured).
        self.timeline_sorter = timeline_sorter or TimelineSorter()
        self.day_detector = day_detector or DayDetector()
        self.scene_detector = scene_detector or SceneDetector()
        self.segment_builder = segment_builder or PlanningSegmentBuilder()
        self.placement_builder = (
            placement_builder or TimelinePlacementBuilder(fps=fps)
        )
        self.multicam_detector = (
            multicam_detector or MulticamDetector(fps=fps)
        )
        self.marker_generator = (
            marker_generator or TimelineMarkerGenerator()
        )

        # Gap Compression is off by default (GapCompressionSettings()
        # defaults to enabled=False), which reproduces the original,
        # fully gap-preserving placement behaviour exactly. Built
        # once per plan() call and shared with both the placement
        # builder and the multicam detector so they can't disagree
        # about where "now" falls on the compressed timeline.
        self.gap_compressor = GapCompressor(gap_compression)

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

        # Detect scenes within each ride day (a finer-grained,
        # smaller-threshold version of the same gap-based
        # grouping - a Scene is the smallest editing unit, e.g. a
        # fuel stop or a stretch of riding between stops), then
        # build planning segments one Scene at a time so each
        # segment is stamped with the correct ride_day AND scene
        # index.
        scenes = []

        for ride_day in ride_days:
            scenes.extend(
                self.scene_detector.detect(
                    ride_day.clips,
                    ride_day=ride_day.index,
                )
            )

        segments = []

        for scene in scenes:
            segments.extend(
                self.segment_builder.build(
                    scene.clips,
                    ride_day=scene.ride_day,
                    scene=scene.index,
                )
            )

        # Build the (possibly identity) real-time -> effective-time
        # map ONCE for this plan() call, over every clip involved,
        # so placement and multicam detection can't disagree.
        gap_map = self.gap_compressor.build_map(sorted_media)

        # Determine frame-accurate placements
        placements = self.placement_builder.build(segments, gap_map)

        # Detect real overlapping-camera windows
        multicam_candidates = self.multicam_detector.detect(
            placements, gap_map
        )

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
            scenes=scenes,
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
        scenes,
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
            scenes=len(scenes),
            total_clips=len(sorted_media),
            total_cameras=len(cameras),
            multicam_segments=multicam_segments,
            transcript_segments=transcript_segments,
            timeline_frames=timeline_frames,
            timeline_duration_seconds=timeline_duration_seconds,
            markers=len(markers),
        )
