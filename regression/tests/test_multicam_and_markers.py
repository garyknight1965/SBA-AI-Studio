"""
============================================================
SBA AI Studio
Multicam Detection + Markers Regression Test
ML-011-017 / ML-011-018
Version : 1.0.0
============================================================

Verifies:
- MulticamDetector finds real overlapping-camera windows and
  ignores clips that merely touch (no gap, no overlap).
- MulticamCandidate.camera_count reflects distinct cameras, not
  raw clip count (a camera can contribute multiple clips to a
  single overlap window).
- TimelineMarkerGenerator produces a "Ride Day" marker and a
  "Multicam" marker at the correct frames.
- PlanningSegments that participate in a multicam window are
  flagged (segment.multicam_candidate == True).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class MulticamAndMarkersRegressionTest(BaseRegressionTest):

    name = "Multicam Detection + Markers (ML-011)"

    category = "Planning"

    description = (
        "Verify multicam window detection, corrected camera_count, "
        "and ride-day/multicam marker generation."
    )

    def _make_media(
        self,
        filename,
        camera_model,
        created,
        duration_seconds,
        fps=25.0,
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

        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.services.timeline_planning_service import (
            TimelinePlanningService,
        )

        library = MediaLibrary()

        day1_start = datetime(2026, 7, 1, 9, 0, 0)

        # Hero13 records two back-to-back clips (0-60s, 60-120s).
        library.add(
            self._make_media(
                "hero13_0001.mp4", "HERO13 Black", day1_start, 60
            )
        )
        library.add(
            self._make_media(
                "hero13_0002.mp4",
                "HERO13 Black",
                day1_start + timedelta(seconds=60),
                60,
            )
        )

        # Hero8 switches on at 40s and runs for 50s (40s-90s),
        # overlapping the tail of clip 1 and the start of clip 2.
        # This means the Hero13 side of the overlap spans 2 clips
        # from the SAME camera - the case that previously broke
        # camera_count (it counted clips, not distinct cameras).
        library.add(
            self._make_media(
                "hero8_0001.mp4",
                "HERO8 Black",
                day1_start + timedelta(seconds=40),
                50,
            )
        )

        result = TimelinePlanningService().plan(library)

        if len(result.multicam_candidates) != 1:
            raise RuntimeError(
                f"Expected 1 multicam candidate, got "
                f"{len(result.multicam_candidates)}."
            )

        candidate = result.multicam_candidates[0]

        if candidate.camera_count != 2:
            raise RuntimeError(
                f"Expected camera_count 2 (distinct cameras), got "
                f"{candidate.camera_count}. This candidate has "
                f"{len(candidate.clips)} clips from "
                f"{len(candidate.camera_names)} camera(s) - "
                f"camera_count must reflect distinct cameras, not "
                f"raw clip count."
            )

        if not candidate.is_valid:
            raise RuntimeError(
                "Candidate with 2 distinct cameras should be valid."
            )

        if set(candidate.camera_names) != {
            "GoPro HERO13 Black",
            "GoPro HERO8 Black",
        }:
            raise RuntimeError(
                f"Unexpected camera_names: {candidate.camera_names}"
            )

        # 3 clips total contributed to this window (2 from Hero13,
        # 1 from Hero8), even though only 2 distinct cameras.
        if len(candidate.clips) != 3:
            raise RuntimeError(
                f"Expected 3 clips in the candidate, got "
                f"{len(candidate.clips)}."
            )

        # Segments that contributed a clip to the multicam window
        # must be flagged.
        flagged_segments = [
            s for s in result.segments if s.multicam_candidate
        ]

        if len(flagged_segments) != len(result.segments):
            raise RuntimeError(
                "All 3 segments in this scenario should be flagged "
                "as multicam_candidate=True (every clip overlaps "
                "the window)."
            )

        if result.statistics.multicam_segments != len(result.segments):
            raise RuntimeError(
                "statistics.multicam_segments should count "
                "multicam-flagged segments."
            )

        # Markers: one Ride Day marker at frame 0, one Multicam
        # marker at the start of the overlap window.
        marker_titles = {m.title: m.frame for m in result.markers}

        if "Ride Day 1" not in marker_titles:
            raise RuntimeError("Missing 'Ride Day 1' marker.")

        if marker_titles["Ride Day 1"] != 0:
            raise RuntimeError(
                f"Expected 'Ride Day 1' marker at frame 0, got "
                f"{marker_titles['Ride Day 1']}."
            )

        multicam_markers = [
            m for m in result.markers if m.category == "Multicam"
        ]

        if len(multicam_markers) != 1:
            raise RuntimeError(
                f"Expected 1 multicam marker, got "
                f"{len(multicam_markers)}."
            )

        if multicam_markers[0].frame != candidate.start_frame:
            raise RuntimeError(
                "Multicam marker frame doesn't match the "
                "candidate's start_frame."
            )

        if "2 cameras" not in multicam_markers[0].title:
            raise RuntimeError(
                f"Expected marker title to say '2 cameras', got "
                f"{multicam_markers[0].title!r}."
            )

        if result.statistics.markers != len(result.markers):
            raise RuntimeError(
                "statistics.markers doesn't match len(result.markers)."
            )

        # ------------------------------------------------
        # Negative case: touching-but-not-overlapping clips
        # must NOT be flagged as multicam.
        # ------------------------------------------------

        library2 = MediaLibrary()

        library2.add(
            self._make_media(
                "hero13_0003.mp4", "HERO13 Black", day1_start, 60
            )
        )
        library2.add(
            self._make_media(
                "hero8_0002.mp4",
                "HERO8 Black",
                day1_start + timedelta(seconds=60),
                30,
            )
        )

        result2 = TimelinePlanningService().plan(library2)

        if result2.multicam_candidates:
            raise RuntimeError(
                "Touching-but-not-overlapping clips must not "
                "produce a multicam candidate."
            )

        if any(s.multicam_candidate for s in result2.segments):
            raise RuntimeError(
                "No segment should be flagged as multicam in the "
                "non-overlapping scenario."
            )

        # ------------------------------------------------
        # Frame-collision case: both cameras start at the exact
        # same instant, so the Ride Day marker and the Multicam
        # marker would both land on frame 0. Resolve only
        # supports one marker per frame, so these must be merged
        # into a single marker rather than one silently
        # overwriting the other when written to Resolve.
        # ------------------------------------------------

        library3 = MediaLibrary()

        library3.add(
            self._make_media(
                "hero13_0004.mp4", "HERO13 Black", day1_start, 60
            )
        )
        library3.add(
            self._make_media(
                "hero8_0003.mp4", "HERO8 Black", day1_start, 60
            )
        )

        result3 = TimelinePlanningService().plan(library3)

        markers_at_zero = [
            m for m in result3.markers if m.frame == 0
        ]

        if len(markers_at_zero) != 1:
            raise RuntimeError(
                f"Expected exactly 1 merged marker at frame 0, "
                f"got {len(markers_at_zero)}. Same-frame markers "
                f"must be merged, since Resolve only supports one "
                f"marker per exact frame."
            )

        merged = markers_at_zero[0]

        if "Ride Day 1" not in merged.title:
            raise RuntimeError(
                f"Merged marker lost the Ride Day title: "
                f"{merged.title!r}"
            )

        if "Multicam" not in merged.title:
            raise RuntimeError(
                f"Merged marker lost the Multicam title: "
                f"{merged.title!r}"
            )
