"""
============================================================
SBA AI Studio
Transcript Segment
Version : 1.0.0
Sprint  : ML-034
============================================================

One block from a DaVinci Resolve transcript export:

    [00:01:00:00 - 00:01:10:00]
    Speaker 1
     I tell you about my positive things about my TIGER.

A segment with no speaker line (a pure sound-effect block, e.g.
"(Wind Blowing)") has speaker=None and is never sent to the AI -
it's dropped automatically, before any editorial judgment is
needed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptSegment:
    """
    One timecoded block from a Resolve transcript export.
    """

    index: int

    start_timecode: str
    end_timecode: str

    speaker: str | None
    text: str

    @property
    def is_speech(self) -> bool:
        """
        False for a pure sound-effect block (no speaker line at
        all) or a speaker line with no actual text - these are
        dropped automatically and never reach the AI.
        """
        return self.speaker is not None and bool(self.text.strip())
