"""
============================================================
SBA AI Studio
YouTube Metadata Generator Regression Test
ML-026
Version : 1.0.0
============================================================

Verifies YouTubeMetadataGenerator's response parsing (clean
JSON, JSON embedded in extra text, and a non-JSON response that
must degrade to parse_error=True rather than raising) using a
fake Ollama client - no real network or model involved.
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
        "client."
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

        if result3["raw_response"] != "I can't help with that request.":
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
