"""
============================================================
SBA AI Studio
IntelliScript Assembler
Version : 1.1.0
Sprint  : ML-034 / ML-052 (paragraph structure for chapters)
============================================================

Builds the final IntelliScript-ready script from a list of ALL
parsed transcript segments plus a keep/paragraph-break decision
per speech segment.

This is deliberately the only place original words are ever
touched, and it only ever does two small, fixed, mechanical
things - never a reword, never a paraphrase:

    1. If a kept segment immediately follows a CUT segment and
       starts with a leading connector word ("And", "But", "So",
       "Then"), that connector is dropped and the next word is
       re-capitalised (e.g. "And the eight," -> "The eight,").
       Case only changes on the word that already existed - no
       word is ever added, removed, or reworded otherwise.

    2. If a kept segment immediately precedes a CUT segment (or
       is the last segment overall) and its text ends in a
       trailing comma, that comma becomes a period, since the
       sentence it used to continue into no longer exists.

Every other character of every kept segment is reproduced
exactly as transcribed. The AI decides WHICH segments to keep
and WHERE paragraphs begin - it never supplies replacement text,
and this assembler has no way to accept any.

ML-052: build_paragraphs() exposes the same grouping this always
did, but structured per-paragraph (original TranscriptSegment
objects + assembled text) rather than only a flat joined string.
This is what IntelliScriptChapterGenerator uses to compute real
edited-video timestamps (from each paragraph's segments' actual
durations) and topic labels (from each paragraph's text) -
without duplicating the connector/comma-fix logic here.
assemble()'s own behavior and output are UNCHANGED - it's now a
thin wrapper over build_paragraphs().
"""

from __future__ import annotations

from dataclasses import dataclass

from sba_resolve.core.models.transcript_segment import TranscriptSegment

_LEADING_CONNECTORS = ("And ", "But ", "So ", "Then ")


@dataclass(slots=True)
class AssembledParagraph:
    """
    One paragraph's original kept segments plus its assembled
    text (connector/comma fixes already applied, same as what
    assemble() would have produced for this paragraph alone).
    """

    segments: list[TranscriptSegment]
    text: str


class IntelliScriptAssembler:
    """
    Deterministically assembles the final script text. Given the
    same segments and decisions, always produces the same output.
    """

    def assemble(
        self,
        all_segments: list[TranscriptSegment],
        decisions: dict[int, dict],
    ) -> str:

        paragraphs = self.build_paragraphs(all_segments, decisions)

        return (
            "\n\n".join(paragraph.text for paragraph in paragraphs) + "\n"
        )

    def build_paragraphs(
        self,
        all_segments: list[TranscriptSegment],
        decisions: dict[int, dict],
    ) -> list[AssembledParagraph]:
        """
        Same grouping logic assemble() has always used, but
        returning structured per-paragraph data (kept segments +
        assembled text) instead of only a flat string.
        """

        total = len(all_segments)

        def is_kept(segment: TranscriptSegment) -> bool:
            return segment.is_speech and decisions.get(
                segment.index, {}
            ).get("keep", False)

        paragraphs: list[AssembledParagraph] = []
        current_segments: list[TranscriptSegment] = []
        current_parts: list[str] = []

        for position, segment in enumerate(all_segments):

            if not is_kept(segment):
                continue

            decision = decisions[segment.index]

            text = segment.text

            previous_segment = (
                all_segments[position - 1] if position > 0 else None
            )
            next_segment = (
                all_segments[position + 1]
                if position < total - 1
                else None
            )

            preceded_by_cut = (
                previous_segment is None
                or not is_kept(previous_segment)
            )
            followed_by_cut = (
                next_segment is None or not is_kept(next_segment)
            )

            if preceded_by_cut:
                text = self._strip_leading_connector(text)

            if followed_by_cut:
                text = self._fix_trailing_comma(text)

            if decision.get("paragraph_break_before") and current_parts:
                paragraphs.append(
                    AssembledParagraph(
                        segments=current_segments,
                        text=" ".join(current_parts),
                    )
                )
                current_segments = []
                current_parts = []

            current_segments.append(segment)
            current_parts.append(text)

        if current_parts:
            paragraphs.append(
                AssembledParagraph(
                    segments=current_segments,
                    text=" ".join(current_parts),
                )
            )

        return paragraphs

    # -----------------------------------------------------

    @staticmethod
    def _strip_leading_connector(text: str) -> str:

        for connector in _LEADING_CONNECTORS:

            if text.startswith(connector):

                remainder = text[len(connector):]

                if remainder:
                    remainder = remainder[0].upper() + remainder[1:]

                return remainder

        return text

    @staticmethod
    def _fix_trailing_comma(text: str) -> str:

        stripped = text.rstrip()

        if stripped.endswith(","):
            return stripped[:-1] + "."

        return text
