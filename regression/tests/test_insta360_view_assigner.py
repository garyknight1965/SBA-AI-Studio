"""
============================================================
SBA AI Studio
Insta360 View Assigner Regression Test
ML-015
Version : 1.0.0
============================================================

Verifies:
- Two Insta360 files sharing the same VID_ group prefix (date,
  time, seq, chapter) get distinct CameraProfile.view labels,
  and therefore distinct camera_display_name values - which
  PlanningSegmentBuilder/TimelinePlacementBuilder use for
  segment grouping and track assignment.
- A lone Insta360 file (no matching sibling) is left untouched
  (view stays blank, plain "Insta360 X3" display name).
- Non-Insta360 files (e.g. GoPro) are never touched.
- End to end: running the full Planning Engine on a paired
  Insta360 clip no longer collides both clips onto one track -
  they land on two separate tracks, and the shared timestamp is
  correctly flagged as a multicam window (two synced views of
  the same moment).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest


class Insta360ViewAssignerRegressionTest(BaseRegressionTest):

    name = "Insta360 View Assigner (ML-015)"

    category = "Planning"

    description = (
        "Verify paired same-moment Insta360 files get distinct "
        "view labels (and therefore separate tracks), while "
        "unpaired Insta360 and non-Insta360 files are untouched."
    )

    def _make_media(
        self,
        filename,
        manufacturer,
        model,
        created,
        duration_seconds=60,
        fps=25.0,
    ):

        from sba_resolve.core.models.camera_profile import (
            CameraProfile,
            CameraType,
        )
        from sba_resolve.core.models.media_file import MediaFile

        profile = CameraProfile(
            manufacturer=manufacturer,
            model=model,
            family=model,
            camera_type=CameraType.CAMERA360,
            confidence=100,
            detection_method="Test Fixture",
        )

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            camera_model=model,
            camera_profile=profile,
            created=created,
            duration=str(duration_seconds),
            fps=fps,
        )

    def run(self) -> None:

        from sba_resolve.core.models.camera_profile import (
            CameraManufacturer,
        )
        from sba_resolve.core.services.insta360_view_assigner import (
            Insta360ViewAssigner,
        )

        moment = datetime(2026, 6, 27, 9, 15, 46)

        # Paired views of the same moment (same date/time/seq/
        # chapter, different trailing number).
        view_a = self._make_media(
            "VID_20260627_091546_00_002_182721.mp4",
            CameraManufacturer.INSTA360,
            "X3",
            moment,
        )
        view_b = self._make_media(
            "VID_20260627_091546_00_002_183113.mp4",
            CameraManufacturer.INSTA360,
            "X3",
            moment,
        )

        # A lone Insta360 clip with no paired sibling.
        lone = self._make_media(
            "VID_20260627_101421_00_004_182907.mp4",
            CameraManufacturer.INSTA360,
            "X3",
            datetime(2026, 6, 27, 10, 14, 21),
        )

        # A GoPro file must never be touched by this assigner.
        gopro = self._make_media(
            "GX010060.MP4",
            CameraManufacturer.GOPRO,
            "HERO13 Black",
            datetime(2026, 6, 27, 8, 0, 0),
        )

        media_files = [view_a, view_b, lone, gopro]

        Insta360ViewAssigner().assign(media_files)

        if view_a.camera_profile.view == view_b.camera_profile.view:
            raise RuntimeError(
                "Paired views must get DIFFERENT view labels, "
                f"got the same value for both: "
                f"{view_a.camera_profile.view!r}"
            )

        if not view_a.camera_profile.view or not view_b.camera_profile.view:
            raise RuntimeError(
                "Paired views must both get a non-empty view "
                f"label. Got: {view_a.camera_profile.view!r}, "
                f"{view_b.camera_profile.view!r}"
            )

        if view_a.camera_display_name == view_b.camera_display_name:
            raise RuntimeError(
                "Paired views must resolve to different "
                f"camera_display_name values, both got "
                f"{view_a.camera_display_name!r}"
            )

        if lone.camera_profile.view:
            raise RuntimeError(
                "A lone Insta360 clip (no matching sibling) "
                f"must not get a view label, got "
                f"{lone.camera_profile.view!r}"
            )

        if lone.camera_display_name != "Insta360 X3":
            raise RuntimeError(
                "A lone Insta360 clip's display name should stay "
                f"plain 'Insta360 X3', got "
                f"{lone.camera_display_name!r}"
            )

        if gopro.camera_profile.view:
            raise RuntimeError(
                "GoPro files must never be touched by "
                "Insta360ViewAssigner."
            )

        # --------------------------------------------------
        # End to end: the Planning Engine must now place the
        # paired views on two different tracks, not collide
        # them, and flag the shared moment as a multicam window.
        # --------------------------------------------------

        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.services.timeline_planning_service import (
            TimelinePlanningService,
        )

        library = MediaLibrary()
        library.add(view_a)
        library.add(view_b)

        result = TimelinePlanningService().plan(library)

        placements_by_name = {
            p.clip_name: p for p in result.placements
        }

        track_a = placements_by_name[view_a.filename].track_index
        track_b = placements_by_name[view_b.filename].track_index

        if track_a == track_b:
            raise RuntimeError(
                "Paired Insta360 views must land on DIFFERENT "
                f"tracks, both got track {track_a}."
            )

        if len(result.multicam_candidates) != 1:
            raise RuntimeError(
                "Expected the paired views to be detected as 1 "
                f"multicam window, got "
                f"{len(result.multicam_candidates)}."
            )
