from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from sba_resolve.core.models.ride_day import RideDay


class DayDetector:
    """
    Groups chronologically sorted media clips into RideDay objects.

    A new RideDay begins whenever the time gap between two consecutive
    clips exceeds the configured maximum gap.
    """

    DEFAULT_MAX_GAP = timedelta(hours=4)

    def __init__(self, max_gap: timedelta | None = None):
        self.max_gap = max_gap or self.DEFAULT_MAX_GAP

    def detect(self, media_files: Iterable):
        media = [
            m for m in media_files
            if getattr(m, "created", None) is not None
        ]

        if not media:
            return []

        media.sort(key=lambda m: m.created)

        ride_days = []

        current_clips = [media[0]]
        current_start = media[0].created
        previous_time = media[0].created

        day_index = 1

        for clip in media[1:]:
            gap = clip.created - previous_time

            if gap > self.max_gap:
                ride_days.append(
                    RideDay(
                        index=day_index,
                        start_time=current_start,
                        end_time=previous_time,
                        clips=current_clips,
                    )
                )

                day_index += 1
                current_clips = [clip]
                current_start = clip.created
            else:
                current_clips.append(clip)

            previous_time = clip.created

        ride_days.append(
            RideDay(
                index=day_index,
                start_time=current_start,
                end_time=previous_time,
                clips=current_clips,
            )
        )

        return ride_days