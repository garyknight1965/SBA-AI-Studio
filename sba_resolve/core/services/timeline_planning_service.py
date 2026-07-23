"""
============================================================
SBA AI Studio
Timeline Planning Service
ML-011-009
Version : 2.3.0
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
    MulticamDetector
        ↓
    HERO13-only restriction OR MulticamAudioSyncService
        ↓
    PlanningResult

No Resolve API code lives here. This service determines *what*
should happen; the Resolve Timeline Builder later decides *how*
to execute it.

Version 2.1.0 (ML-054 Step 2b) added an audio sync verification
pass over every detected multicam candidate.

Version 2.2.0 added enable_multicam_audio_sync (default False) -
when off, MulticamAudioSyncService.mark_all_unsynced() ran
instead of evaluate(), but this was still scoped only to clips
inside a detected multicam candidate - a standalone, non-
overlapping clip from any camera still placed normally,
unaffected either way.

Version 2.3.0 (2026-07-19) replaces that default-off behaviour
with a stricter, project-wide rule, per Gary's real-world
testing: when enable_multicam_audio_sync is False (the default),
ONLY GoPro HERO13 Black clips ever auto-place on the timeline -
every clip from every other camera goes to a placeholder track,
whether or not it overlaps with anything. This applies to EVERY
placement, not just multicam-candidate members. The one
exception is Insta360 paired dual-lens views (ML-015,
Insta360ViewAssigner) - same physical camera, same moment by
construction, a separate pre-existing feature unrelated to
cross-camera audio sync - which stay exempt and continue
auto-placing on their own tracks exactly as before. Enabling
enable_multicam_audio_sync reverts to the previous, more
surgical candidate-scoped evaluate() behaviour (real audio
correlation attempted per overlapping group, HERO13 as the
audio-correlation reference rather than an absolute placement
restriction).
"""

from __future__ import annotations

