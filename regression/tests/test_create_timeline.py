"""
============================================================
SBA AI Studio
Create Timeline Regression Test
RES-006F.2
Version : 1.0.0
============================================================

Verifies sba_resolve.commands.create_timeline.create_timeline()
against fake Resolve API objects (real DaVinciResolveScript is
only available inside Resolve's own Python console, so this
test stands in the same call surface: GetTimelineCount,
GetTimelineByIndex, CreateEmptyTimeline, SetCurrentTimeline,
GetTrackCount, AddTrack, SetTrackName, AppendToTimeline).

This does not prove Resolve itself behaves this way (that was
confirmed separately via tools/resolve_gap_placement_test.py) -
it proves create_timeline()'s own wiring logic (track creation,
camera-based naming, filename matching, skip handling) is
correct.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class FakeClip:

    def __init__(self, filename):
        self.filename = filename

    def GetClipProperty(self):
        return {"File Name": self.filename}

    def GetName(self):
        return self.filename


class FakeTimeline:

    def __init__(self, name, timeline_fps="24"):
        self.name = name
        self.track_counts = {"video": 1}
        self.track_names = {}
        self.markers = {}
        self.timeline_fps = timeline_fps

    def GetName(self):
        return self.name

    def GetTrackCount(self, track_type):
        return self.track_counts.get(track_type, 0)

    def AddTrack(self, track_type):
        self.track_counts[track_type] = (
            self.track_counts.get(track_type, 0) + 1
        )
        return True

    def SetTrackName(self, track_type, index, name):
        self.track_names[(track_type, index)] = name
        return True

    def AddMarker(self, frame_id, color, name, note, duration, custom_data=None):
        if frame_id in self.markers:
            return False
        self.markers[frame_id] = {
            "color": color,
            "name": name,
            "note": note,
            "duration": duration,
            "customData": custom_data or "",
        }
        return True

    def GetSetting(self, key):
        if key == "timelineFrameRate":
            return self.timeline_fps
        return None


class FakeProject:

    def __init__(self):
        self.timelines = []
        self.current_timeline = None

    def GetTimelineCount(self):
        return len(self.timelines)

    def GetTimelineByIndex(self, index):
        return self.timelines[index - 1]

    def SetCurrentTimeline(self, timeline):
        self.current_timeline = timeline


class FakeMediaPool:

    def __init__(self):
        self.append_calls = []

    def CreateEmptyTimeline(self, name):
        timeline = FakeTimeline(name)
        return timeline

    def AppendToTimeline(self, items):
        self.append_calls.append(items)
        return True


class FakeContext:

    def __init__(self, project, media_pool, project_data, imported_items):
        self.project = project
        self.media_pool = media_pool
        self.project_data = project_data
        self.imported_items = imported_items


class CreateTimelineRegressionTest(BaseRegressionTest):

    name = "Create Timeline (RES-006F.2)"

    category = "Resolve"

    description = (
        "Verify create_timeline() builds correct per-camera "
        "tracks and gap-preserving placements from a "
        "PlanningResult, against fake Resolve API objects."
    )

    def _make_media(self, filename, camera_model, created, duration_seconds, fps=29.97):

        from sba_resolve.core.models.camera_profile import (
            CameraManufacturer,
            CameraProfile,
            CameraType,
        )
        from sba_resolve.core.models.media_file import MediaFile

        profile = CameraProfile(
            manufacturer=CameraManufacturer.GOPRO,
            model=camera_model,
            family="Hero",
            camera_type=CameraType.ACTION,
            confidence=100,
            detection_method="Test Fixture",
        )

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            camera_model=camera_model,
            camera_profile=profile,
            created=created,
            duration=str(duration_seconds),
            fps=fps,
        )

    def run(self) -> None:

        from sba_resolve.commands.create_timeline import create_timeline

        day1_start = datetime(2026, 7, 1, 9, 0, 0)

        media_objects = [
            self._make_media(
                "hero13_0001.mp4", "HERO13 Black", day1_start, 60
            ),
            self._make_media(
                "hero13_0002.mp4",
                "HERO13 Black",
                day1_start + timedelta(seconds=61),
                30,
            ),
            self._make_media(
                "hero8_0001.mp4",
                "HERO8 Black",
                day1_start + timedelta(seconds=95),
                45,
            ),
        ]

        # Simulate import_media() having skipped one clip (e.g. a
        # missing file) by only including 2 of the 3 as "imported".
        imported_items = [
            FakeClip("hero13_0001.mp4"),
            FakeClip("hero8_0001.mp4"),
        ]

        project = FakeProject()
        media_pool = FakeMediaPool()

        context = FakeContext(
            project=project,
            media_pool=media_pool,
            project_data={
                "project_name": "Test Project",
                "timeline_name": "Test Project Master",
                "media_objects": media_objects,
            },
            imported_items=imported_items,
        )

        timeline = create_timeline(context)

        if timeline is None:
            raise RuntimeError("create_timeline() returned None.")

        if project.current_timeline is not timeline:
            raise RuntimeError(
                "Timeline was not set as the project's current "
                "timeline."
            )

        # Exactly one AppendToTimeline batch call expected.
        if len(media_pool.append_calls) != 1:
            raise RuntimeError(
                f"Expected 1 AppendToTimeline call, got "
                f"{len(media_pool.append_calls)}."
            )

        items = media_pool.append_calls[0]

        # Only 2 of the 3 planned clips had a matching imported
        # item (hero13_0002.mp4 was "skipped" at import time).
        if len(items) != 2:
            raise RuntimeError(
                f"Expected 2 append items (1 clip unmatched), "
                f"got {len(items)}."
            )

        # Hero13 and Hero8 must be on different tracks.
        track_indexes = {item["trackIndex"] for item in items}

        if len(track_indexes) != 2:
            raise RuntimeError(
                "Expected clips on 2 different tracks, got "
                f"{len(track_indexes)}."
            )

        # Enough video tracks must have been created.
        if timeline.GetTrackCount("video") < max(track_indexes):
            raise RuntimeError(
                "Not enough video tracks were created for the "
                "highest track_index used."
            )

        # Tracks must be named after their camera.
        named_tracks = {
            name for name in timeline.track_names.values()
        }

        if not any("HERO13" in name for name in named_tracks):
            raise RuntimeError(
                "No track was named for the Hero13 camera."
            )

        if not any("HERO8" in name for name in named_tracks):
            raise RuntimeError(
                "No track was named for the Hero8 camera."
            )

        # recordFrame and duration must be computed using the
        # TIMELINE's fps (24, per FakeTimeline.timeline_fps), NOT
        # the clip's own native fps (29.97, per _make_media's
        # default) and NOT the old hardcoded 25fps default.
        hero8_items = [
            item for item in items
            if item["mediaPoolItem"].filename == "hero8_0001.mp4"
        ]

        if not hero8_items:
            raise RuntimeError("Hero8 clip missing from append items.")

        timeline_fps = 24.0

        expected_frame = round(95 * timeline_fps)

        if hero8_items[0]["recordFrame"] != expected_frame:
            raise RuntimeError(
                f"Expected Hero8 recordFrame {expected_frame} "
                f"(95s at the timeline's 24fps), got "
                f"{hero8_items[0]['recordFrame']}. recordFrame "
                f"must use the real timeline fps, not the clip's "
                f"native fps or a hardcoded default."
            )

        # This fixture has no camera overlap, so only the Ride Day
        # 1 marker should have been written (at frame 0).
        if len(timeline.markers) != 1:
            raise RuntimeError(
                f"Expected 1 marker written to the timeline, got "
                f"{len(timeline.markers)}."
            )

        if 0 not in timeline.markers:
            raise RuntimeError(
                "Expected a marker at frame 0 (Ride Day 1)."
            )

        if timeline.markers[0]["name"] != "Ride Day 1":
            raise RuntimeError(
                f"Expected marker at frame 0 named 'Ride Day 1', "
                f"got {timeline.markers[0]['name']!r}."
            )
