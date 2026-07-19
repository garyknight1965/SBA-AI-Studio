"""
============================================================
SBA AI Studio
IntelliScript Chapter Generator
Version : 1.0.0
Sprint  : ML-052
============================================================

Generates YouTube-style chapter markers from IntelliScript's
OWN keep/cut + paragraph-break decisions - not from raw Scene
Detection footage timing (see ChapterGenerator, ML-030, which
explicitly documents its timestamps only apply to raw,
unedited footage).

Because IntelliScript already knows exactly which segments were
kept and where paragraphs begin, this generator can compute each
chapter's REAL position in the edited video: the cumulative
duration of every KEPT segment before it, in original order (no
reordering happens anywhere in IntelliScript - only keep/cut).
This is the actual edited-timeline timing the old ChapterGenerator
could never produce.

This also adds something IntelliScript's own editorial pass never
does: a short SUBJECT/topic label per paragraph (e.g. "Tiger 900
Build Quality", "Tyre Review"), via one additional Ollama call
that reads each paragraph's already-assembled text. Like every
other AI step in this app, it is not allowed to invent facts -
it may only describe/summarize what the paragraph's own text
already says, never add new claims. A parse failure or a missing
label for any paragraph falls back to a generic "Chapter N" label
rather than blocking the whole result.

YouTube's real chapter requirements (checked here, matching
ChapterGenerator's own checks):
    - The first chapter must start at 0:00.
    - At least 3 chapters are required for YouTube to display
      them at all.
    - Each chapter must be at least 10 seconds long.
"""

from __future__ import annotations

import json
import re

from sba_resolve.core.models.transcript_segment import TranscriptSegment
from sba_resolve.core.services.intelliscript_assembler import (
    AssembledParagraph,
    IntelliScriptAssembler,
)
from sba_resolve.core.services.ollama_client import OllamaClient
from sba_resolve.core.services.timeline_fps import DEFAULT_PROJECT_FPS

MIN_CHAPTER_SECONDS = 10.0

MIN_CHAPTERS_FOR_YOUTUBE = 3

# Consolidation target - Gary's own choice, distinct from
# MIN_CHAPTER_SECONDS (YouTube's bare legal minimum above). One
# chapter per topic-paragraph produced far too many very short
# chapters on real transcripts; consecutive paragraphs are merged
# until each chapter reaches at least this long. See
# _consolidate_paragraphs().
DEFAULT_MIN_CHAPTER_SECONDS = 60.0

_FALLBACK_LABEL_PREFIX = "Chapter"


