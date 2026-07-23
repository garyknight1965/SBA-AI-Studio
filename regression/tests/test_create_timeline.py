"""
============================================================
SBA AI Studio
Create Timeline Regression Test
RES-006F.2
Version : 1.1.0
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

Version 1.1.0 (2026-07-19, ML-054 Scope Change #2) adds
"enable_multicam_audio_sync": True to every test's project_data.
The real default is now False, under which ONLY GoPro HERO13
Black auto-places - these three tests all use a HERO8 clip to
exercise Resolve-wiring mechanics (multi-track separation, drop
detection, wrong-position detection) that have nothing to do
with ML-054's camera-eligibility rule, so they explicitly opt
into the richer per-clip placement path via project_data
(create_timeline.py already reads this key before falling back
to config/settings.json) rather than being rewritten around the
new default.
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


def _is_timeline_nesting_call(call):
    """
    True if this AppendToTimeline call is create_timeline()'s
    Master-timeline nesting step (appending a day's Timeline as
    a Media Pool item), rather than a normal per-clip placement
    call.
    """

    return any(
        item["mediaPoolItem"].GetClipProperty().get("Type")
        == "Timeline"
        for item in call
    )


class FakeTimeline:

    def __init__(self, name, timeline_fps="24"):
        self.name = name
        self.track_counts = {"video": 1}
        self.track_names = {}
        self.markers = {}
        self.timeline_fps = timeline_fps
        self.items_by_track: dict[int, list] = {}

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

    def GetItemListInTrack(self, track_type, index):
        if track_type != "video":
            return []
        return self.items_by_track.get(index, [])


class FakeProject:

    def __init__(self, timeline_fps="24"):
        self.timelines = []
        self.current_timeline = None
        self.timeline_fps = timeline_fps

    def GetTimelineCount(self):
        return len(self.timelines)

    def GetTimelineByIndex(self, index):
        return self.timelines[index - 1]

    def SetCurrentTimeline(self, timeline):
        self.current_timeline = timeline

    def GetSetting(self, key):
        if key == "timelineFrameRate":
            return self.timeline_fps
        return None


class FakeTimelineItem:

    def __init__(self, media_pool_item, start_frame):
        self._media_pool_item = media_pool_item
        self._start_frame = start_frame

    def GetMediaPoolItem(self):
        return self._media_pool_item

    def GetStart(self):
        return self._start_frame


class FakeTimelineClip:
    """
    Represents a Timeline's own entry in the Media Pool (every
    real Resolve Timeline also exists as a Media Pool item of
    Type "Timeline" - this is what create_timeline() looks up to
    nest a day's timeline into the Master timeline).
    """

    def __init__(self, name):
        self.name = name

    def GetClipProperty(self):
        return {
            "Type": "Timeline",
            "File Name": self.name,
            "Clip Name": self.name,
        }

    def GetName(self):
        return self.name


class FakeFolder:

    def __init__(self):
        self.clips = []
        self.subfolders = []

    def GetClipList(self):
        return self.clips

    def GetSubFolderList(self):
        return self.subfolders


class FakeMediaPool:

    def __init__(self):
        self.append_calls = []
        self.timeline = None
        self.created_timelines = []
        self.root_folder = FakeFolder()

    def GetRootFolder(self):
        return self.root_folder

    def CreateEmptyTimeline(self, name):
        timeline = FakeTimeline(name)
        self.timeline = timeline
        self.created_timelines.append(timeline)
        # Every real Resolve Timeline also exists as a Media Pool
        # item - mirror that here so _find_timeline_media_pool_item()
        # can find it for Master-timeline nesting.
        self.root_folder.clips.append(FakeTimelineClip(name))
        return timeline

    def AppendToTimeline(self, items):
        self.append_calls.append(items)
        return self._place(items)

    def _place(self, items):
        """
        Places items on self.timeline exactly as requested and
        returns the resulting FakeTimelineItems - the "everything
        works correctly" baseline. Subclasses override
        AppendToTimeline to simulate specific Resolve failure
        modes, but should still route through this so
        GetItemListInTrack() reflects what was actually placed.

        When an item has no "recordFrame" key (the Master
        timeline's nested-clip appends never specify one), a
        synthetic sequence position is assigned instead - this
        fake harness only needs to prove ORDERING for those
        appends, not real Resolve duration-based end-of-track
        frame math.
        """

        appended = []

        for item in items:

            record_frame = item.get("recordFrame")

            if record_frame is None:
                existing = (
                    self.timeline.items_by_track.get(
                        item["trackIndex"], []
                    )
                    if self.timeline is not None
                    else []
                )
                record_frame = len(existing)

            timeline_item = FakeTimelineItem(
                item["mediaPoolItem"], record_frame
            )

            if self.timeline is not None:
                self.timeline.items_by_track.setdefault(
                    item["trackIndex"], []
                ).append(timeline_item)

            appended.append(timeline_item)

        return appended


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
                # ML-054 Scope Change #2: this test exercises
                # multi-camera Resolve wiring mechanics, not the
                # HERO13-only default rule - opt into the richer
                # per-clip path explicitly.
                "enable_multicam_audio_sync": True,
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

        # create_timeline() now returns the assembled Master
        # timeline (see ML-057 follow-up) - this fixture has a
        # single ride day, so the actual day timeline with the
        # real tracks/clips/markers is the first one created.
        day_timeline = media_pool.created_timelines[0]

        # One AppendToTimeline call per distinct track is now
        # expected (ML-018 - splitting per track avoids a
        # same-frame, cross-track batching issue diagnosed in
        # Resolve where a clip sharing another track's clip's
        # exact recordFrame within the SAME batch call could
        # silently vanish from the timeline entirely).
        #
        # create_timeline() also nests this day's timeline into
        # a Master timeline afterward (a separate, later
        # AppendToTimeline call carrying a Timeline-type Media
        # Pool item, not a clip) - excluded here since this
        # section is only about per-clip placement mechanics on
        # the day's own timeline.

        day_clip_calls = [
            call
            for call in media_pool.append_calls
            if not _is_timeline_nesting_call(call)
        ]

        items = [
            item
            for call in day_clip_calls
            for item in call
        ]

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

        if len(day_clip_calls) != len(track_indexes):
            raise RuntimeError(
                "Expected one AppendToTimeline call per distinct "
                f"track, got {len(day_clip_calls)} calls "
                f"for {len(track_indexes)} track(s)."
            )

        # Enough video tracks must have been created.
        if day_timeline.GetTrackCount("video") < max(track_indexes):
            raise RuntimeError(
                "Not enough video tracks were created for the "
                "highest track_index used."
            )

        # Tracks must be named after their camera.
        named_tracks = {
            name for name in day_timeline.track_names.values()
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
        if len(day_timeline.markers) != 1:
            raise RuntimeError(
                f"Expected 1 marker written to the timeline, got "
                f"{len(day_timeline.markers)}."
            )

        if 0 not in day_timeline.markers:
            raise RuntimeError(
                "Expected a marker at frame 0 (Ride Day 1)."
            )

        if day_timeline.markers[0]["name"] != "Ride Day 1":
            raise RuntimeError(
                f"Expected marker at frame 0 named 'Ride Day 1', "
                f"got {day_timeline.markers[0]['name']!r}."
            )


class FakeMediaPoolDropsOne(FakeMediaPool):
    """
    Simulates Resolve silently dropping one specific requested
    clip (e.g. an overlap with existing content on the same
    video track at the same recordFrame) - AppendToTimeline
    returns fewer TimelineItems than were requested for whichever
    call contains that clip, without raising.

    Named rather than positional ("drop the last item"), since
    create_timeline() now issues one AppendToTimeline call per
    track (ML-018) - a positional drop would remove the only
    item in a single-item, single-track call and change the
    test's intent.
    """

    def __init__(self, drop_name):
        super().__init__()
        self.drop_name = drop_name.lower()

    def AppendToTimeline(self, items):
        self.append_calls.append(items)

        keep = [
            item
            for item in items
            if self._name_of(item) != self.drop_name
        ]

        return self._place(keep)

    @staticmethod
    def _name_of(item):
        props = item["mediaPoolItem"].GetClipProperty()
        name = props.get("File Name") or props.get("Clip Name") or ""
        return name.lower()


class FakeMediaPoolWrongPosition(FakeMediaPool):
    """
    Simulates Resolve accepting every requested clip (correct
    count, no dropped-clip warning) while silently placing one
    or more of them at the WRONG frame - the exact failure mode
    a count-only check can't catch, and the one behind the
    "empty-looking track" symptom seen with paired Insta360
    views.
    """

    def __init__(self, wrong_position_for):
        super().__init__()
        self.wrong_position_for = set(wrong_position_for)

    def AppendToTimeline(self, items):
        self.append_calls.append(items)

        appended = []

        for item in items:

            props = item["mediaPoolItem"].GetClipProperty()
            name = props.get("File Name") or props.get("Clip Name")

            actual_frame = item.get("recordFrame")

            if actual_frame is None:
                existing = (
                    self.timeline.items_by_track.get(
                        item["trackIndex"], []
                    )
                    if self.timeline is not None
                    else []
                )
                actual_frame = len(existing)

            if name in self.wrong_position_for:
                # Lands somewhere else entirely, rather than at
                # the requested recordFrame.
                actual_frame += 999999

            timeline_item = FakeTimelineItem(
                item["mediaPoolItem"], actual_frame
            )

            if self.timeline is not None:
                self.timeline.items_by_track.setdefault(
                    item["trackIndex"], []
                ).append(timeline_item)

            appended.append(timeline_item)

        return appended


class CreateTimelineDroppedClipRegressionTest(BaseRegressionTest):

    name = "Create Timeline Dropped Clip Warning (ML-013)"

    category = "Resolve"

    description = (
        "Verify create_timeline() detects and reports when "
        "Resolve's AppendToTimeline returns fewer items than "
        "were requested, instead of silently reporting success."
    )

    def _make_media(self, filename, camera_model, created, duration_seconds, fps=24.0):

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

        import io
        from contextlib import redirect_stdout

        from sba_resolve.commands.create_timeline import create_timeline

        day1_start = datetime(2026, 7, 1, 9, 0, 0)

        media_objects = [
            self._make_media(
                "hero13_0001.mp4", "HERO13 Black", day1_start, 60
            ),
            self._make_media(
                "hero8_0001.mp4",
                "HERO8 Black",
                day1_start + timedelta(seconds=95),
                45,
            ),
        ]

        imported_items = [
            FakeClip("hero13_0001.mp4"),
            FakeClip("hero8_0001.mp4"),
        ]

        project = FakeProject()
        media_pool = FakeMediaPoolDropsOne(drop_name="hero8_0001.mp4")

        context = FakeContext(
            project=project,
            media_pool=media_pool,
            project_data={
                "project_name": "Test Project",
                "timeline_name": "Test Project Master",
                "media_objects": media_objects,
                # ML-054 Scope Change #2: this test exercises
                # Resolve's own drop-detection mechanics via a
                # HERO8 clip - opt into the richer per-clip path
                # explicitly rather than being excluded by the
                # new HERO13-only default.
                "enable_multicam_audio_sync": True,
            },
            imported_items=imported_items,
        )

        captured = io.StringIO()

        with redirect_stdout(captured):
            timeline = create_timeline(context)

        output = captured.getvalue()

        if timeline is None:
            raise RuntimeError(
                "create_timeline() should not raise or return "
                "None just because Resolve dropped a clip - it "
                "should warn and continue."
            )

        if "WARNING" not in output or "silently dropped" not in output:
            raise RuntimeError(
                "Expected a WARNING about silently dropped "
                "clip(s) when AppendToTimeline returns fewer "
                "items than requested. Got output:\n" + output
            )

        # The report should reflect what Resolve ACTUALLY placed
        # (1), not what was requested (2).
        if "Timeline created with 1 clips" not in output:
            raise RuntimeError(
                "Expected the final summary to report the "
                "actual placed count (1), not the requested "
                "count. Got output:\n" + output
            )


class CreateTimelineWrongPositionRegressionTest(BaseRegressionTest):

    name = "Create Timeline Wrong Position Warning (ML-017)"

    category = "Resolve"

    description = (
        "Verify create_timeline() detects and reports when a "
        "clip lands at the WRONG frame despite AppendToTimeline "
        "returning a full, correctly-sized list - the failure "
        "mode a count-only check can't catch."
    )

    def _make_media(self, filename, camera_model, created, duration_seconds, fps=24.0):

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

        import io
        from contextlib import redirect_stdout

        from sba_resolve.commands.create_timeline import create_timeline

        day1_start = datetime(2026, 7, 1, 9, 0, 0)

        media_objects = [
            self._make_media(
                "hero13_0001.mp4", "HERO13 Black", day1_start, 60
            ),
            self._make_media(
                "hero8_0001.mp4",
                "HERO8 Black",
                day1_start + timedelta(seconds=95),
                45,
            ),
        ]

        imported_items = [
            FakeClip("hero13_0001.mp4"),
            FakeClip("hero8_0001.mp4"),
        ]

        project = FakeProject()

        # hero8_0001.mp4 will report a full, successful
        # AppendToTimeline (correct count, no dropped-clip
        # warning), but actually lands at the wrong frame.
        media_pool = FakeMediaPoolWrongPosition(
            wrong_position_for={"hero8_0001.mp4"}
        )

        context = FakeContext(
            project=project,
            media_pool=media_pool,
            project_data={
                "project_name": "Test Project",
                "timeline_name": "Test Project Master",
                "media_objects": media_objects,
                # ML-054 Scope Change #2: this test exercises
                # Resolve's own wrong-position-detection mechanics
                # via a HERO8 clip - opt into the richer per-clip
                # path explicitly rather than being excluded by
                # the new HERO13-only default.
                "enable_multicam_audio_sync": True,
            },
            imported_items=imported_items,
        )

        captured = io.StringIO()

        with redirect_stdout(captured):
            timeline = create_timeline(context)

        output = captured.getvalue()

        if timeline is None:
            raise RuntimeError(
                "create_timeline() should not raise or return "
                "None for a wrong-position placement - it "
                "should warn and continue."
            )

        # Must NOT report a dropped-clip warning - the count was
        # correct, this is a different failure mode.
        if "silently dropped" in output:
            raise RuntimeError(
                "This scenario has a correct count - it should "
                "not trigger the dropped-clip warning. Got "
                "output:\n" + output
            )

        if (
            "did not land where requested" not in output
            or "hero8_0001.mp4" not in output
        ):
            raise RuntimeError(
                "Expected a WARNING naming hero8_0001.mp4 as "
                "having landed at the wrong frame. Got output:\n"
                + output
            )

        if "NOT FOUND" in output:
            raise RuntimeError(
                "hero8_0001.mp4 WAS found on its track (just at "
                "the wrong frame) - should report the actual "
                "frame, not NOT FOUND. Got output:\n" + output
            )