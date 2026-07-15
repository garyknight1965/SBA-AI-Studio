"""
============================================================
SBA AI Studio
Timeline Marker Generator
ML-011-018
Version : 2.0.0 Alpha
============================================================

Generates TimelineMarker objects for a reconstructed ride:
one marker at the start of each ride day, one at the start of
each detected Scene, and one at the start of each detected
multicam window.

Version 2.0 (ML-020) adds general same-frame merging. Resolve
only accepts one marker per exact frame - whenever two or more
generated markers land on the same frame (e.g. a day's first
Scene always starts on the same frame as that day's Ride Day
marker; a Scene and a Multicam window can also coincide), they
are merged into a single marker instead of silently colliding
(only one would reach Resolve, and create_timeline() would
report the other as a failed AddMarker() call).

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

    SCENE_COLOUR = "Yellow"

    MULTICAM_COLOUR = "Purple"

    # When markers collide on the same frame, the lowest-priority
    # number wins the merged marker's colour/category. Anything
    # not listed (shouldn't happen) sorts last.
    CATEGORY_PRIORITY = {
        "Ride Day": 0,
        "Multicam": 1,
        "Scene": 2,
    }

    def generate(
        self,
        placements: Iterable[TimelinePlacement],
        multicam_candidates: Iterable[MulticamCandidate],
    ) -> list[TimelineMarker]:

        placements = list(placements)
        multicam_candidates = list(multicam_candidates)

        markers: list[TimelineMarker] = []

        markers.extend(self._ride_day_markers(placements))
        markers.extend(self._scene_markers(placements))
        markers.extend(self._multicam_markers(multicam_candidates))

        markers = self._merge_by_frame(markers)

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
    def _scene_markers(
        placements: list[TimelinePlacement],
    ) -> list[TimelineMarker]:

        earliest_frame_by_scene: dict[tuple[int, int], int] = {}

        for placement in placements:

            key = (placement.ride_day, placement.scene)

            current = earliest_frame_by_scene.get(key)

            if current is None or placement.record_frame < current:
                earliest_frame_by_scene[key] = placement.record_frame

        markers = []

        for (ride_day, scene), frame in sorted(
            earliest_frame_by_scene.items()
        ):

            # Scene 1 of every day lands on the exact same frame as
            # that day's Ride Day marker (it's the first clip of
            # the day, by construction) - this is a GUARANTEED,
            # redundant collision, not a genuine one, so it's
            # skipped here rather than left for _merge_by_frame()
            # to absorb. (Genuine collisions - e.g. a Multicam
            # window that happens to start at a Ride Day's first
            # frame - are real information and DO get merged
            # below, not skipped.)
            if scene == 1:
                continue

            markers.append(
                TimelineMarker(
                    frame=frame,
                    title=f"Day {ride_day} - Scene {scene}",
                    description="",
                    colour=TimelineMarkerGenerator.SCENE_COLOUR,
                    category="Scene",
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

    @classmethod
    def _merge_by_frame(
        cls,
        markers: list[TimelineMarker],
    ) -> list[TimelineMarker]:
        """
        Resolve only accepts one marker per exact frame. Merge
        any markers sharing a frame into a single TimelineMarker
        instead of leaving a silent collision for create_timeline()
        to discover at AddMarker() time.

        The merged marker's colour/category comes from whichever
        collided marker has the highest priority (Ride Day >
        Multicam > Scene). Titles are combined (deduplicated,
        order-preserving) so nothing is silently lost from a
        merge; descriptions are combined the same way, skipping
        any that are empty.
        """

        by_frame: dict[int, list[TimelineMarker]] = {}

        for marker in markers:
            by_frame.setdefault(marker.frame, []).append(marker)

        merged: list[TimelineMarker] = []

        for frame, group in by_frame.items():

            if len(group) == 1:
                merged.append(group[0])
                continue

            group = sorted(
                group,
                key=lambda m: cls.CATEGORY_PRIORITY.get(m.category, 99),
            )

            primary = group[0]

            # Combine every colliding marker's title (deduplicated,
            # order-preserving) rather than keeping only the
            # highest-priority one - nothing should be silently
            # lost from a merge (e.g. a Multicam marker colliding
            # with a Ride Day marker must still visibly say
            # "Multicam" somewhere in the merged title).
            combined_title = " / ".join(
                dict.fromkeys(m.title for m in group)
            )

            combined_description = " | ".join(
                m.description for m in group if m.description
            )

            merged.append(
                TimelineMarker(
                    frame=frame,
                    title=combined_title,
                    description=combined_description,
                    colour=primary.colour,
                    category=primary.category,
                    generated=True,
                )
            )

        return merged