class IntelliScriptChapterGenerator:
    """
    Builds a chapter list from IntelliScript's assembled
    paragraphs, with real edited-video timestamps and AI-generated
    subject labels.
    """

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.ollama_client = ollama_client or OllamaClient()
        self.assembler = IntelliScriptAssembler()

    def generate(
        self,
        all_segments: list[TranscriptSegment],
        decisions: dict[int, dict],
        fps: float | None = None,
        min_chapter_seconds: float = DEFAULT_MIN_CHAPTER_SECONDS,
    ) -> dict:
        """
        Returns:
            {
                "chapters": [
                    {
                        "time_seconds": 0.0,
                        "time_text": "0:00",
                        "label": "Tiger 900 Build Quality",
                    },
                    ...
                ],
                "meets_youtube_requirements": True,
                "warnings": [...],
            }

        all_segments / decisions: exactly what
        IntelliScriptEditor.build_script() consumes/returns
        ("decisions" from its result dict) - this generator does
        not re-run any keep/cut editorial judgment, it only reads
        the same decisions already made.

        Consolidation: paragraphs are one-per-topic, which on a real
        transcript can produce many very short chapters back to
        back (Gary's own real transcript test case showed this).
        Per Gary's decision, consecutive paragraphs are merged
        together until each chapter reaches at least
        min_chapter_seconds (default 60s) before starting a new one
        - see _consolidate_paragraphs(). A merged chapter keeps the
        label of whichever paragraph STARTS it (the topic that
        opens that stretch of video), not a combined/summarized
        label - simplest and least likely to misrepresent content
        that was never re-read as a whole by the AI.
        """

        fps = fps if fps and fps > 0 else DEFAULT_PROJECT_FPS

        paragraphs = self.assembler.build_paragraphs(
            all_segments, decisions
        )

        paragraphs = [p for p in paragraphs if p.segments]

        if not paragraphs:
            return {
                "chapters": [],
                "meets_youtube_requirements": False,
                "warnings": ["No kept paragraphs to build chapters from."],
            }

        labels = self._generate_labels(paragraphs)

        durations = [
            sum(
                self._segment_duration_seconds(segment, fps)
                for segment in paragraph.segments
            )
            for paragraph in paragraphs
        ]

        chapters = self._consolidate_paragraphs(
            labels, durations, min_chapter_seconds
        )

        # Guard against float noise - the first chapter must be
        # exactly 0:00 by YouTube's rules, and should already be
        # by construction.
        chapters[0]["time_seconds"] = 0.0
        chapters[0]["time_text"] = "0:00"

        warnings = self._check_requirements(chapters)

        return {
            "chapters": chapters,
            "meets_youtube_requirements": not warnings,
            "warnings": warnings,
        }

    @staticmethod
    def _consolidate_paragraphs(
        labels: list[str],
        durations: list[float],
        min_chapter_seconds: float,
    ) -> list[dict]:
        """
        Groups consecutive paragraphs into chapters so each chapter
        (except possibly the last) covers at least
        min_chapter_seconds. A chapter's label is the label of the
        paragraph that STARTS its group - later paragraphs folded
        into the same group don't get their own marker or affect
        the label, only extend how long this chapter runs before
        the next one starts.

        The final group is a special case: if it doesn't reach
        min_chapter_seconds on its own (there's simply not enough
        video left), it's merged backward into the previous chapter
        instead of being left as a too-short trailing chapter -
        unless it's the ONLY group, in which case it's kept as the
        sole chapter regardless of length (there's nothing to merge
        it into).
        """

        chapters: list[dict] = []

        elapsed_seconds = 0.0
        group_start_seconds = 0.0
        group_label = labels[0]
        group_duration = 0.0

        for index, duration in enumerate(durations):

            if group_duration == 0.0:
                group_start_seconds = elapsed_seconds
                group_label = labels[index]

            group_duration += duration
            elapsed_seconds += duration

            is_last = index == len(durations) - 1

            if group_duration >= min_chapter_seconds or is_last:

                chapters.append(
                    {
                        "time_seconds": group_start_seconds,
                        "time_text": IntelliScriptChapterGenerator._format_time(
                            group_start_seconds
                        ),
                        "label": group_label,
                    }
                )

                group_duration = 0.0

        # Merge a too-short trailing group backward into the
        # previous chapter, unless it's the only chapter there is.
        if len(chapters) >= 2:

            last_chapter_duration = (
                elapsed_seconds - chapters[-1]["time_seconds"]
            )

            if last_chapter_duration < min_chapter_seconds:
                chapters.pop()

        return chapters

    # -----------------------------------------------------
    # Timing
    # -----------------------------------------------------

    @staticmethod
    def _segment_duration_seconds(
        segment: TranscriptSegment, fps: float
    ) -> float:

        start = IntelliScriptChapterGenerator._timecode_to_seconds(
            segment.start_timecode, fps
        )
        end = IntelliScriptChapterGenerator._timecode_to_seconds(
            segment.end_timecode, fps
        )

        return max(0.0, end - start)

    @staticmethod
    def _timecode_to_seconds(timecode: str, fps: float) -> float:
        """
        Parses a Resolve-style HH:MM:SS:FF timecode into seconds.
        Falls back to treating it as HH:MM:SS (no frames field)
        if only 3 parts are present, rather than raising - a
        malformed/unexpected timecode format should degrade
        gracefully, not crash chapter generation entirely.
        """

        parts = timecode.split(":")

        try:
            if len(parts) == 4:
                hours, minutes, seconds, frames = (int(p) for p in parts)
                return (
                    hours * 3600
                    + minutes * 60
                    + seconds
                    + (frames / fps if fps else 0.0)
                )
            if len(parts) == 3:
                hours, minutes, seconds = (int(p) for p in parts)
                return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            pass

        return 0.0

    @staticmethod
    def _format_time(total_seconds: float) -> str:

        total_seconds = max(0, round(total_seconds))

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"

        return f"{minutes}:{seconds:02d}"

    # -----------------------------------------------------
    # Topic labeling (new AI step, not part of IntelliScriptEditor)
    # -----------------------------------------------------

    def _generate_labels(
        self, paragraphs: list[AssembledParagraph]
    ) -> list[str]:
        """
        Returns one label per paragraph, same order. Falls back to
        "Chapter N" for any paragraph whose label couldn't be
        determined (parse failure, missing index, empty string) -
        a labeling problem should never block chapter generation
        entirely, since the timing is still correct and useful
        even with a generic label.
        """

        fallback = [
            f"{_FALLBACK_LABEL_PREFIX} {i + 1}"
            for i in range(len(paragraphs))
        ]

        prompt = self._build_label_prompt(paragraphs)

        raw_response = self.ollama_client.generate(prompt)

        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)

        if not json_match:
            return fallback

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return fallback

        raw_labels = data.get("labels")

        if not isinstance(raw_labels, list):
            return fallback

        labels = list(fallback)

        for index, label in enumerate(raw_labels):

            if index >= len(labels):
                break

            if isinstance(label, str) and label.strip():
                labels[index] = label.strip()

        return labels

    @staticmethod
    def _build_label_prompt(
        paragraphs: list[AssembledParagraph],
    ) -> str:

        paragraph_lines = [
            f"{index}: {paragraph.text}"
            for index, paragraph in enumerate(paragraphs)
        ]

        paragraphs_text = "\n\n".join(paragraph_lines)

        last_index = len(paragraphs) - 1

        return f"""Act as a video editor writing YouTube chapter labels
for a motorcycle vlog.

Below is a numbered list of paragraphs from the video's script,
already grouped by topic. For EACH paragraph, write a short
chapter label (2-6 words) that accurately describes what that
paragraph is actually about.

CRITICAL: only describe/summarize what the paragraph's own text
actually says. Do not invent, guess, or add any detail, fact, or
claim that isn't already in the paragraph's text - a chapter
label is a short description of existing content, never new
content of its own.

Paragraphs:
{paragraphs_text}

Respond with ONLY a JSON object, no other text, in exactly this
shape:

{{
  "labels": ["label for paragraph 0", "label for paragraph 1", "..."]
}}

Include EVERY index from 0 to {last_index}, in order, with no
gaps.
"""

    # -----------------------------------------------------
    # YouTube requirement checks (same rules as ChapterGenerator)
    # -----------------------------------------------------

    @staticmethod
    def _check_requirements(chapters: list[dict]) -> list[str]:

        warnings = []

        if len(chapters) < MIN_CHAPTERS_FOR_YOUTUBE:
            warnings.append(
                f"Only {len(chapters)} chapter(s) - YouTube "
                f"requires at least {MIN_CHAPTERS_FOR_YOUTUBE} "
                f"to display chapters at all."
            )

        for index in range(1, len(chapters)):

            gap = (
                chapters[index]["time_seconds"]
                - chapters[index - 1]["time_seconds"]
            )

            if gap < MIN_CHAPTER_SECONDS:
                warnings.append(
                    f"'{chapters[index - 1]['label']}' is only "
                    f"{gap:.0f}s before '{chapters[index]['label']}' "
                    f"- YouTube requires each chapter to be at "
                    f"least {MIN_CHAPTER_SECONDS:.0f}s."
                )

        return warnings

    # -----------------------------------------------------
    # Description formatting (matches ChapterGenerator's helper)
    # -----------------------------------------------------

    @staticmethod
    def format_for_description(chapter_result: dict) -> str:
        """
        Renders this generator's chapters as ready-to-paste text
        for a YouTube video description.
        """

        return "\n".join(
            f"{chapter['time_text']} {chapter['label']}"
            for chapter in chapter_result["chapters"]
        )
