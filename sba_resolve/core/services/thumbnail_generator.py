"""
============================================================
SBA AI Studio
Thumbnail Generator
ML-061
Version : 1.0.0
============================================================

Suggests a handful of candidate still frames from a ride day's real
footage, and composites a chosen frame with an overlay text
(typically the AI-generated thumbnail_text from
YouTubeMetadataGenerator, ML-059) and the channel's logo into a
finished YouTube thumbnail (1280x720 PNG).

Frame extraction reads directly from the source media files via cv2
(already a project dependency) - no Resolve connection required, so
this works the same way whether triggered from the GUI or a
standalone script.

Candidate frames are chosen deterministically (evenly spread across
the day's clips, in real capture order) rather than "AI-picked" -
judging which single frame looks best (composition, motion blur,
whether the subject is actually in frame) isn't something either an
LLM or this code can reliably judge, so Gary picks from a handful of
real candidates himself instead, matching the project's "never
guess" philosophy.

Text/logo compositing uses Pillow rather than cv2's own text
rendering - cv2 only offers a handful of built-in Hershey fonts with
no anti-aliasing or custom TrueType support, not good enough for
something meant to look like a real, professional thumbnail.

ML-063 (2026-07-23): overlay text is now auto-fitted within the
frame - the font size shrinks to fit the available width, and text
that still doesn't fit at a reasonable minimum size wraps across up
to 3 lines instead. The original version drew text at a fixed size
with no width check at all, letting longer suggested text (e.g.
"Motorcycle Touring Netherlands") run straight off the right edge of
a real saved thumbnail.

ML-064 (2026-07-23, per Gary's request): text style is now Barlow
Condensed ExtraBold (bundled with the app, SIL Open Font License -
see assets/fonts/OFL.txt), white, with a soft drop shadow instead of
the earlier black stroke outline - a common real YouTube-thumbnail
look. Bundled the same way ExifTool already is (extracted fresh to
sys._MEIPASS on every launch of the packaged .exe - see
exiftool_engine.py's _bundled_exiftool_path() for the identical
pattern), so this works in both source and packaged-.exe runs
without needing the font installed system-wide.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def _bundled_font_path() -> Path:
    """
    Resolves the bundled assets/fonts/BarlowCondensed-ExtraBold.ttf
    location - same pattern as exiftool_engine.py's
    _bundled_exiftool_path(): when running as a PyInstaller ONEFILE
    build, bundled data files are extracted fresh to a temporary
    folder on every launch (sys._MEIPASS), not next to the real .exe.
    When running from source, resolves relative to the project root
    (three levels up from this file's location:
    sba_resolve/core/services/).
    """

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return (
                Path(meipass)
                / "assets" / "fonts" / "BarlowCondensed-ExtraBold.ttf"
            )

    return (
        Path(__file__).resolve().parents[3]
        / "assets" / "fonts" / "BarlowCondensed-ExtraBold.ttf"
    )


@dataclass(slots=True)
class ThumbnailCandidate:
    """
    One candidate still frame suggested for a thumbnail.

    `image` is loosely typed (not annotated as numpy.ndarray) so this
    module doesn't force a hard numpy/cv2 import just to describe the
    dataclass shape - callers that only need candidate metadata (e.g.
    tests using a fake frame reader) aren't forced to have those
    installed either.
    """

    clip_name: str

    timestamp_seconds: float

    image: object


class ThumbnailFrameExtractor:
    """
    Suggests candidate still frames from a set of MediaFiles, and
    extracts the actual pixel data for each suggested candidate.
    """

    def __init__(
        self,
        frame_reader: Callable[[str, float], object] | None = None,
    ):
        """
        frame_reader(file_path, timestamp_seconds) -> image | None

        Defaults to a real cv2-based reader. Tests inject a fake
        reader instead, so this class never needs a real video file
        on disk to be exercised.
        """

        self.frame_reader = frame_reader or self._read_frame_cv2

    def suggest_candidates(
        self,
        media_files: list,
        count: int = 5,
    ) -> list[ThumbnailCandidate]:
        """
        Picks up to `count` clips evenly spread across the given
        media_files (assumed already sorted in capture order by the
        caller - e.g. one ride day's clips), and extracts the
        midpoint frame of each as a candidate.

        Clips with no known duration, or where frame extraction
        fails, are silently skipped rather than raising - a missing
        candidate isn't fatal here, Gary just sees fewer options to
        pick from.
        """

        usable = [
            media
            for media in media_files
            if self._duration_seconds(media) is not None
            and self._duration_seconds(media) > 0
        ]

        if not usable:
            return []

        count = max(1, min(count, len(usable)))

        if count == 1:
            indices = [0]
        else:
            indices = [
                round(i * (len(usable) - 1) / (count - 1))
                for i in range(count)
            ]

        # De-duplicate while preserving order (evenly-spaced rounding
        # can land on the same index twice for a short list).
        seen_indices = []
        for index in indices:
            if index not in seen_indices:
                seen_indices.append(index)

        candidates = []

        for index in seen_indices:

            media = usable[index]

            duration = self._duration_seconds(media)

            midpoint = duration / 2.0

            image = self.frame_reader(str(media.full_path), midpoint)

            if image is None:
                continue

            candidates.append(
                ThumbnailCandidate(
                    clip_name=media.filename,
                    timestamp_seconds=midpoint,
                    image=image,
                )
            )

        return candidates

    @staticmethod
    def _duration_seconds(media) -> float | None:

        duration = getattr(media, "duration", None)

        if duration is None:
            return None

        try:
            return float(duration)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _read_frame_cv2(file_path: str, timestamp_seconds: float):

        import cv2

        capture = cv2.VideoCapture(file_path)

        try:

            if not capture.isOpened():
                return None

            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)

            success, frame = capture.read()

            return frame if success else None

        finally:
            capture.release()


class ThumbnailComposer:
    """
    Composites a chosen still frame with overlay text and (optionally)
    a logo image into a finished 1280x720 YouTube thumbnail.
    """

    OUTPUT_SIZE = (1280, 720)

    TEXT_MARGIN = 60

    LOGO_MARGIN = 40

    # Logo width capped at this fraction of the thumbnail's width, so
    # an oversized logo file can never swamp the frame underneath it.
    LOGO_MAX_WIDTH_FRACTION = 0.18

    def compose(
        self,
        frame_image,
        text: str = "",
        logo_path: str | None = None,
    ):
        """
        Returns a PIL.Image.Image, ready to .save() or hand back to
        the GUI for preview.

        frame_image: a BGR numpy array (as returned by
        ThumbnailFrameExtractor/cv2), OR an existing PIL.Image.Image
        (accepted directly so callers - including tests - can pass a
        synthetic image without needing numpy/cv2 at all).
        """

        pil_image = self._to_pil_image(frame_image)

        pil_image = self._fit_to_output_size(pil_image)

        pil_image = pil_image.convert("RGB")

        if text.strip():
            pil_image = self._draw_text(pil_image, text.strip())

        if logo_path:
            pil_image = self._paste_logo(pil_image, logo_path)

        return pil_image

    def save(self, composed_image, output_path) -> None:

        output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        composed_image.save(output_path)

    def _to_pil_image(self, frame_image):

        from PIL import Image

        if isinstance(frame_image, Image.Image):
            return frame_image

        array = frame_image

        # Assume a BGR numpy array (cv2's native format) - convert to
        # RGB for PIL.
        if (
            hasattr(array, "shape")
            and len(array.shape) == 3
            and array.shape[2] == 3
        ):
            array = array[:, :, ::-1]

        return Image.fromarray(array)

    def _fit_to_output_size(self, pil_image):
        """
        Resizes+crops (cover-fit, not stretch) to exactly
        OUTPUT_SIZE, so every thumbnail is the correct YouTube
        dimensions regardless of the source clip's native aspect
        ratio.
        """

        target_w, target_h = self.OUTPUT_SIZE

        source_w, source_h = pil_image.size

        target_ratio = target_w / target_h
        source_ratio = source_w / source_h

        if source_ratio > target_ratio:
            new_h = target_h
            new_w = round(new_h * source_ratio)
        else:
            new_w = target_w
            new_h = round(new_w / source_ratio)

        resized = pil_image.resize((new_w, new_h))

        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2

        return resized.crop((left, top, left + target_w, top + target_h))

    def _draw_text(self, pil_image, text):

        from PIL import Image, ImageDraw, ImageFilter

        max_width = pil_image.width - (2 * self.TEXT_MARGIN)

        measure_draw = ImageDraw.Draw(pil_image)

        font, lines = self._fit_text(
            measure_draw, text, pil_image.width, max_width
        )

        line_height = self._text_line_height(measure_draw, font)

        # ML-064: soft drop shadow instead of a stroke outline - a
        # common real YouTube-thumbnail look. Shadow text is drawn
        # offset on its own transparent layer, blurred, then
        # composited underneath the crisp white text on top.
        shadow_offset = max(3, pil_image.width // 250)
        shadow_blur = max(2, pil_image.width // 350)

        shadow_layer = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)

        y = self.TEXT_MARGIN

        for line in lines:
            shadow_draw.text(
                (self.TEXT_MARGIN + shadow_offset, y + shadow_offset),
                line,
                font=font,
                fill=(0, 0, 0, 200),
            )
            y += line_height

        shadow_layer = shadow_layer.filter(
            ImageFilter.GaussianBlur(shadow_blur)
        )

        composited = Image.alpha_composite(
            pil_image.convert("RGBA"), shadow_layer
        )

        draw = ImageDraw.Draw(composited)

        y = self.TEXT_MARGIN

        for line in lines:
            draw.text(
                (self.TEXT_MARGIN, y),
                line,
                font=font,
                fill=(255, 255, 255, 255),
            )
            y += line_height

        return composited.convert("RGB")

    def _fit_text(self, draw, text, image_width, max_width):
        """
        Finds a font size (and, if needed, a word-wrapped set of
        lines) that keeps every line within max_width - the earlier
        version used a fixed font size with no width check at all,
        which let longer suggested text run straight off the edge
        of the frame instead of fitting inside it.

        Tries progressively smaller font sizes first (single line);
        if even the smallest reasonable size still doesn't fit on
        one line, wraps the text across up to 3 lines instead so it
        stays legible rather than shrinking to the point of being
        unreadable.
        """

        base_size = image_width // 12
        min_size = max(18, image_width // 30)

        size = base_size

        while size > min_size:
            font = self._load_font_at_size(size)
            if draw.textlength(text, font=font) <= max_width:
                return font, [text]
            size -= 2

        # Doesn't fit on one line even at the minimum size - wrap
        # across multiple lines at the minimum size instead.
        font = self._load_font_at_size(min_size)

        lines = self._wrap_text(draw, text, font, max_width, max_lines=3)

        return font, lines

    @staticmethod
    def _wrap_text(draw, text, font, max_width, max_lines):
        """
        Simple greedy word-wrap: fills each line with as many words
        as fit within max_width. If the text still doesn't fit
        within max_lines, the last line is truncated with an
        ellipsis rather than overflowing further lines off the
        bottom of the frame.
        """

        words = text.split()

        lines = []
        current_line = ""

        for word in words:

            candidate = f"{current_line} {word}".strip()

            if draw.textlength(candidate, font=font) <= max_width:
                current_line = candidate
                continue

            if current_line:
                lines.append(current_line)

            current_line = word

            if len(lines) == max_lines:
                break

        if current_line and len(lines) < max_lines:
            lines.append(current_line)

        if not lines:
            lines = [text]

        if len(lines) > max_lines:
            lines = lines[:max_lines]

        # If the last line itself is still too wide (a single very
        # long word), truncate it with an ellipsis rather than let
        # it run off the edge.
        last_line = lines[-1]

        while (
            draw.textlength(f"{last_line}...", font=font) > max_width
            and len(last_line) > 1
        ):
            last_line = last_line[:-1]

        if last_line != lines[-1]:
            lines[-1] = f"{last_line}..."

        return lines

    @staticmethod
    def _text_line_height(draw, font):

        bbox = draw.textbbox((0, 0), "Ag", font=font)

        return (bbox[3] - bbox[1]) + 10

    def _load_font(self, image_width):

        return self._load_font_at_size(image_width // 12)

    @staticmethod
    def _load_font_at_size(font_size):

        from PIL import ImageFont

        # ML-064: Barlow Condensed ExtraBold, per Gary's request -
        # bundled with the app (see _bundled_font_path()), tried
        # first. Falls back to common system bold fonts, then
        # Pillow's built-in default font, rather than raising if
        # the bundled font is somehow missing.
        candidate_paths = [
            str(_bundled_font_path()),
            "arialbd.ttf",
            "Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

        for candidate in candidate_paths:
            try:
                return ImageFont.truetype(candidate, font_size)
            except OSError:
                continue

        return ImageFont.load_default()

    def _paste_logo(self, pil_image, logo_path):

        from PIL import Image

        logo_path = Path(logo_path)

        if not logo_path.is_file():
            return pil_image

        try:
            with Image.open(logo_path) as logo_file:
                # .convert() returns a new, independent Image object,
                # so it's safe to keep using `logo` after the `with`
                # block closes the underlying file handle.
                logo = logo_file.convert("RGBA")
        except Exception:
            return pil_image

        pil_image = pil_image.copy()

        max_logo_width = round(
            pil_image.width * self.LOGO_MAX_WIDTH_FRACTION
        )

        if logo.width > max_logo_width and logo.width > 0:
            scale = max_logo_width / logo.width
            logo = logo.resize(
                (max_logo_width, max(1, round(logo.height * scale)))
            )

        position = (
            pil_image.width - logo.width - self.LOGO_MARGIN,
            pil_image.height - logo.height - self.LOGO_MARGIN,
        )

        pil_image.paste(logo, position, mask=logo)

        return pil_image
