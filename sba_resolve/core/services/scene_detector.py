"""
============================================================
SBA AI Studio
Scene Detector
ML-020-002
Version : 1.0.0 Alpha
============================================================

Detects Scene boundaries WITHIN a single Ride Day.

Uses the same gap-based algorithm as DayDetector (a new group
begins whenever the time gap between two consecutive clips
exceeds a threshold), but at a MUCH smaller default threshold.

A Ride Day boundary means "stopped riding for hours" (e.g.
overnight). A Scene boundary means "camera stopped recording for
a few minutes" - almost always because the rider deliberately
turned it off for a real stop (fuel, coffee, a viewpoint), since
continuous riding footage doesn't have gaps of this size.

This detects scene boundaries only, from gap timing. It does
NOT attempt to determine WHAT a scene is (Fuel Stop vs Coffee
Stop vs Mountain Pass) - that requires signals this project
doesn't have yet (GPS, motion/audio analysis). Scenes are
numbered, not named, until a future labelling layer exists.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from sba_resolve.core.models.scene import Scene


class SceneDetector:
    """
    Groups a single Ride Day's chronologically sorted clips into
    Scene objects.
    """

    DEFAULT_MAX_GAP = timedelta(minutes=5)

    def __init__(self, max_gap: timedelta | None = None):
        self.max_gap = max_gap or self.DEFAULT_MAX_GAP

    def detect(
        self,
        ride_day_clips: Iterable,
        ride_day: int = 1,
    ) -> list[Scene]:
        """
        Parameters
        ----------
        ride_day_clips
            Clips belonging to a single RideDay (need not
            already be sorted).
        ride_day
            The RideDay index these clips belong to. Stamped
            onto every resulting Scene.
        """

        media = [
            m for m in ride_day_clips
            if getattr(m, "created", None) is not None
        ]

        if not media:
            return []

        media.sort(key=lambda m: m.created)

        scenes = []

        current_clips = [media[0]]
        current_start = media[0].created
        previous_time = media[0].created

        scene_index = 1

        for clip in media[1:]:
            gap = clip.created - previous_time

            if gap > self.max_gap:
                scenes.append(
                    Scene(
                        ride_day=ride_day,
                        index=scene_index,
                        start_time=current_start,
                        end_time=previous_time,
                        clips=current_clips,
                    )
                )

                scene_index += 1
                current_clips = [clip]
                current_start = clip.created
            else:
                current_clips.append(clip)

            previous_time = clip.created

        scenes.append(
            Scene(
                ride_day=ride_day,
                index=scene_index,
                start_time=current_start,
                end_time=previous_time,
                clips=current_clips,
            )
        )

        return scenes
