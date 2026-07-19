"""
============================================================
SBA AI Studio
YouTube Metadata Generator Regression Test
ML-026 / ML-051 (chapter wiring)
Version : 1.1.0
============================================================

Verifies YouTubeMetadataGenerator's response parsing (clean
JSON, JSON embedded in extra text, and a non-JSON response that
must degrade to parse_error=True rather than raising) using a
fake Ollama client - no real network or model involved.

Also verifies ML-051's chapter-appending: a chapters section is
appended to the description (with its raw-footage-timing caveat)
when chapter_days is provided, and is cleanly absent when it
isn't - including the parse_error case, where the appended text
still needs to land somewhere useful (raw_response) rather than
being silently dropped.
"""

from __future__ import annotations

import json

from regression.base_test import BaseRegressionTest


class FakeOllamaClient:

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response_text


class YouTubeMetadataGeneratorRegressionTest(BaseRegressionTest):

    name = "YouTube Metadata Generator (ML-026)"

    category = "Planning"

    description = (
        "Verify prompt construction and response parsing "
        "(clean JSON, JSON embedded in extra text, and "
        "non-JSON degrading gracefully) using a fake Ollama "
        "client, plus ML-051's chapter-appending behavior."
    )

    def run(self) -> None:

        from sba_resolve.core.services.youtube_metadata_generator import (
            YouTubeMetadataGenerator,
        )

        ride_summary = {
            "total_days": 1,
            "days": [
                {
                    "day": 1,
                    "date": "2026-05-12",
                    "duration_minutes": 90.0,
                    "cameras": ["GoPro HERO13 Black"],
                    "scene_count": 3,
                    "places": ["Whithorn, Scotland, United Kingdom"],
                }
            ],
        }

        # --------------------------------------------------
        # 1. Clean JSON response.
        # --------------------------------------------------

        clean_json = json.dumps(
            {
                "title": "Whithorn Castle Ride - Scottish Biker Abroad",
                "description": "A day riding to Whithorn...",
                "tags": ["motorcycle", "scotland", "whithorn"],
            }
        )

        generator = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        result = generator.generate(ride_summary, "12-05-2026 castle")

        if result["parse_error"]:
            raise RuntimeError(
                "Clean JSON response should not produce a "
                "parse_error."
            )

        if result["title"] != "Whithorn Castle Ride - Scottish Biker Abroad":
            raise RuntimeError(
                f"Unexpected title: {result['title']!r}"
            )

        if result["tags"] != ["motorcycle", "scotland", "whithorn"]:
            raise RuntimeError(
                f"Unexpected tags: {result['tags']!r}"
            )

        # Prompt must actually include the real facts, not
        # invented ones - e.g. the place name and day count.
        if "Whithorn" not in generator.ollama_client.last_prompt:
            raise RuntimeError(
                "Prompt should include the GPS-derived place name."
            )

        # --------------------------------------------------
        # 2. JSON embedded in extra chatty text (some models
        #    preface their answer despite instructions).
        # --------------------------------------------------

        chatty_response = (
            "Sure, here's the metadata you asked for:\n\n"
            + clean_json
            + "\n\nLet me know if you'd like changes!"
        )

        generator2 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(chatty_response)
        )

        result2 = generator2.generate(ride_summary, "12-05-2026 castle")

        if result2["parse_error"]:
            raise RuntimeError(
                "JSON embedded in extra text should still parse "
                "correctly."
            )

        if result2["title"] != "Whithorn Castle Ride - Scottish Biker Abroad":
            raise RuntimeError(
                f"Unexpected title from chatty response: "
                f"{result2['title']!r}"
            )

        # --------------------------------------------------
        # 3. Non-JSON response degrades to parse_error=True,
        #    with the raw response preserved (nothing lost).
        # --------------------------------------------------

        generator3 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(
                "I can't help with that request."
            )
        )

        result3 = generator3.generate(ride_summary, "12-05-2026 castle")

        if not result3["parse_error"]:
            raise RuntimeError(
                "A non-JSON response should set parse_error=True."
            )

        if not result3["raw_response"].startswith(
            "I can't help with that request."
        ):
            raise RuntimeError(
                "raw_response should preserve the model's exact "
                "output even on parse failure."
            )

        if result3["title"] is not None:
            raise RuntimeError(
                "title should be None when parsing fails."
            )

        # --------------------------------------------------
        # 4. A day with NO identified places must explicitly
        #    tell the model not to invent one, rather than
        #    silently omitting the "places" field and leaving a
        #    gap the model fills with a guess (this is what let
        #    an earlier real run hallucinate "Normandy Coast"
        #    for a ride with no GPS data at all).
        # --------------------------------------------------

        no_places_summary = {
            "total_days": 1,
            "days": [
                {
                    "day": 1,
                    "date": "2026-07-12",
                    "duration_minutes": 66.0,
                    "cameras": ["GoPro HERO13 Black"],
                    "scene_count": 4,
                    "places": [],
                }
            ],
        }

        generator4 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        generator4.generate(no_places_summary, "Sunday ride")

        prompt = generator4.ollama_client.last_prompt

        if "NONE IDENTIFIED" not in prompt:
            raise RuntimeError(
                "A day with no identified places must explicitly "
                "tell the model not to invent one - found no "
                "'NONE IDENTIFIED' marker in the prompt."
            )

        if "do not invent" not in prompt.lower():
            raise RuntimeError(
                "Prompt is missing the explicit anti-hallucination "
                "instruction."
            )

        # --------------------------------------------------
        # 5. ML-051: chapter_days=None (or omitted) must NOT
        #    add any chapters section - this covers projects
        #    where Planning/chapter data isn't available yet.
        # --------------------------------------------------

        generator5 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        result5 = generator5.generate(
            ride_summary, "12-05-2026 castle", chapter_days=None
        )

        if "Chapters" in (result5["description"] or ""):
            raise RuntimeError(
                "No chapters section should be appended when "
                "chapter_days is None."
            )

        # --------------------------------------------------
        # 6. ML-051: chapter_days provided must append a
        #    chapters section, with the raw-footage-timing
        #    caveat, using ChapterGenerator's own formatting.
        # --------------------------------------------------

        chapter_days = [
            {
                "ride_day": 1,
                "chapters": [
                    {"time_seconds": 0.0, "time_text": "0:00", "label": "Scene 1"},
                    {"time_seconds": 125.0, "time_text": "2:05", "label": "Scene 2"},
                    {"time_seconds": 340.0, "time_text": "5:40", "label": "Scene 3"},
                ],
                "meets_youtube_requirements": True,
                "warnings": [],
            }
        ]

        generator6 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        result6 = generator6.generate(
            ride_summary,
            "12-05-2026 castle",
            chapter_days=chapter_days,
        )

        description6 = result6["description"] or ""

        if "Chapters" not in description6:
            raise RuntimeError(
                "A chapters section should be appended when "
                "chapter_days is provided."
            )

        if "0:00 Scene 1" not in description6:
            raise RuntimeError(
                "Appended chapters should include ChapterGenerator's "
                "formatted lines (e.g. '0:00 Scene 1')."
            )

        if "edited timing" not in description6.lower():
            raise RuntimeError(
                "Appended chapters section must carry the "
                "raw-footage-timing caveat, not be presented as "
                "ready-to-publish."
            )

        # --------------------------------------------------
        # 7. ML-051: a day with zero chapters (e.g. Planning
        #    ran but found no scenes) must not append an empty
        #    or malformed section.
        # --------------------------------------------------

        empty_chapter_days = [
            {
                "ride_day": 1,
                "chapters": [],
                "meets_youtube_requirements": False,
                "warnings": ["Only 0 chapter(s)..."],
            }
        ]

        generator7 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        result7 = generator7.generate(
            ride_summary,
            "12-05-2026 castle",
            chapter_days=empty_chapter_days,
        )

        if "Chapters" in (result7["description"] or ""):
            raise RuntimeError(
                "No chapters section should be appended when every "
                "day has zero chapters."
            )

        # --------------------------------------------------
        # 8. ML-051: chapters must still be appended (to
        #    raw_response) even when the model's own response
        #    fails to parse - nothing should be silently lost.
        # --------------------------------------------------

        generator8 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient("I can't help with that.")
        )

        result8 = generator8.generate(
            ride_summary,
            "12-05-2026 castle",
            chapter_days=chapter_days,
        )

        if not result8["parse_error"]:
            raise RuntimeError(
                "This response should still fail to parse as JSON."
            )

        if "Chapters" not in result8["raw_response"]:
            raise RuntimeError(
                "Chapters should still be appended (to raw_response) "
                "even when the model's response fails to parse."
            )
