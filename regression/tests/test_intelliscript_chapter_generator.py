"""
============================================================
SBA AI Studio
IntelliScript Chapter Generator Regression Test
ML-052
Version : 1.0.0
============================================================

Verifies IntelliScriptChapterGenerator's timing math (cumulative
duration of KEPT segments only, in original order) and its
topic-label parsing (clean JSON, missing/short response falling
back to generic labels rather than crashing) using fake segments
and a fake Ollama client - no real transcript, network, or model
involved.
"""

from __future__ import annotations

import json

from regression.base_test import BaseRegressionTest


class FakeLabelClient:

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response_text


class IntelliScriptChapterGeneratorRegressionTest(BaseRegressionTest):

    name = "IntelliScript Chapter Generator (ML-052)"

    category = "Planning"

    description = (
        "Verify real edited-video timing math (cumulative kept-"
        "segment duration, cut segments excluded entirely) and "
        "topic-label parsing/fallback using fake segments and a "
        "fake Ollama client."
    )

    def run(self) -> None:

        from sba_resolve.core.models.transcript_segment import (
            TranscriptSegment,
        )
        from sba_resolve.core.services.intelliscript_chapter_generator import (
            IntelliScriptChapterGenerator,
        )

        # --------------------------------------------------
        # 1. Basic timing: a CUT segment must not count toward
        #    elapsed edited-video time at all - this is the core
        #    fix over the old raw-footage ChapterGenerator.
        # --------------------------------------------------

        segments = [
            TranscriptSegment(
                0, "00:00:00:00", "00:00:05:00", "Speaker 1", "Kept one."
            ),
            TranscriptSegment(
                1,
                "00:00:05:00",
                "00:05:00:00",
                "Speaker 1",
                "This huge cut chunk should not count.",
            ),
            TranscriptSegment(
                2, "00:05:00:00", "00:05:10:00", "Speaker 1", "Kept two."
            ),
            TranscriptSegment(
                3, "00:05:10:00", "00:05:25:00", "Speaker 1", "Kept three."
            ),
        ]

        decisions = {
            0: {"keep": True, "paragraph_break_before": True},
            1: {"keep": False, "paragraph_break_before": False},
            2: {"keep": True, "paragraph_break_before": True},
            3: {"keep": True, "paragraph_break_before": True},
        }

        clean_labels = json.dumps(
            {"labels": ["Opening", "Second Topic", "Third Topic"]}
        )

        generator = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient(clean_labels)
        )

        result = generator.generate(segments, decisions, fps=24.0, min_chapter_seconds=0.0)

        chapters = result["chapters"]

        if len(chapters) != 3:
            raise RuntimeError(
                f"Expected 3 chapters (one per paragraph, with consolidation "
                f"disabled via min_chapter_seconds=0.0), got "
                f"{len(chapters)}."
            )

        if chapters[0]["time_seconds"] != 0.0:
            raise RuntimeError("First chapter must start at 0:00.")

        # Chapter 2 should start at 5s (duration of kept segment 0
        # only) - the huge cut segment (nearly 5 minutes) must NOT
        # have been counted.
        if abs(chapters[1]["time_seconds"] - 5.0) > 0.01:
            raise RuntimeError(
                f"Second chapter should start at 5.0s (cut segment "
                f"excluded), got {chapters[1]['time_seconds']}. This "
                f"is the core bug this generator exists to fix - raw "
                f"footage time must never leak into edited-video "
                f"timestamps."
            )

        # Chapter 3 should start at 5s + 10s (kept segments 0 and 2).
        if abs(chapters[2]["time_seconds"] - 15.0) > 0.01:
            raise RuntimeError(
                f"Third chapter should start at 15.0s, got "
                f"{chapters[2]['time_seconds']}."
            )

        if chapters[0]["label"] != "Opening":
            raise RuntimeError(
                f"Expected label 'Opening', got {chapters[0]['label']!r}."
            )

        # --------------------------------------------------
        # 2. A completely CUT-out sequence contributes zero
        #    additional elapsed time, however long it was in the
        #    raw footage.
        # --------------------------------------------------

        if "This huge cut chunk" in str(chapters):
            raise RuntimeError(
                "Cut segment text should never appear in chapter "
                "output."
            )

        # --------------------------------------------------
        # 3. Non-JSON label response must fall back to generic
        #    "Chapter N" labels rather than crashing or losing the
        #    chapters entirely - timing is still useful even with
        #    a generic label.
        # --------------------------------------------------

        generator2 = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient("I can't help with that.")
        )

        result2 = generator2.generate(segments, decisions, fps=24.0, min_chapter_seconds=0.0)

        if len(result2["chapters"]) != 3:
            raise RuntimeError(
                "Chapters should still be produced (with fallback "
                "labels) even when the label response fails to parse."
            )

        if result2["chapters"][0]["label"] != "Chapter 1":
            raise RuntimeError(
                f"Expected fallback label 'Chapter 1', got "
                f"{result2['chapters'][0]['label']!r}."
            )

        # --------------------------------------------------
        # 4. A label response with fewer labels than paragraphs
        #    must fall back only for the MISSING ones, not discard
        #    the labels that were actually provided.
        # --------------------------------------------------

        short_labels = json.dumps({"labels": ["Only One Label"]})

        generator3 = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient(short_labels)
        )

        result3 = generator3.generate(segments, decisions, fps=24.0, min_chapter_seconds=0.0)

        if result3["chapters"][0]["label"] != "Only One Label":
            raise RuntimeError(
                "The one real label provided should be used, not "
                "discarded in favour of the fallback."
            )

        if result3["chapters"][1]["label"] != "Chapter 2":
            raise RuntimeError(
                "Missing labels beyond what the model provided should "
                "fall back to 'Chapter N', not be left blank or "
                "crash."
            )

        # --------------------------------------------------
        # 5. No kept paragraphs at all (e.g. everything was cut)
        #    must return an empty, well-formed result rather than
        #    raising.
        # --------------------------------------------------

        all_cut_decisions = {
            0: {"keep": False, "paragraph_break_before": False},
            1: {"keep": False, "paragraph_break_before": False},
            2: {"keep": False, "paragraph_break_before": False},
            3: {"keep": False, "paragraph_break_before": False},
        }

        generator4 = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient(clean_labels)
        )

        result4 = generator4.generate(
            segments, all_cut_decisions, fps=24.0, min_chapter_seconds=0.0
        )

        if result4["chapters"] != []:
            raise RuntimeError(
                "No kept segments should produce an empty chapter "
                "list, not raise or fabricate chapters."
            )

        if result4["meets_youtube_requirements"]:
            raise RuntimeError(
                "Zero chapters should never report as meeting "
                "YouTube's requirements."
            )

        # --------------------------------------------------
        # 6. format_for_description() renders ready-to-paste text
        #    matching ChapterGenerator's own format.
        # --------------------------------------------------

        formatted = IntelliScriptChapterGenerator.format_for_description(
            result
        )

        if "0:00 Opening" not in formatted:
            raise RuntimeError(
                f"format_for_description output missing expected "
                f"line: {formatted!r}"
            )

        # --------------------------------------------------
        # 7. Consolidation (Gary's decision): consecutive short
        #    paragraphs merge into one chapter until it reaches
        #    min_chapter_seconds, rather than one chapter per
        #    paragraph. Six 20s paragraphs with a 60s minimum
        #    should merge into exactly two 60s chapters.
        # --------------------------------------------------

        consolidation_segments = [
            TranscriptSegment(
                i, f"00:00:{i*20:02d}:00", f"00:00:{i*20+20:02d}:00",
                "Speaker 1", f"Paragraph {i}."
            )
            for i in range(6)
        ]

        consolidation_decisions = {
            i: {"keep": True, "paragraph_break_before": True}
            for i in range(6)
        }

        consolidation_labels = json.dumps(
            {
                "labels": [
                    "Topic A", "Topic B", "Topic C",
                    "Topic D", "Topic E", "Topic F",
                ]
            }
        )

        generator5 = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient(consolidation_labels)
        )

        result5 = generator5.generate(
            consolidation_segments,
            consolidation_decisions,
            fps=24.0,
            min_chapter_seconds=60.0,
        )

        if len(result5["chapters"]) != 2:
            raise RuntimeError(
                f"Six 20s paragraphs with a 60s minimum should "
                f"consolidate into exactly 2 chapters (3 "
                f"paragraphs = 60s each), got "
                f"{len(result5['chapters'])}: {result5['chapters']!r}"
            )

        if result5["chapters"][0]["label"] != "Topic A":
            raise RuntimeError(
                "First consolidated chapter should keep the label "
                "of the paragraph that STARTS it (Topic A), not a "
                "combined label."
            )

        if abs(result5["chapters"][1]["time_seconds"] - 60.0) > 0.01:
            raise RuntimeError(
                f"Second chapter should start at 60s (after the "
                f"first three 20s paragraphs), got "
                f"{result5['chapters'][1]['time_seconds']}."
            )

        if result5["chapters"][1]["label"] != "Topic D":
            raise RuntimeError(
                "Second consolidated chapter should keep the label "
                "of the 4th paragraph (Topic D), the one that "
                "starts it."
            )

        # --------------------------------------------------
        # 8. A too-short trailing group merges backward into the
        #    previous chapter rather than being left as its own
        #    sub-minimum chapter.
        # --------------------------------------------------

        trailing_short_segments = [
            TranscriptSegment(
                0, "00:00:00:00", "00:01:10:00", "Speaker 1", "Long one."
            ),
            TranscriptSegment(
                1, "00:01:10:00", "00:01:20:00", "Speaker 1", "Short trailer."
            ),
        ]

        trailing_short_decisions = {
            0: {"keep": True, "paragraph_break_before": True},
            1: {"keep": True, "paragraph_break_before": True},
        }

        trailing_labels = json.dumps(
            {"labels": ["Main Topic", "Trailing Bit"]}
        )

        generator6 = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient(trailing_labels)
        )

        result6 = generator6.generate(
            trailing_short_segments,
            trailing_short_decisions,
            fps=24.0,
            min_chapter_seconds=60.0,
        )

        if len(result6["chapters"]) != 1:
            raise RuntimeError(
                f"A too-short trailing paragraph (10s) after a "
                f"70s main paragraph should merge backward into a "
                f"single chapter, not be left as its own "
                f"sub-minimum chapter. Got "
                f"{len(result6['chapters'])}: {result6['chapters']!r}"
            )

        if result6["chapters"][0]["label"] != "Main Topic":
            raise RuntimeError(
                "The merged chapter should keep the label of "
                "whichever paragraph started it (Main Topic)."
            )

        # --------------------------------------------------
        # 9. A single paragraph shorter than min_chapter_seconds
        #    is still kept as the sole chapter (nothing to merge
        #    it into) rather than being dropped entirely.
        # --------------------------------------------------

        lone_short_segments = [
            TranscriptSegment(
                0, "00:00:00:00", "00:00:15:00", "Speaker 1", "Only bit."
            ),
        ]

        lone_short_decisions = {
            0: {"keep": True, "paragraph_break_before": True},
        }

        generator7 = IntelliScriptChapterGenerator(
            ollama_client=FakeLabelClient(
                json.dumps({"labels": ["Only Topic"]})
            )
        )

        result7 = generator7.generate(
            lone_short_segments,
            lone_short_decisions,
            fps=24.0,
            min_chapter_seconds=60.0,
        )

        if len(result7["chapters"]) != 1:
            raise RuntimeError(
                "A single short paragraph with nothing to merge "
                "into should still produce exactly one chapter, "
                f"got {result7['chapters']!r}."
            )
