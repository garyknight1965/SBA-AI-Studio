"""
============================================================
SBA AI Studio
Recording Session Report Builder
ML-031-002
Version : 1.0.0 Alpha
============================================================

Decomposes each Ride Day into "recording sessions" - maximal
real-world time intervals where the SET of actively-recording
cameras stays constant. This directly answers "which cameras
were rolling together, and when":

    09:15-09:43   GoPro HERO13 Black, Insta360 X3
    09:44-10:02   GoPro HERO13 Black
    10:05-10:28   GoPro HERO13 Black, Insta360 X3
    10:31-10:40   Insta360 X3

This is the foundation for camera-group / multicam sync
suggestions - understanding the recording SESSIONS, not just
pairwise clip overlaps.

Algorithm: a standard interval-decomposition sweep. Every clip
contributes a "camera starts recording" event at its capture
start and a "camera stops recording" event at its capture end.
Walking through all UNIQUE event timestamps in order, the active
camera set between consecutive timestamps is exactly whatever it
was after processing all events at the earlier timestamp - this
naturally handles multiple cameras starting/stopping at the same
instant without double-counting.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable


class RecordingSessionReportBuilder:
    """
    Builds a per-Ride-Day recording session breakdown from a
    PlanningResult.
    """

    def build(self, result) -> dict:
        """
        Returns:

            {
                "days": [
                    {
                        "ride_day": 1,
                        "sessions": [
                            {
                                "start_time": datetime,
                                "end_time": datetime,
                                "cameras": ["GoPro HERO13 Black", ...],
                            },
                            ...
                        ],
                    },
                    ...
                ],
            }
        """

        clips_by_day: dict[int, list[tuple[str, datetime, datetime]]] = (
            defaultdict(list)
        )

        for placement in result.placements:

            media = placement.media_file

            start = getattr(media, "created", None)

            if start is None:
                continue

            duration_seconds = self._duration_seconds(media)

            end = (
                start + timedelta(seconds=duration_seconds)
                if duration_seconds > 0
                else start
            )

            camera = (
                placement.camera_name
                or getattr(media, "camera_display_name", None)
                or "Unknown"
            )

            clips_by_day[placement.ride_day].append((camera, start, end))

        days = [
            {
                "ride_day": ride_day,
                "sessions": self._decompose(clips_by_day[ride_day]),
            }
            for ride_day in sorted(clips_by_day)
        ]

        return {"days": days}

    @staticmethod
    def _duration_seconds(media) -> float:

        raw = getattr(media, "duration", "")

        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _decompose(
        cls,
        clips: Iterable[tuple[str, datetime, datetime]],
    ) -> list[dict]:

        events_by_time: dict[datetime, list[tuple[str, int]]] = (
            defaultdict(list)
        )

        for camera, start, end in clips:

            if end <= start:
                continue

            events_by_time[start].append((camera, 1))
            events_by_time[end].append((camera, -1))

        if not events_by_time:
            return []

        times = sorted(events_by_time)

        active_count: dict[str, int] = defaultdict(int)

        sessions = []

        for index, time in enumerate(times):

            for camera, delta in events_by_time[time]:

                active_count[camera] += delta

                if active_count[camera] <= 0:
                    del active_count[camera]

            if index + 1 < len(times):

                next_time = times[index + 1]

                cameras = sorted(active_count)

                if cameras:
                    sessions.append(
                        {
                            "start_time": time,
                            "end_time": next_time,
                            "cameras": cameras,
                        }
                    )

        return sessions

    @staticmethod
    def format_session_line(session: dict) -> str:
        """
        Renders one session as "HH:MM-HH:MM  Camera A, Camera B".
        """

        start_text = session["start_time"].strftime("%H:%M")
        end_text = session["end_time"].strftime("%H:%M")

        return (
            f"{start_text}-{end_text}  "
            f"{', '.join(session['cameras'])}"
        )
