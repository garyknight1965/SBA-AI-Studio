"""
youtube_chapter_parser.py

ML-055. Parses (time_seconds, label) chapter pairs directly out of the
live YouTube Metadata description text (ui/widgets/youtube_metadata_widget.py's
description_field), not from IntelliScriptChapterGenerator's internal
model -- so whatever Gary has actually typed/edited in that panel before
publishing is exactly what drives the chapter title cards.

Uses YouTube's own required chapter-line syntax as the parse target
(M:SS or H:MM:SS followed by a label), the same format
IntelliScriptChapterGenerator._format_time() already produces -- so this
works whether Gary leaves the generated text untouched, edits labels,
adds a chapter by hand, or removes the caveat/header line entirely.
"""

import re
from dataclasses import dataclass

_CHAPTER_LINE_RE = re.compile(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s+(.+)$")


@dataclass
class ParsedChapter:
    time_seconds: float
    label: str


def parse_chapters_from_description(description_text: str) -> list[ParsedChapter]:
    """Extracts every valid YouTube-chapter-format line from
    description_text, in the order they appear. Lines that don't match
    the M:SS/H:MM:SS + label pattern are ignored (this deliberately
    does NOT require a specific header like "Chapters:" -- YouTube
    itself doesn't require one either).

    Returns an empty list if nothing matches -- callers should treat
    that as "no chapters to place" rather than an error, since Gary
    may not have generated/kept any chapter lines.
    """
    chapters = []
    for line in description_text.splitlines():
        match = _CHAPTER_LINE_RE.match(line.strip())
        if not match:
            continue
        hours_str, minutes_str, seconds_str, label = match.groups()
        hours = int(hours_str) if hours_str else 0
        minutes = int(minutes_str)
        seconds = int(seconds_str)
        total_seconds = hours * 3600 + minutes * 60 + seconds
        chapters.append(
            ParsedChapter(time_seconds=float(total_seconds), label=label.strip())
        )
    return chapters