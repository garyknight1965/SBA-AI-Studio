"""
============================================================
SBA AI Studio
Planning Result
ML-011-010
Version : 1.1.0
============================================================

Represents the complete output of the Planning Engine.

This object bridges the Planning Engine and the Resolve
Timeline Builder.

Version 1.1.0 (ML-054 Step 2b) adds unsynced_clips - clips that
were part of a detected multicam candidate but could not be
verified via audio sync, and were therefore excluded from
placements entirely rather than guessed onto the timeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sba_resolve.core.models.multicam_candidate import MulticamCandidate
from sba_resolve.core.models.planning_segment import PlanningSegment
from sba_resolve.core.models.planning_statistics import PlanningStatistics
from sba_resolve.core.models.timeline_marker import TimelineMarker
from sba_resolve.core.models.timeline_placement import TimelinePlacement
from sba_resolve.core.models.timeline_plan import TimelinePlan
from sba_resolve.core.models.unsynced_clip import UnsyncedClip


@dataclass(slots=True)
class PlanningResult:
    """
    Complete Planning Engine output.
    """

    timeline_plan: TimelinePlan = field(default_factory=TimelinePlan)

    segments: list[PlanningSegment] = field(default_factory=list)

    placements: list[TimelinePlacement] = field(default_factory=list)

    markers: list[TimelineMarker] = field(default_factory=list)

    multicam_candidates: list[MulticamCandidate] = field(default_factory=list)

    unsynced_clips: list[UnsyncedClip] = field(default_factory=list)

    statistics: PlanningStatistics = field(
        default_factory=PlanningStatistics
    )

    @property
    def has_segments(self) -> bool:
        return bool(self.segments)

    @property
    def has_multicam(self) -> bool:
        return bool(self.multicam_candidates)

    @property
    def has_unsynced_clips(self) -> bool:
        return bool(self.unsynced_clips)

    def summary(self) -> dict:
        return {
            "segments": len(self.segments),
            "placements": len(self.placements),
            "markers": len(self.markers),
            "multicam_candidates": len(self.multicam_candidates),
            "unsynced_clips": len(self.unsynced_clips),
            "timeline_days": self.timeline_plan.total_days,
            "timeline_tracks": self.timeline_plan.total_tracks,
            "timeline_clips": self.timeline_plan.total_clips,
        }