from sba_resolve.core.models.gap_compression_settings import (
    GapCompressionSettings,
)
from sba_resolve.core.models.planning_result import PlanningResult
from sba_resolve.core.models.planning_statistics import PlanningStatistics
from sba_resolve.core.models.unsynced_clip import UnsyncedClip
from sba_resolve.core.services.day_detector import DayDetector
from sba_resolve.core.services.gap_compressor import GapCompressor
from sba_resolve.core.services.multicam_audio_sync_service import (
    MulticamAudioSyncService,
)
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

    # The only camera that auto-places when
    # enable_multicam_audio_sync is False (the default). Matches
    # the first entry of MulticamAudioSyncService's
    # DEFAULT_CAMERA_ORDER - GoPro HERO13 Black is Gary's trusted
    # lav-mic anchor camera.
    TRUSTED_ANCHOR_CAMERA = "GoPro HERO13 Black"

    def __init__(
        self,
        timeline_sorter: TimelineSorter | None = None,
        day_detector: DayDetector | None = None,
        scene_detector: SceneDetector | None = None,
        segment_builder: PlanningSegmentBuilder | None = None,
        placement_builder: TimelinePlacementBuilder | None = None,
        multicam_detector: MulticamDetector | None = None,
        multicam_audio_sync_service: MulticamAudioSyncService | None = None,
        marker_generator: TimelineMarkerGenerator | None = None,
        fps: float | None = None,
        gap_compression: GapCompressionSettings | None = None,
        enable_multicam_audio_sync: bool = False,
    ) -> None:

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
        self.multicam_audio_sync_service = (
            multicam_audio_sync_service or MulticamAudioSyncService()
        )
        self.marker_generator = (
            marker_generator or TimelineMarkerGenerator()
        )

        # OFF by default (2026-07-19) - when off, only
        # TRUSTED_ANCHOR_CAMERA auto-places (see
        # _restrict_to_hero13_only). Caller (create_timeline.py)
        # reads this from config/settings.json via
        # load_multicam_audio_sync_enabled() and passes it in.
        self.enable_multicam_audio_sync = enable_multicam_audio_sync

        self.gap_compressor = GapCompressor(gap_compression)

    def plan(self, media_library) -> PlanningResult:
        """
        Execute Ride Reconstruction and return the complete
        Planning Engine output.
        """

        if media_library is None:
            raise ValueError("media_library cannot be None")

        media_files = list(media_library)

        sorted_media = self.timeline_sorter.sort(media_files)

        ride_days = self.day_detector.detect(sorted_media)

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

        gap_map = self.gap_compressor.build_map(sorted_media)

        placements = self.placement_builder.build(segments, gap_map)

        multicam_candidates = self.multicam_detector.detect(
            placements, gap_map
        )

        # ML-054 v2.3.0: when audio sync is enabled, use the
        # original candidate-scoped correlation-attempt logic.
        # When disabled (the default), apply the stricter,
        # project-wide "only HERO13 auto-places" rule instead -
        # this now examines EVERY placement, not just clips
        # inside a detected multicam candidate.
        if self.enable_multicam_audio_sync:
            sync_results = self.multicam_audio_sync_service.evaluate(
                multicam_candidates,
                placements,
                fps=self.multicam_detector.fps,
            )
            placements, unsynced_clips = self._apply_sync_results(
                placements, sync_results
            )
        else:
            placements, unsynced_clips = self._restrict_to_hero13_only(
                placements,
                multicam_candidates,
                self.multicam_audio_sync_service,
            )

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

        markers = self.marker_generator.generate(
            placements,
            multicam_candidates,
        )

        statistics = self._build_statistics(
            ride_days=ride_days,
            scenes=scenes,
            sorted_media=sorted_media,
            segments=segments,
            placements=placements,
            markers=markers,
        )

        return PlanningResult(
            segments=segments,
            placements=placements,
            markers=markers,
            multicam_candidates=multicam_candidates,
            unsynced_clips=unsynced_clips,
            statistics=statistics,
        )

    @classmethod
    def _restrict_to_hero13_only(
        cls,
        placements,
        multicam_candidates,
        multicam_audio_sync_service: MulticamAudioSyncService,
    ) -> tuple[list, list[UnsyncedClip]]:
        """
        Applied when enable_multicam_audio_sync is False (the
        default, 2026-07-19): ONLY TRUSTED_ANCHOR_CAMERA
        (GoPro HERO13 Black) clips ever auto-place on the
        timeline. Every clip from every other camera is
        converted into an UnsyncedClip, regardless of whether it
        overlaps with anything - a stricter, simpler,
        project-wide rule requested by Gary after real-world
        testing showed standalone (non-overlapping) HERO8/X3
        clips still auto-placing under the previous
        candidate-scoped rule.

        Exception: clips that are part of an already-paired
        Insta360 dual-lens view group (ML-015 - same physical
        camera/moment by construction, unrelated to cross-camera
        audio sync) stay exempt and are still placed
        automatically, exactly as ML-015 has always worked.
        """

        paired_view_clip_ids: set[int] = set()

        for candidate in multicam_candidates:
            clips = list(candidate.clips)
            if multicam_audio_sync_service.is_paired_view_group(clips):
                paired_view_clip_ids.update(id(clip) for clip in clips)

        kept_placements = []
        unsynced_clips: list[UnsyncedClip] = []

        for placement in placements:

            is_trusted_camera = (
                placement.camera_name == cls.TRUSTED_ANCHOR_CAMERA
            )
            is_paired_view = (
                id(placement.media_file) in paired_view_clip_ids
            )

            if is_trusted_camera or is_paired_view:
                kept_placements.append(placement)
                continue

            unsynced_clips.append(
                UnsyncedClip(
                    camera_name=placement.camera_name,
                    clip_name=placement.clip_name,
                    reason=(
                        f"Only {cls.TRUSTED_ANCHOR_CAMERA} auto-places "
                        f"automatically (audio sync disabled) - "
                        f"requires manual placement/sync in Resolve."
                    ),
                    ride_day=placement.ride_day,
                )
            )

        return kept_placements, unsynced_clips

    @staticmethod
    def _apply_sync_results(
        placements,
        sync_results,
    ) -> tuple[list, list[UnsyncedClip]]:
        """
        Splits placements into (kept_placements, unsynced_clips)
        based on the sync_results returned by
        MulticamAudioSyncService.evaluate(). Only used when
        enable_multicam_audio_sync is True.
        """

        if not sync_results:
            return placements, []

        kept_placements = []
        unsynced_clips: list[UnsyncedClip] = []

        for placement in placements:

            result = sync_results.get(id(placement.media_file))

            if result is None:
                kept_placements.append(placement)
                continue

            if result.is_reference or result.synced:
                if result.corrected_record_frame is not None:
                    placement.record_frame = result.corrected_record_frame
                kept_placements.append(placement)
                continue

            unsynced_clips.append(
                UnsyncedClip(
                    camera_name=placement.camera_name,
                    clip_name=placement.clip_name,
                    reason=result.reason,
                    ride_day=placement.ride_day,
                )
            )

        return kept_placements, unsynced_clips

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