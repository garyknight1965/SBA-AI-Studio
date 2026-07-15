"""
============================================================
SBA AI Studio
Gap Compression Regression Test
ML-012
Version : 1.0.0
============================================================

Verifies:
- Gap Compression is OFF by default: TimelinePlanningService()
  with no gap_compression argument produces the exact same
  record_frame values as before this feature existed.
- When enabled, a long real-world gap is compressed down to
  the configured compressed_gap_seconds, while a short gap
  (below the threshold) is left untouched.
- Multicam detection still finds the same overlap window
  under compression (start/end frames simply shift with the
  compressed timeline).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class GapCompressionRegressionTest(BaseRegressionTest):

    name = "Gap Compression (ML-012)"

    category = "Planning"

    description = (
        "Verify Gap Compression is opt-in, disabled by default, "
        "and correctly shortens long gaps without disturbing "
        "multicam detection."
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

        from sba_resolve.core.models.gap_compression_settings import (
            GapCompressionSettings,
        )
        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.services.timeline_planning_service import (
            TimelinePlanningService,
        )

        day_start = datetime(2026, 7, 1, 9, 0, 0)

        # Clip 1: 0-30s.
        # Short gap (10s) then Clip 2: 40-70s.
        # Long gap (30 min) then Clip 3: 1840-1870s.
        clip1_start = day_start
        clip2_start = day_start + timedelta(seconds=40)
        clip3_start = clip2_start + timedelta(seconds=30) + timedelta(
            minutes=30
        )

        def build_library():
            library = MediaLibrary()
            library.add(
                self._make_media(
                    "hero13_0001.mp4", "HERO13 Black", clip1_start, 30
                )
            )
            library.add(
                self._make_media(
                    "hero13_0002.mp4", "HERO13 Black", clip2_start, 30
                )
            )
            library.add(
                self._make_media(
                    "hero13_0003.mp4", "HERO13 Black", clip3_start, 30
                )
            )
            return library

        # ------------------------------------------------
        # 1. Disabled (default): must reproduce the original
        #    real-ride-time, fully gap-preserving placement.
        # ------------------------------------------------

        default_result = TimelinePlanningService().plan(build_library())

        placements_by_name = {
            p.clip_name: p for p in default_result.placements
        }

        fps = 25.0

        expected_clip2_frame = round(
            (clip2_start - clip1_start).total_seconds() * fps
        )
        expected_clip3_frame = round(
            (clip3_start - clip1_start).total_seconds() * fps
        )

        if placements_by_name["hero13_0002.mp4"].record_frame != (
            expected_clip2_frame
        ):
            raise RuntimeError(
                "Gap Compression disabled by default should "
                "preserve the original short-gap placement, but "
                f"got {placements_by_name['hero13_0002.mp4'].record_frame} "
                f"instead of {expected_clip2_frame}."
            )

        if placements_by_name["hero13_0003.mp4"].record_frame != (
            expected_clip3_frame
        ):
            raise RuntimeError(
                "Gap Compression disabled by default should "
                "preserve the original long-gap placement, but "
                f"got {placements_by_name['hero13_0003.mp4'].record_frame} "
                f"instead of {expected_clip3_frame}."
            )

        # ------------------------------------------------
        # 2. Enabled: the 30 minute gap (well above the 60s
        #    threshold) should compress down to 2s. The 10s
        #    gap (below threshold) must stay untouched.
        # ------------------------------------------------

        settings = GapCompressionSettings(
            enabled=True,
            gap_threshold_seconds=60.0,
            compressed_gap_seconds=2.0,
        )

        compressed_result = TimelinePlanningService(
            gap_compression=settings
        ).plan(build_library())

        compressed_by_name = {
            p.clip_name: p for p in compressed_result.placements
        }

        # Clip 2 sits after only a 10s gap (below the 60s
        # threshold) - its position must be unchanged.
        if compressed_by_name["hero13_0002.mp4"].record_frame != (
            expected_clip2_frame
        ):
            raise RuntimeError(
                "A gap below the threshold must not be "
                "compressed, but clip 2's frame changed: "
                f"{compressed_by_name['hero13_0002.mp4'].record_frame} "
                f"!= {expected_clip2_frame}."
            )

        # Clip 3 sits after clip 2's end (70s) plus a 30 minute
        # gap, compressed to 2s. Expected position: clip2 end
        # (frame at 70s) + 2s of compressed gap.
        clip2_end_frame = expected_clip2_frame + round(30 * fps)
        expected_compressed_clip3_frame = clip2_end_frame + round(
            2.0 * fps
        )

        if compressed_by_name["hero13_0003.mp4"].record_frame != (
            expected_compressed_clip3_frame
        ):
            raise RuntimeError(
                "Long gap was not compressed to the configured "
                "compressed_gap_seconds: got "
                f"{compressed_by_name['hero13_0003.mp4'].record_frame}, "
                f"expected {expected_compressed_clip3_frame}."
            )

        # The long-gap clip must now land much earlier than it
        # did with compression disabled - proof compression
        # actually shortened the timeline.
        if compressed_by_name["hero13_0003.mp4"].record_frame >= (
            placements_by_name["hero13_0003.mp4"].record_frame
        ):
            raise RuntimeError(
                "Compressed placement should land earlier than "
                "the uncompressed placement for the same clip."
            )

        # ------------------------------------------------
        # 3. Multicam detection must still agree with placement
        #    under compression (regression against the anchor/
        #    gap_map wiring in MulticamDetector).
        # ------------------------------------------------

        multicam_library = MediaLibrary()

        multicam_library.add(
            self._make_media(
                "hero13_overlap.mp4", "HERO13 Black", clip3_start, 60
            )
        )
        multicam_library.add(
            self._make_media(
                "hero8_overlap.mp4",
                "HERO8 Black",
                clip3_start + timedelta(seconds=10),
                30,
            )
        )

        multicam_result = TimelinePlanningService(
            gap_compression=settings
        ).plan(multicam_library)

        if len(multicam_result.multicam_candidates) != 1:
            raise RuntimeError(
                "Expected 1 multicam candidate under Gap "
                "Compression, got "
                f"{len(multicam_result.multicam_candidates)}."
            )

        candidate = multicam_result.multicam_candidates[0]

        overlap_placement = next(
            p
            for p in multicam_result.placements
            if p.clip_name == "hero13_overlap.mp4"
        )

        expected_start_frame = overlap_placement.record_frame + round(
            10 * fps
        )

        if candidate.start_frame != expected_start_frame:
            raise RuntimeError(
                "Multicam candidate start_frame doesn't match the "
                "compressed placement's timeline: got "
                f"{candidate.start_frame}, expected "
                f"{expected_start_frame}."
            )
