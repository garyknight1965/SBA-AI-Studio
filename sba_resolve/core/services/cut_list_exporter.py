"""
cut_list_exporter.py

ML-047 precursor / standalone fix, per Gary's real complaint (2026-07-20):
manually cutting video using IntelliScript's kept-segment timecodes was
clipping the start/end of words, because those timecodes are Resolve's
own transcript-export block boundaries, passed through completely
unmodified by resolve_transcript_parser.py - Resolve draws those
boundaries tight to detected speech, with zero built-in handle/padding.

This module adds a small time HANDLE (extra time borrowed from the
adjacent footage, still present in the source media, just outside the
strict transcript boundary) to the start and end of each contiguous run
of KEPT segments, so a manual cut using these adjusted timecodes leaves
a bit of breathing room instead of clipping consonants.

Deliberately separate from IntelliScriptAssembler - that module's whole
design point is NEVER touching timing, only text. This module is the
opposite: it never touches text, only timing.

KNOWN LIMITATION (flagged, not solved): if two kept runs are separated
by a cut segment shorter than 2x the handle duration, the two runs'
handles can overlap inside that short cut segment - meaning a sliver of
"cut" content ends up included on both sides. This is a rare edge case
with short cuts; not automatically resolved here. Report back if this
causes a real problem so it can be addressed properly (e.g. shrinking
the handle only for that specific short gap) rather than guessed at now.
"""

from __future__ import annotations

from dataclasses import dataclass

from sba_resolve.core.models.transcript_segment import TranscriptSegment

DEFAULT_HANDLE_SECONDS = 0.4


@dataclass(slots=True)
class CutListEntry:
    start_timecode: str
    end_timecode: str
    text: str


def timecode_to_seconds(timecode: str, fps: float) -> float:
    """Converts a Resolve-style HH:MM:SS:FF timecode to total seconds,
    given the project's frame rate. Raises ValueError on a malformed
    timecode rather than silently returning 0 - a bad conversion here
    would silently produce wrong cut points.
    """
    parts = timecode.strip().split(":")
    if len(parts) != 4:
        raise ValueError(
            f"Expected a 4-part HH:MM:SS:FF timecode, got '{timecode}'."
        )
    hours, minutes, seconds, frames = (int(part) for part in parts)
    return hours * 3600 + minutes * 60 + seconds + (frames / fps)


def seconds_to_timecode(total_seconds: float, fps: float) -> str:
    """Converts total seconds back to a Resolve-style HH:MM:SS:FF
    timecode at the given frame rate. Clamps negative input to 0 rather
    than producing a negative/invalid timecode.
    """
    total_seconds = max(0.0, total_seconds)
    frame_rate = round(fps)
    total_frames = round(total_seconds * fps)
    frames = total_frames % frame_rate
    whole_seconds = total_frames // frame_rate
    seconds = whole_seconds % 60
    total_minutes = whole_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def build_cut_list(
    all_segments: list[TranscriptSegment],
    decisions: dict[int, dict],
    fps: float,
    handle_seconds: float = DEFAULT_HANDLE_SECONDS,
) -> list[CutListEntry]:
    """Groups consecutive KEPT segments into contiguous runs (ignoring
    paragraph_break_before, which is a text/topic grouping only and
    does not imply a cut - two paragraphs can be fully consecutive in
    the source footage with no cut between them at all), then returns
    one CutListEntry per run with handle_seconds subtracted from the
    run's start and added to its end.

    Text in each entry is the raw joined segment text for that run
    (NOT the connector/comma-fixed text IntelliScriptAssembler
    produces) - this is a cutting reference, not the final script.
    """

    def is_kept(segment: TranscriptSegment) -> bool:
        return segment.is_speech and decisions.get(
            segment.index, {}
        ).get("keep", False)

    entries: list[CutListEntry] = []
    run_segments: list[TranscriptSegment] = []

    for segment in all_segments:
        if is_kept(segment):
            run_segments.append(segment)
            continue

        if run_segments:
            entries.append(_build_entry(run_segments, fps, handle_seconds))
            run_segments = []

    if run_segments:
        entries.append(_build_entry(run_segments, fps, handle_seconds))

    return entries


def _build_entry(
    run_segments: list[TranscriptSegment], fps: float, handle_seconds: float
) -> CutListEntry:
    start_seconds = timecode_to_seconds(
        run_segments[0].start_timecode, fps
    ) - handle_seconds
    end_seconds = timecode_to_seconds(
        run_segments[-1].end_timecode, fps
    ) + handle_seconds

    text = " ".join(segment.text for segment in run_segments)

    return CutListEntry(
        start_timecode=seconds_to_timecode(start_seconds, fps),
        end_timecode=seconds_to_timecode(end_seconds, fps),
        text=text,
    )


def format_cut_list(entries: list[CutListEntry], handle_seconds: float) -> str:
    """Formats entries as plain text, one block per entry, in the same
    general [start - end] style as a Resolve transcript export, so
    it's immediately familiar to read.
    """
    lines = [
        f"Cut list - handle: -{handle_seconds:.1f}s / +{handle_seconds:.1f}s "
        f"applied to each range's start/end.\n"
    ]
    for entry in entries:
        lines.append(f"[{entry.start_timecode} - {entry.end_timecode}]")
        lines.append(f" {entry.text}")
        lines.append("")
    return "\n".join(lines)