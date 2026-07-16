"""
============================================================
SBA AI Studio
IntelliScript Editor
Version : 1.0.0
Sprint  : ML-034
============================================================

Turns a raw DaVinci Resolve transcript export into an
IntelliScript-ready script, using a local Ollama model for the
EDITORIAL judgment only:

    - which segments to keep (cutting dead air, stuttering,
      repetitive filler, rambling/confusing asides, and
      meta-commentary about the video itself)
    - where a new paragraph (topic/beat change) begins

The AI NEVER supplies replacement text. It is only ever asked for
keep/cut + paragraph-break decisions per segment index; the exact
original words are reassembled by IntelliScriptAssembler, which
is pure, deterministic code. This is what keeps the output
verbatim-safe for Resolve's IntelliScript, which needs the script
text to match the spoken audio exactly - no corrected spelling,
no corrected grammar, no paraphrasing.

Pure sound-effect blocks (no speaker line at all) are dropped
automatically before the AI ever sees them - that's not an
editorial judgment call.

Per the project's "AI Roadmap": local AI (Ollama) by default,
cloud AI optional (not built here yet).
"""

from __future__ import annotations

import json
import re

from sba_resolve.core.models.transcript_segment import TranscriptSegment
from sba_resolve.core.services.intelliscript_assembler import (
    IntelliScriptAssembler,
)
from sba_resolve.core.services.ollama_client import OllamaClient
from sba_resolve.core.services.resolve_transcript_parser import (
    ResolveTranscriptParser,
)


class IntelliScriptEditor:
    """
    Builds an IntelliScript-ready script from a raw Resolve
    transcript export.
    """

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.ollama_client = ollama_client or OllamaClient()
        self.parser = ResolveTranscriptParser()
        self.assembler = IntelliScriptAssembler()

    def build_script(self, raw_transcript_text: str) -> dict:
        """
        Returns:
            {
                "script": str,
                "decisions": dict[int, dict],
                "raw_response": str,
                "parse_error": bool,
                "segment_count": int,
                "kept_count": int,
            }

        On parse_error, "script" is "" and "decisions" is empty -
        raw_response is still returned in full so nothing is lost,
        the caller just has to read the model's response itself
        rather than getting a usable script.
        """

        all_segments = self.parser.parse(raw_transcript_text)

        speech_segments = [s for s in all_segments if s.is_speech]

        if not speech_segments:
            return {
                "script": "",
                "decisions": {},
                "raw_response": "",
                "parse_error": False,
                "segment_count": 0,
                "kept_count": 0,
            }

        prompt = self._build_prompt(speech_segments)

        raw_response = self.ollama_client.generate(prompt)

        decisions, parse_error = self._parse_decisions(
            raw_response, speech_segments
        )

        script = (
            ""
            if parse_error
            else self.assembler.assemble(all_segments, decisions)
        )

        return {
            "script": script,
            "decisions": decisions,
            "raw_response": raw_response,
            "parse_error": parse_error,
            "segment_count": len(speech_segments),
            "kept_count": sum(
                1 for d in decisions.values() if d.get("keep")
            ),
        }

    # -----------------------------------------------------

    def _build_prompt(
        self, speech_segments: list[TranscriptSegment]
    ) -> str:

        lines = [
            f"{segment.index}: {segment.text}"
            for segment in speech_segments
        ]

        segments_text = "\n".join(lines)

        last_index = speech_segments[-1].index

        return f"""Act as an expert video editor working on a motorcycle vlog.

Below is a numbered list of transcript segments, in original
spoken order. For EACH segment, decide whether to KEEP or CUT it,
and whether it starts a new paragraph (topic/beat change).

Guidelines:
- Cut dead air, stuttering, and repetitive filler.
- Cut rambling, confusing, or unfinished asides that don't add
  anything to the story.
- Cut meta-commentary about the video itself (e.g. the speaker
  talking about what they've just been talking about).
- Keep the core storyline and message engaging.
- Group consecutive KEPT segments into paragraphs by topic - set
  paragraph_break_before true whenever a segment starts a new
  topic or beat, false if it continues the same paragraph as the
  previous kept segment.

CRITICAL: you are ONLY deciding keep/cut and paragraph grouping.
Do not rewrite, reword, correct, or paraphrase anything - you
have no ability to supply replacement text, and any text you
included in your response would be ignored. The exact original
words are reassembled automatically from your keep/cut decisions.

Segments:
{segments_text}

Respond with ONLY a JSON object, no other text, in exactly this
shape:

{{
  "decisions": [
    {{"index": 0, "keep": true, "paragraph_break_before": true}},
    {{"index": 1, "keep": false, "paragraph_break_before": false}}
  ]
}}

Include EVERY index from 0 to {last_index}, in order, with no
gaps.
"""

    # -----------------------------------------------------

    @staticmethod
    def _parse_decisions(
        raw_response: str,
        speech_segments: list[TranscriptSegment],
    ) -> tuple[dict[int, dict], bool]:

        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)

        if not json_match:
            return {}, True

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return {}, True

        raw_decisions = data.get("decisions")

        if not isinstance(raw_decisions, list):
            return {}, True

        decisions: dict[int, dict] = {}

        for item in raw_decisions:

            if not isinstance(item, dict):
                continue

            try:
                index = int(item["index"])
            except (KeyError, TypeError, ValueError):
                continue

            decisions[index] = {
                "keep": bool(item.get("keep", False)),
                "paragraph_break_before": bool(
                    item.get("paragraph_break_before", False)
                ),
            }

        valid_indices = {segment.index for segment in speech_segments}

        missing = valid_indices - decisions.keys()

        if missing:
            # Fail-safe: a truncated/partial model response should
            # never silently DELETE content. Default any missing
            # segment to keep=True so it survives into the script -
            # worse to leave in a bit that needed cutting than to
            # silently lose footage the editor never sees again.
            for index in missing:
                decisions[index] = {
                    "keep": True,
                    "paragraph_break_before": False,
                }

        return decisions, False
