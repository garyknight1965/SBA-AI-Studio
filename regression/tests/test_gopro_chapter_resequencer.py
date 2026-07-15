"""
============================================================
SBA AI Studio
GoPro Chapter Resequencer Regression Test
ML-022
Version : 1.0.0
============================================================

Verifies:
- Multiple chapters sharing a session number (e.g. GH010145,
  GH020145, GH030145) get corrected, sequential capture times -
  chapter 1's real timestamp stays as the anchor, and each later
  chapter's time becomes the previous chapter's (corrected) time
  plus that chapter's duration.
- A lone GoPro file whose session number happens to match the
  pattern, but has no sibling chapters, is left untouched.
- Files from a DIFFERENT camera/session are never cross-mixed
  into the wrong group.
- End to end: running the full Planning Engine on a 3-chapter
  recording places all 3 chapters back-to-back, not collapsed
  onto the same frame.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class GoProChapterResequencerRegressionTest(BaseRegressionTest):

    name = "GoPro Chapter Resequencer (ML-022)"

    category = "Planning"

    description = (
        "Verify multi-chapter GoPro recordings get corrected, "
        "sequential capture times instead of all chapters "
        "sharing chapter 1's timestamp."
    )

    def _make_media(
        self,
        filename,
        camera_model,
        created,
        duration_seconds=60,
        fps=24.0,
    ):

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

        from sba_resolve.core.services.gopro_chapter_resequencer import (
            GoProChapterResequencer,
        )

        recording_start = datetime(2026, 7, 1, 9, 0, 0)

        # 3 chapters of ONE continuous recording (session 0145).
        # GoPro embeds recording_start into ALL of them - that's
        # the bug being fixed.
        chapter1 = self._make_media(
            "GH010145.MP4", "HERO13 Black", recording_start, 120
        )
        chapter2 = self._make_media(
            "GH020145.MP4", "HERO13 Black", recording_start, 90
        )
        chapter3 = self._make_media(
            "GH030145.MP4", "HERO13 Black", recording_start, 45
        )

        # A separate, unrelated single-chapter recording from the
        # SAME camera - must not be touched or cross-mixed.
        unrelated = self._make_media(
            "GH010200.MP4",
            "HERO13 Black",
            recording_start + timedelta(hours=2),
            60,
        )

        # A different camera that happens to reuse the same
        # session number - must be grouped separately, not mixed
        # with the HERO13 chapters above.
        other_camera_chapter1 = self._make_media(
            "GH010145.MP4",
            "HERO8 Black",
            recording_start + timedelta(minutes=5),
            60,
        )
        other_camera_chapter2 = self._make_media(
            "GH020145.MP4",
            "HERO8 Black",
            recording_start + timedelta(minutes=5),
            60,
        )

        media_files = [
            chapter3,
            chapter1,
            unrelated,
            chapter2,
            other_camera_chapter2,
            other_camera_chapter1,
        ]

        GoProChapterResequencer().resequence(media_files)

        # Chapter 1 is the anchor - untouched.
        if chapter1.created != recording_start:
            raise RuntimeError(
                f"Chapter 1's timestamp should never change, got "
                f"{chapter1.created!r}."
            )

        # Chapter 2 should start exactly when chapter 1 ends.
        expected_chapter2 = recording_start + timedelta(
            seconds=120
        )

        if chapter2.created != expected_chapter2:
            raise RuntimeError(
                f"Expected chapter 2 at {expected_chapter2!r}, "
                f"got {chapter2.created!r}."
            )

        # Chapter 3 should start exactly when chapter 2 ends
        # (using chapter 2's CORRECTED time, not its original one).
        expected_chapter3 = expected_chapter2 + timedelta(
            seconds=90
        )

        if chapter3.created != expected_chapter3:
            raise RuntimeError(
                f"Expected chapter 3 at {expected_chapter3!r}, "
                f"got {chapter3.created!r}."
            )

        # The unrelated single-chapter recording must be
        # untouched.
        if unrelated.created != recording_start + timedelta(
            hours=2
        ):
            raise RuntimeError(
                "An unrelated single-chapter recording must not "
                "be modified."
            )

        # The other camera's chapters must be resequenced
        # independently, not mixed with HERO13's chapters.
        if other_camera_chapter1.created != (
            recording_start + timedelta(minutes=5)
        ):
            raise RuntimeError(
                "A different camera's chapter 1 must never "
                "change."
            )

        expected_other_chapter2 = (
            recording_start + timedelta(minutes=5, seconds=60)
        )

        if other_camera_chapter2.created != expected_other_chapter2:
            raise RuntimeError(
                f"Expected the other camera's chapter 2 at "
                f"{expected_other_chapter2!r}, got "
                f"{other_camera_chapter2.created!r} - it may have "
                f"been cross-mixed with the HERO13 group."
            )

        # --------------------------------------------------
        # End to end: the Planning Engine must place all 3
        # chapters back-to-back, not collapsed onto one frame.
        # --------------------------------------------------

        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.services.timeline_planning_service import (
            TimelinePlanningService,
        )

        fresh_chapter1 = self._make_media(
            "GH010500.MP4", "HERO13 Black", recording_start, 120
        )
        fresh_chapter2 = self._make_media(
            "GH020500.MP4", "HERO13 Black", recording_start, 90
        )
        fresh_chapter3 = self._make_media(
            "GH030500.MP4", "HERO13 Black", recording_start, 45
        )

        library = MediaLibrary()
        library.add(fresh_chapter2)
        library.add(fresh_chapter1)
        library.add(fresh_chapter3)

        # Note: TimelinePlanningService doesn't call the
        # resequencer itself (it's an import-time correction, not
        # a planning-time one) - this proves that once corrected,
        # the Planning Engine places the results correctly.
        GoProChapterResequencer().resequence(list(library))

        result = TimelinePlanningService().plan(library)

        placements_by_name = {
            p.clip_name: p.record_frame for p in result.placements
        }

        fps = 25.0

        if placements_by_name["GH010500.MP4"] != 0:
            raise RuntimeError("Chapter 1 should start at frame 0.")

        if placements_by_name["GH020500.MP4"] != round(120 * fps):
            raise RuntimeError(
                "Chapter 2 should start immediately after "
                "chapter 1's duration, not collide with it."
            )

        if placements_by_name["GH030500.MP4"] != round(
            (120 + 90) * fps
        ):
            raise RuntimeError(
                "Chapter 3 should start immediately after "
                "chapters 1+2's combined duration."
            )
