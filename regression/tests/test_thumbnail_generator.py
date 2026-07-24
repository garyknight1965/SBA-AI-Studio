"""
============================================================
SBA AI Studio
Thumbnail Generator Regression Test
ML-061
Version : 1.0.0
============================================================

Verifies:
- ThumbnailFrameExtractor.suggest_candidates(): picks clips evenly
  spread across the given list (using a fake frame_reader - no real
  video files involved), computes the midpoint timestamp of each
  correctly, skips clips with no/invalid duration, caps the count to
  however many usable clips exist, and skips a candidate cleanly if
  the frame reader itself fails (returns None) rather than raising.
- ThumbnailComposer.compose(): always outputs exactly 1280x720
  regardless of the source image's aspect ratio (cover-fit crop, not
  stretch); accepts both a raw BGR numpy array (cv2's native format)
  and a plain PIL.Image directly; draws overlay text without raising
  and visibly changes pixels in the text region; pastes a logo image
  into the bottom-right corner; and handles a missing/invalid logo
  path gracefully (image unchanged, no crash).
- ThumbnailComposer.save(): writes a real, correctly-sized image file
  to disk.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from regression.base_test import BaseRegressionTest


class ThumbnailGeneratorRegressionTest(BaseRegressionTest):

    name = "Thumbnail Generator (ML-061)"

    category = "Planning"

    description = (
        "Verify candidate frame selection (evenly spaced, fake "
        "frame reader) and text/logo compositing (cover-fit "
        "resize, text drawing, logo pasting, graceful missing-"
        "logo handling)."
    )

    def _make_media(self, filename, duration_seconds):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            duration=str(duration_seconds) if duration_seconds is not None else None,
        )

    def run(self) -> None:

        self._run_frame_extractor_tests()
        self._run_composer_tests()
        self._run_settings_loader_tests()

    def _run_frame_extractor_tests(self) -> None:

        from sba_resolve.core.services.thumbnail_generator import (
            ThumbnailFrameExtractor,
        )

        # --------------------------------------------------
        # 1. Evenly spaced selection across 5 clips, count=3 ->
        #    indices 0, 2, 4 (first, middle, last).
        # --------------------------------------------------

        media_files = [
            self._make_media(f"clip{i}.mp4", duration_seconds=60.0)
            for i in range(5)
        ]

        read_calls = []

        def fake_reader(file_path, timestamp_seconds):
            read_calls.append((file_path, timestamp_seconds))
            return f"IMAGE:{file_path}"

        extractor = ThumbnailFrameExtractor(frame_reader=fake_reader)

        candidates = extractor.suggest_candidates(media_files, count=3)

        if [c.clip_name for c in candidates] != [
            "clip0.mp4", "clip2.mp4", "clip4.mp4"
        ]:
            raise RuntimeError(
                f"Expected evenly-spaced clips [0, 2, 4], got "
                f"{[c.clip_name for c in candidates]!r}."
            )

        # Midpoint of a 60s clip is 30s.
        if any(c.timestamp_seconds != 30.0 for c in candidates):
            raise RuntimeError(
                f"Expected every candidate's timestamp to be the "
                f"clip's midpoint (30.0s for a 60s clip), got "
                f"{[c.timestamp_seconds for c in candidates]!r}."
            )

        expected_image = f"IMAGE:{media_files[0].full_path}"

        if candidates[0].image != expected_image:
            raise RuntimeError(
                f"Expected the candidate's image to come from the "
                f"injected frame_reader, got "
                f"{candidates[0].image!r}, expected "
                f"{expected_image!r}."
            )

        # --------------------------------------------------
        # 2. Clips with no/invalid duration are skipped entirely
        #    - never even considered for spacing.
        # --------------------------------------------------

        mixed_media = [
            self._make_media("no_duration.mp4", duration_seconds=None),
            self._make_media("good1.mp4", duration_seconds=10.0),
            self._make_media("zero_duration.mp4", duration_seconds=0.0),
            self._make_media("good2.mp4", duration_seconds=20.0),
        ]

        extractor2 = ThumbnailFrameExtractor(frame_reader=fake_reader)

        candidates2 = extractor2.suggest_candidates(mixed_media, count=5)

        if [c.clip_name for c in candidates2] != ["good1.mp4", "good2.mp4"]:
            raise RuntimeError(
                f"Expected only the 2 clips with valid durations, "
                f"got {[c.clip_name for c in candidates2]!r}."
            )

        # --------------------------------------------------
        # 3. count is capped to however many usable clips exist -
        #    asking for 10 candidates from 2 usable clips should
        #    not raise or duplicate.
        # --------------------------------------------------

        if len(candidates2) != 2:
            raise RuntimeError(
                f"Expected count to be capped at 2 usable clips, "
                f"got {len(candidates2)}."
            )

        # --------------------------------------------------
        # 4. A frame reader that fails (returns None) for a
        #    specific clip is skipped cleanly, not raised.
        # --------------------------------------------------

        def failing_reader(file_path, timestamp_seconds):
            if "clip2" in file_path:
                return None
            return f"IMAGE:{file_path}"

        extractor3 = ThumbnailFrameExtractor(frame_reader=failing_reader)

        candidates3 = extractor3.suggest_candidates(media_files, count=5)

        if any(c.clip_name == "clip2.mp4" for c in candidates3):
            raise RuntimeError(
                "Expected clip2.mp4 (failed frame read) to be "
                "skipped, not included as a candidate."
            )

        if len(candidates3) != 4:
            raise RuntimeError(
                f"Expected 4 candidates (5 clips minus 1 failed "
                f"read), got {len(candidates3)}."
            )

    def _run_composer_tests(self) -> None:

        from PIL import Image

        from sba_resolve.core.services.thumbnail_generator import (
            ThumbnailComposer,
        )

        composer = ThumbnailComposer()

        # --------------------------------------------------
        # 5. Cover-fit crop always produces exactly 1280x720,
        #    regardless of source aspect ratio - test both a
        #    wide (16:9-ish but different absolute size) and a
        #    square source image.
        # --------------------------------------------------

        wide_source = Image.new("RGB", (640, 360), color=(10, 20, 30))

        composed_wide = composer.compose(wide_source, text="")

        if composed_wide.size != (1280, 720):
            raise RuntimeError(
                f"Expected a 1280x720 output for a wide source, "
                f"got {composed_wide.size!r}."
            )

        square_source = Image.new("RGB", (1000, 1000), color=(10, 20, 30))

        composed_square = composer.compose(square_source, text="")

        if composed_square.size != (1280, 720):
            raise RuntimeError(
                f"Expected a 1280x720 output for a square source "
                f"(cover-fit crop), got {composed_square.size!r}."
            )

        # --------------------------------------------------
        # 6. A raw BGR numpy array (cv2's native format) is
        #    accepted directly, not just a PIL.Image.
        # --------------------------------------------------

        import numpy as np

        # BGR array where B=10, G=20, R=30 -> should become RGB
        # (30, 20, 10) after conversion.
        bgr_array = np.full((360, 640, 3), (10, 20, 30), dtype=np.uint8)

        composed_from_array = composer.compose(bgr_array, text="")

        if composed_from_array.size != (1280, 720):
            raise RuntimeError(
                f"Expected a 1280x720 output from a numpy BGR "
                f"array input, got {composed_from_array.size!r}."
            )

        sampled_pixel = composed_from_array.getpixel((640, 360))

        if sampled_pixel != (30, 20, 10):
            raise RuntimeError(
                f"Expected BGR (10, 20, 30) to convert to RGB "
                f"(30, 20, 10), got {sampled_pixel!r} - the "
                f"BGR->RGB channel swap may be broken."
            )

        # --------------------------------------------------
        # 7. Overlay text visibly changes pixels in the text
        #    region, without raising.
        # --------------------------------------------------

        plain_source = Image.new("RGB", (1280, 720), color=(10, 20, 30))

        composed_with_text = composer.compose(
            plain_source, text="WHITHORN CASTLE RIDE"
        )

        text_region = composed_with_text.crop(
            (
                composer.TEXT_MARGIN,
                composer.TEXT_MARGIN,
                composer.TEXT_MARGIN + 400,
                composer.TEXT_MARGIN + 150,
            )
        )

        region_colors = {pixel for pixel in text_region.getdata()}

        if region_colors == {(10, 20, 30)}:
            raise RuntimeError(
                "Expected the text region to contain pixels "
                "other than the plain background colour after "
                "drawing text."
            )

        # --------------------------------------------------
        # 7b. ML-063: long text must be auto-fitted (shrunk or
        #     wrapped) to stay within the frame, not run off the
        #     right edge. This is the exact real-world bug Gary
        #     hit: "Motorcycle Touring Netherlands" overflowed
        #     past the right edge of a saved thumbnail.
        # --------------------------------------------------

        long_text_source = Image.new("RGB", (1280, 720), color=(20, 30, 40))

        composed_long_text = composer.compose(
            long_text_source, text="Motorcycle Touring Netherlands"
        )

        # The last few columns on the right edge should still be
        # plain background - if text overflowed the frame, ink
        # would appear right up against (or past) the edge.
        edge_region = composed_long_text.crop(
            (1270, 0, 1280, composer.TEXT_MARGIN + 150)
        )

        edge_colors = {pixel for pixel in edge_region.getdata()}

        if edge_colors != {(20, 30, 40)}:
            raise RuntimeError(
                "Expected the long overlay text to be shrunk/"
                "wrapped to fit within the frame - found non-"
                "background pixels at the right edge, meaning "
                "text is running off the screen again."
            )

        # --------------------------------------------------
        # 7c. ML-063: text far too long for even the minimum font
        #     size on one line must wrap onto multiple lines
        #     (each still within bounds) rather than overflow.
        # --------------------------------------------------

        very_long_text = (
            "An Extremely Long Thumbnail Overlay Text That Would "
            "Never Fit On One Line At All"
        )

        composed_very_long = composer.compose(
            Image.new("RGB", (1280, 720), color=(20, 30, 40)),
            text=very_long_text,
        )

        very_long_edge_region = composed_very_long.crop(
            (1270, 0, 1280, 300)
        )

        very_long_edge_colors = {
            pixel for pixel in very_long_edge_region.getdata()
        }

        if very_long_edge_colors != {(20, 30, 40)}:
            raise RuntimeError(
                "Expected even extremely long overlay text to "
                "wrap across multiple lines and stay within the "
                "frame - found non-background pixels at the "
                "right edge."
            )

        # --------------------------------------------------
        # 7d. ML-064: the bundled Barlow Condensed ExtraBold font
        #     file must actually exist on disk and be a valid
        #     font - if it's missing, every thumbnail silently
        #     falls back to a plainer system font instead.
        # --------------------------------------------------

        from sba_resolve.core.services.thumbnail_generator import (
            _bundled_font_path,
        )

        font_path = _bundled_font_path()

        if not font_path.is_file():
            raise RuntimeError(
                f"Expected the bundled font to exist at "
                f"{font_path}, but it's missing."
            )

        from PIL import ImageFont

        try:
            ImageFont.truetype(str(font_path), 48)
        except OSError as exc:
            raise RuntimeError(
                f"Bundled font file at {font_path} exists but "
                f"isn't a valid/loadable font: {exc}"
            )

        # --------------------------------------------------
        # 7e. ML-064: text rendering uses a soft drop shadow
        #     (a gradient of intermediate tones blending into
        #     the background), not the old hard black stroke -
        #     confirmed by checking for blended pixels distinct
        #     from both pure background and pure white text.
        # --------------------------------------------------

        background_colour = (80, 130, 190)

        shadow_source = Image.new("RGB", (1280, 720), color=background_colour)

        composed_shadow = composer.compose(shadow_source, text="RIDE")

        sample_region = composed_shadow.crop(
            (composer.TEXT_MARGIN, composer.TEXT_MARGIN, 400, 200)
        )

        sample_colours = {pixel for pixel in sample_region.getdata()}

        has_white_text = (255, 255, 255) in sample_colours

        has_blended_shadow_tones = any(
            colour != background_colour and colour != (255, 255, 255)
            for colour in sample_colours
        )

        if not has_white_text:
            raise RuntimeError(
                "Expected pure white (255, 255, 255) text pixels "
                "in the rendered thumbnail."
            )

        if not has_blended_shadow_tones:
            raise RuntimeError(
                "Expected a soft, blurred drop shadow (blended "
                "intermediate tones) around the text, not just a "
                "hard-edged background/white split."
            )

        # --------------------------------------------------
        # 8. A missing/invalid logo path is handled gracefully -
        #    the image comes back unchanged, no crash.
        # --------------------------------------------------

        composed_no_logo = composer.compose(
            Image.new("RGB", (1280, 720), color=(5, 5, 5)),
            text="",
            logo_path="/definitely/does/not/exist.png",
        )

        if composed_no_logo.getpixel((1200, 650)) != (5, 5, 5):
            raise RuntimeError(
                "Expected a missing logo path to leave the image "
                "unchanged, not raise or alter pixels."
            )

        # --------------------------------------------------
        # 9. A real logo file pastes into the bottom-right
        #    corner region.
        # --------------------------------------------------

        with tempfile.TemporaryDirectory() as tmp_dir:

            logo_path = Path(tmp_dir) / "logo.png"

            logo_image = Image.new(
                "RGBA", (200, 100), color=(255, 0, 0, 255)
            )
            logo_image.save(logo_path)

            composed_with_logo = composer.compose(
                Image.new("RGB", (1280, 720), color=(5, 5, 5)),
                text="",
                logo_path=str(logo_path),
            )

            corner_pixel = composed_with_logo.getpixel(
                (
                    1280 - composer.LOGO_MARGIN - 5,
                    720 - composer.LOGO_MARGIN - 5,
                )
            )

            if corner_pixel[:3] == (5, 5, 5):
                raise RuntimeError(
                    "Expected the logo to be visibly pasted into "
                    "the bottom-right corner, but the background "
                    "colour was still there."
                )

            # --------------------------------------------------
            # 10. save() writes a real, correctly-sized image
            #     file to disk.
            # --------------------------------------------------

            output_path = Path(tmp_dir) / "thumbnail.png"

            composer.save(composed_with_logo, output_path)

            if not output_path.is_file():
                raise RuntimeError(
                    "Expected save() to write a real file to disk."
                )

            with Image.open(output_path) as reopened:
                reopened_size = reopened.size

            if reopened_size != (1280, 720):
                raise RuntimeError(
                    f"Expected the saved file to be 1280x720, got "
                    f"{reopened_size!r}."
                )

    def _run_settings_loader_tests(self) -> None:

        import json

        from sba_resolve.core.services.app_settings import (
            load_thumbnail_logo_path,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:

            missing_path = Path(tmp_dir) / "does_not_exist.json"

            if load_thumbnail_logo_path(missing_path) != "":
                raise RuntimeError(
                    "Expected '' for a missing settings file."
                )

            malformed_path = Path(tmp_dir) / "malformed.json"
            malformed_path.write_text("{not valid json", encoding="utf-8")

            if load_thumbnail_logo_path(malformed_path) != "":
                raise RuntimeError(
                    "Expected '' for malformed JSON, not a raise."
                )

            valid_path = Path(tmp_dir) / "valid.json"
            valid_path.write_text(
                json.dumps({"thumbnail_logo_path": "D:/logos/sba.png"}),
                encoding="utf-8",
            )

            if load_thumbnail_logo_path(valid_path) != "D:/logos/sba.png":
                raise RuntimeError(
                    "Expected the configured logo path to be "
                    "returned when present and valid."
                )

            wrong_type_path = Path(tmp_dir) / "wrong_type.json"
            wrong_type_path.write_text(
                json.dumps({"thumbnail_logo_path": 12345}),
                encoding="utf-8",
            )

            if load_thumbnail_logo_path(wrong_type_path) != "":
                raise RuntimeError(
                    "Expected '' when the configured value isn't "
                    "a string, not a raise."
                )
