"""
============================================================
SBA AI Studio
Recording Session Report Builder Regression Test
ML-031
Version : 1.0.0
============================================================

Verifies RecordingSessionReportBuilder's interval-decomposition
sweep:

- A period where two cameras overlap becomes a single "both
  cameras" session, not two overlapping ones.
- Sessions before/after an overlap correctly show just the one
  active camera.
- A gap where NOTHING is recording produces no session at all
  (not an empty-camera-set entry).
- Multiple ride days are decomposed independently.
- format_session_line() renders the expected "HH:MM-HH:MM
  Cameras" text.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest


class RecordingSessionReportBuilderRegressionTest(BaseRegressionTest):

    name = "Recording Session Report Builder (ML-031)"

    category = "Planning"

    description = (
        "Verify the recording-session interval decomposition "
        "correctly merges overlapping camera activity and "
        "leaves genuine gaps unlisted."
    )

    def _make_placement(
        self, clip_name, ride_day, camera_name, created, duration_seconds
    ):

        from sba_resolve.core.models.media_file import MediaFile
        from sba_resolve.core.models.timeline_placement import (
            TimelinePlacement,
        )

        media = MediaFile(
            filename=clip_name,
            full_path=Path(f"/fake/{clip_name}"),
            relative_path=Path(clip_name),
            extension=".mp4",
            size=1024,
            created=created,
            duration=str(duration_seconds),
        )

        placement = TimelinePlacement(media_file=media)
        placement.ride_day = ride_day
        placement.camera_name = camera_name
        placement.clip_name = clip_name

        return placement

    def run(self) -> None:

        from sba_resolve.core.models.planning_result import PlanningResult
        from sba_resolve.core.services.recording_session_report_builder import (
            RecordingSessionReportBuilder,
        )

        day = datetime(2026, 5, 12)

        def t(hour, minute):
            return day.replace(hour=hour, minute=minute)

        placements = [
            self._make_placement(
                "helmet1.mp4", 1, "Helmet", t(9, 15),
                duration_seconds=5 * 60,  # 09:15-09:20
            ),
            self._make_placement(
                "insta1.mp4", 1, "Insta360", t(9, 20),
                duration_seconds=23 * 60,  # 09:20-09:43
            ),
            self._make_placement(
                "helmet1b.mp4", 1, "Helmet", t(9, 15),
                duration_seconds=28 * 60,  # 09:15-09:43 (overlaps insta1)
            ),
            self._make_placement(
                "helmet2.mp4", 1, "Helmet", t(10, 5),
                duration_seconds=23 * 60,  # 10:05-10:28
            ),
            self._make_placement(
                "insta2.mp4", 1, "Insta360", t(10, 5),
                duration_seconds=15 * 60,  # 10:05-10:20
            ),
            # Day 2: a single, independent camera run.
            self._make_placement(
                "day2clip.mp4", 2, "Helmet", t(14, 0),
                duration_seconds=10 * 60,
            ),
        ]

        result = PlanningResult(placements=placements)

        report = RecordingSessionReportBuilder().build(result)

        if len(report["days"]) != 2:
            raise RuntimeError(
                f"Expected 2 days, got {len(report['days'])}."
            )

        day1 = report["days"][0]
        day2 = report["days"][1]

        if day1["ride_day"] != 1 or day2["ride_day"] != 2:
            raise RuntimeError("Days out of order or mislabeled.")

        sessions = day1["sessions"]

        if len(sessions) != 4:
            raise RuntimeError(
                f"Expected 4 sessions for day 1, got "
                f"{len(sessions)}: {sessions}"
            )

        s1, s2, s3, s4 = sessions

        if s1["cameras"] != ["Helmet"]:
            raise RuntimeError(
                f"Expected session 1 to be Helmet-only, got "
                f"{s1['cameras']!r}."
            )

        if s1["start_time"] != t(9, 15) or s1["end_time"] != t(9, 20):
            raise RuntimeError(
                f"Expected session 1 to span 09:15-09:20, got "
                f"{s1['start_time']}-{s1['end_time']}."
            )

        if s2["cameras"] != ["Helmet", "Insta360"]:
            raise RuntimeError(
                f"Expected session 2 to be Helmet+Insta360 "
                f"(merged overlap, not two separate entries), "
                f"got {s2['cameras']!r}."
            )

        if s2["start_time"] != t(9, 20) or s2["end_time"] != t(9, 43):
            raise RuntimeError(
                f"Expected session 2 to span 09:20-09:43, got "
                f"{s2['start_time']}-{s2['end_time']}."
            )

        for session in sessions:
            if session["start_time"] == t(9, 43):
                raise RuntimeError(
                    "The genuine recording gap (09:43-10:05) "
                    "should not produce a session entry at all."
                )

        if s3["cameras"] != ["Helmet", "Insta360"]:
            raise RuntimeError(
                f"Expected session 3 to be Helmet+Insta360, got "
                f"{s3['cameras']!r}."
            )

        if s3["start_time"] != t(10, 5) or s3["end_time"] != t(10, 20):
            raise RuntimeError(
                f"Expected session 3 to span 10:05-10:20, got "
                f"{s3['start_time']}-{s3['end_time']}."
            )

        if s4["cameras"] != ["Helmet"]:
            raise RuntimeError(
                f"Expected session 4 to be Helmet-only, got "
                f"{s4['cameras']!r}."
            )

        if s4["start_time"] != t(10, 20) or s4["end_time"] != t(10, 28):
            raise RuntimeError(
                f"Expected session 4 to span 10:20-10:28, got "
                f"{s4['start_time']}-{s4['end_time']}."
            )

        if len(day2["sessions"]) != 1:
            raise RuntimeError(
                f"Expected 1 session for day 2, got "
                f"{len(day2['sessions'])}."
            )

        rendered = RecordingSessionReportBuilder.format_session_line(s2)

        if rendered != "09:20-09:43  Helmet, Insta360":
            raise RuntimeError(
                f"Unexpected rendered session line: {rendered!r}"
            )
