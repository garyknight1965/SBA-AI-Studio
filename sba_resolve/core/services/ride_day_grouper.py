"""
============================================================
SBA AI Studio
Ride Day Grouper
Version : 1.0.0
============================================================

Groups a project-wide PlanningResult's placements, markers, and
unsynced clips into one RideDayTimelinePlan per ride day, with
frame numbers rebased relative to each day's own earliest clip.

PlanningResult itself stays project-wide and unchanged (record_frame
values there remain real elapsed time since the whole project's
first clip) - that project-wide view is still correct and useful for
multicam detection, statistics, and anything else operating across
the whole project.

This service exists so the Resolve Builder boundary
(sba_resolve/commands/create_timeline.py) can build one independent
Resolve timeline per ride day instead of one flat project-wide
timeline, each starting at (or near) frame 0, without changing any
Planning Engine frame math.

Resolve-independent: pure data transformation, no Resolve API calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sba_resolve.core.models.planning_result import PlanningResult
from sba_resolve.core.models.timeline_marker import TimelineMarker
from sba_resolve.core.models.timeline_placement import TimelinePlacement
from sba_resolve.core.models.unsynced_clip import UnsyncedClip


@dataclass(slots=True)
class RideDayTimelinePlan:
    """
    Everything needed to build ONE Resolve timeline for ONE ride
    day.

    record_frame values on `placements` and `markers` here are
    already rebased relative to this day's own earliest clip -
    frame 0 is (at or near) this day's first clip, not the whole
    project's.
    """

    ride_day: int

    date_label: str = ""

    placements: list[TimelinePlacement] = field(default_factory=list)

    markers: list[TimelineMarker] = field(default_factory=list)

    unsynced_clips: list[UnsyncedClip] = field(default_factory=list)

    @property
    def timeline_name_suffix(self) -> str:
        """
        e.g. "Day 1 - 2026-07-12", or "Day 1" if no clip in this
        day had a known creation time to derive a date from.
        """

        if self.date_label:
            return f"Day {self.ride_day} - {self.date_label}"

        return f"Day {self.ride_day}"


class RideDayGrouper:
    """
    Splits a project-wide PlanningResult into one
    RideDayTimelinePlan per ride day.
    """

    @classmethod
    def group(cls, result: PlanningResult) -> list[RideDayTimelinePlan]:

        ride_days = sorted(
            {placement.ride_day for placement in result.placements}
        )

        plans = []

        for ride_day in ride_days:

            day_placements = [
                placement
                for placement in result.placements
                if placement.ride_day == ride_day
            ]

            day_markers = [
                marker
                for marker in result.markers
                if marker.ride_day == ride_day
            ]

            day_unsynced = [
                clip
                for clip in result.unsynced_clips
                if clip.ride_day == ride_day
            ]

            offset = min(
                placement.record_frame for placement in day_placements
            )

            plans.append(
                RideDayTimelinePlan(
                    ride_day=ride_day,
                    date_label=cls._date_label(day_placements),
                    placements=[
                        cls._rebase_placement(placement, offset)
                        for placement in day_placements
                    ],
                    markers=[
                        cls._rebase_marker(marker, offset)
                        for marker in day_markers
                    ],
                    unsynced_clips=day_unsynced,
                )
            )

        return plans

    @staticmethod
    def _rebase_placement(
        placement: TimelinePlacement,
        offset: int,
    ) -> TimelinePlacement:

        return TimelinePlacement(
            media_file=placement.media_file,
            ride_day=placement.ride_day,
            scene=placement.scene,
            track_index=placement.track_index,
            record_frame=max(0, placement.record_frame - offset),
            duration_frames=placement.duration_frames,
            camera_name=placement.camera_name,
            clip_name=placement.clip_name,
        )

    @staticmethod
    def _rebase_marker(
        marker: TimelineMarker,
        offset: int,
    ) -> TimelineMarker:

        return TimelineMarker(
            frame=max(0, marker.frame - offset),
            title=marker.title,
            description=marker.description,
            colour=marker.colour,
            category=marker.category,
            generated=marker.generated,
            ride_day=marker.ride_day,
        )

    @staticmethod
    def _date_label(placements: list[TimelinePlacement]) -> str:
        """
        Derive a YYYY-MM-DD label for this day from its earliest
        clip's creation time. Returns "" if no clip in this day
        has a known creation time.
        """

        created_times = [
            placement.media_file.created
            for placement in placements
            if getattr(placement.media_file, "created", None)
            is not None
        ]

        if not created_times:
            return ""

        return min(created_times).strftime("%Y-%m-%d")
