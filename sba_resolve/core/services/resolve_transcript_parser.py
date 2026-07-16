"""
============================================================
SBA AI Studio
Resolve Transcript Parser
Version : 1.0.0
Sprint  : ML-034
============================================================

Parses a DaVinci Resolve transcript export (plain text, one
timecoded block per entry) into ordered TranscriptSegment
objects.

Block shape:

    [00:01:00:00 - 00:01:10:00]
    Speaker 1
     I tell you about my positive things about my TIGER.

    [00:12:02:22 - 00:12:13:03]
     (Wind Blowing)

A block with no "Speaker N" line is a pure sound-effect entry -
parsed with speaker=None, never a text rewrite.
"""

from __future__ import annotations

import re
from pathlib import Path

from sba_resolve.core.models.transcript_segment import TranscriptSegment

_TIMECODE_RE = re.compile(
    r"^\[(?P<start>[\d:]+)\s*-\s*(?P<end>[\d:]+)\]$"
)

_SPEAKER_RE = re.compile(r"^Speaker\s+\d+$")


class ResolveTranscriptParser:
    """
    Parses raw Resolve transcript export text into
    TranscriptSegment objects, in original order.
    """

    def parse(self, raw_text: str) -> list[TranscriptSegment]:

        lines = raw_text.splitlines()

        segments: list[TranscriptSegment] = []

        index = 0
        position = 0
        total = len(lines)

        while position < total:

            line = lines[position].strip()

            if not line:
                position += 1
                continue

            match = _TIMECODE_RE.match(line)

            if not match:
                # Content outside a recognised timecode block -
                # skip defensively rather than crash on an
                # unexpected export format quirk.
                position += 1
                continue

            start = match.group("start")
            end = match.group("end")

            position += 1

            speaker = None

            if position < total and _SPEAKER_RE.match(
                lines[position].strip()
            ):
                speaker = lines[position].strip()
                position += 1

            text_lines = []

            while position < total and lines[position].strip() != "":
                text_lines.append(lines[position].strip())
                position += 1

            text = re.sub(r"\s+", " ", " ".join(text_lines)).strip()

            segments.append(
                TranscriptSegment(
                    index=index,
                    start_timecode=start,
                    end_timecode=end,
                    speaker=speaker,
                    text=text,
                )
            )

            index += 1

        return segments

    def parse_file(self, path: str | Path) -> list[TranscriptSegment]:
        """
        Convenience wrapper: parse a transcript export file from
        disk.
        """

        return self.parse(Path(path).read_text(encoding="utf-8"))
