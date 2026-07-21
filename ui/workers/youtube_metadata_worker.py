"""
============================================================
SBA AI Studio
YouTube Metadata Worker
ML-028-002 / ML-052 (IntelliScript-based chapter wiring)
Version : 1.3.0 Alpha
============================================================

Runs YouTube metadata generation (Planning Engine -> ride
summary -> configured AI provider) on a background thread, so a
slow model load or an unreachable backend doesn't freeze the GUI.

run() is deliberately plain, synchronous Python calling
already-regression-tested services (TimelinePlanningService,
RideSummaryBuilder, YouTubeMetadataGenerator) - it can be called
directly (bypassing QThread.start()) for testing without
spinning up a real thread.

ML-052: chapters are now sourced from IntelliScriptChapterGenerator
(real edited-video timestamps, AI-generated subject labels) rather
than the raw-footage ChapterGenerator (ML-030/ML-051) - raw footage
timing was confirmed wrong for real published videos (e.g. showing
"1:37:55" for a video that's actually a couple of minutes long
once edited). This requires the raw transcript text AND the
IntelliScript decisions already generated for this project - both
optional constructor args. If either is missing (no transcript
loaded, or IntelliScript hasn't been generated yet), NO chapters
section is added at all - deliberately not falling back to the
raw-footage generator, since showing no chapters is better than
showing known-wrong ones.

Chapter generation (re-parsing the transcript + running
IntelliScriptChapterGenerator) is wrapped in its own try/except so
a failure here never blocks the actual title/description/tags
from being returned - it just falls back to no chapters section.

Version 1.3.0 (Groq provider backlog item): YouTubeMetadataGenerator's
default (get_ai_provider()) now reads Settings' AI Provider choice
(Ollama or Groq) and its model itself, so this worker no longer
constructs a client itself. The "model" parameter is kept ONLY for
backward compatibility with existing regression tests that still
pass it (e.g. model="llama3.2") - it is accepted but intentionally
unused; provider/model selection now happens entirely inside
YouTubeMetadataGenerator's default. A future cleanup could remove
this parameter once those tests are updated to stop passing it.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.groq_provider import GroqError
from sba_resolve.core.services.intelliscript_chapter_generator import (
    IntelliScriptChapterGenerator,
)
from sba_resolve.core.services.ollama_client import OllamaError
from sba_resolve.core.services.resolve_transcript_parser import (
    ResolveTranscriptParser,
)
from sba_resolve.core.services.ride_summary_builder import RideSummaryBuilder
from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)
from sba_resolve.core.services.youtube_metadata_generator import (
    YouTubeMetadataGenerator,
)


class YouTubeMetadataWorker(QThread):

    succeeded = Signal(dict)

    failed = Signal(str)

    def __init__(
        self,
        media_list,
        project_name: str,
        model: str = "llama3.2",
        extra_notes: str = "",
        raw_transcript_text: str | None = None,
        intelliscript_decisions: dict[int, dict] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.media_list = list(media_list)
        self.project_name = project_name
        # Accepted for backward compatibility only - see class
        # docstring. Intentionally not used to construct anything.
        self.model = model
        self.extra_notes = extra_notes
        self.raw_transcript_text = raw_transcript_text
        self.intelliscript_decisions = intelliscript_decisions

    def run(self) -> None:

        try:
            result = TimelinePlanningService().plan(self.media_list)

            summary = RideSummaryBuilder().build(result)

            chapter_days = self._safe_generate_intelliscript_chapters()

            generator = YouTubeMetadataGenerator()

            metadata = generator.generate(
                summary,
                self.project_name,
                self.extra_notes,
                chapter_days=chapter_days,
            )

        except (OllamaError, GroqError) as exc:
            self.failed.emit(str(exc))
            return

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        self.succeeded.emit(metadata)

    def _safe_generate_intelliscript_chapters(self) -> list[dict] | None:
        """
        Returns a "days"-shaped list (a single entry, since one
        video always covers one ride day) built from
        IntelliScriptChapterGenerator, or None if:
            - no transcript text or no IntelliScript decisions are
              available for this project yet, or
            - anything in re-parsing/chapter generation fails.

        Deliberately swallowed rather than propagated - a chapters
        section is a bonus addition to the description, not a
        reason to fail metadata generation entirely. Returning None
        here means NO chapters section gets added at all (see
        YouTubeMetadataGenerator, which only appends one when
        chapter_days is truthy) - this is intentional: no chapters
        is better than the old raw-footage timestamps, which were
        confirmed wrong for real published videos.
        """

        if not self.raw_transcript_text or not self.intelliscript_decisions:
            return None

        try:
            all_segments = ResolveTranscriptParser().parse(
                self.raw_transcript_text
            )

            chapter_result = IntelliScriptChapterGenerator().generate(
                all_segments, self.intelliscript_decisions
            )

            if not chapter_result.get("chapters"):
                return None

            # YouTubeMetadataGenerator expects a "days" list (see
            # ChapterGenerator's original shape) - one video always
            # covers one ride day, so this is always a single entry.
            return [
                {
                    "ride_day": 1,
                    "chapters": chapter_result["chapters"],
                    "meets_youtube_requirements": chapter_result[
                        "meets_youtube_requirements"
                    ],
                    "warnings": chapter_result["warnings"],
                }
            ]

        except Exception:
            return None