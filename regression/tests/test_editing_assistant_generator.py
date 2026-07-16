"""
============================================================
SBA AI Studio
Editing Assistant Generator Regression Test
ML-030
Version : 1.0.0
============================================================

Verifies EditingAssistantGenerator's prompt construction
(grounded in real day/scene facts) and response parsing (clean
JSON, JSON embedded in extra text, non-JSON degrading
gracefully) using a fake Ollama client - no real network or
model involved.
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


class EditingAssistantGeneratorRegressionTest(BaseRegressionTest):

    name = "Editing Assistant Generator (ML-030)"

    category = "Planning"

    description = (
        "Verify story analysis / editing suggestions prompt "
        "grounding and response parsing using a fake Ollama "
        "client."
    )

    def run(self) -> None:

        from sba_resolve.core.services.editing_assistant_generator import (
            EditingAssistantGenerator,
        )

        day_summary = {
            "total_days": 1,
            "days": [
                {
                    "day": 1,
                    "date": "2026-07-12",
                    "duration_minutes": 90.0,
                    "cameras": ["GoPro HERO13 Black"],
                    "scene_count": 2,
                    "places": ["Whithorn, Scotland, United Kingdom"],
                }
            ],
        }

        scene_facts = [
            {
                "ride_day": 1,
                "scene": 1,
                "duration_minutes": 45.0,
                "clip_count": 1,
                "cameras": ["GoPro HERO13 Black"],
                "camera_count": 1,
                "is_multicam": False,
                "has_hero13_audio": True,
            },
            {
                "ride_day": 1,
                "scene": 2,
                "duration_minutes": 5.0,
                "clip_count": 2,
                "cameras": ["GoPro HERO13 Black", "GoPro HERO8 Black"],
                "camera_count": 2,
                "is_multicam": True,
                "has_hero13_audio": True,
            },
        ]

        # --------------------------------------------------
        # 1. Clean JSON response, and the prompt must contain
        #    the REAL facts (place name, multicam flag), not
        #    generic filler.
        # --------------------------------------------------

        clean_json = json.dumps(
            {
                "story_analysis": (
                    "Open with the long first scene, then use the "
                    "short multicam scene as a closer."
                ),
                "editing_suggestions": [
                    "Scene 1 is 45 minutes - consider trimming.",
                    "Scene 2 has a multicam window - cut between "
                    "cameras for variety.",
                ],
            }
        )

        generator = EditingAssistantGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        result = generator.generate(day_summary, scene_facts, "Sunday ride")

        if result["parse_error"]:
            raise RuntimeError(
                "Clean JSON response should not produce a "
                "parse_error."
            )

        if "trimming" not in result["editing_suggestions"][0]:
            raise RuntimeError(
                f"Unexpected editing_suggestions: "
                f"{result['editing_suggestions']!r}"
            )

        prompt = generator.ollama_client.last_prompt

        if "Whithorn" not in prompt:
            raise RuntimeError(
                "Prompt should include the real place name from "
                "day_summary."
            )

        if "MULTICAM" not in prompt:
            raise RuntimeError(
                "Prompt should include the real multicam flag "
                "from scene_facts."
            )

        if "45" not in prompt:
            raise RuntimeError(
                "Prompt should include the real scene duration."
            )

        # --------------------------------------------------
        # 2. JSON embedded in chatty extra text still parses.
        # --------------------------------------------------

        chatty = "Sure, here you go:\n\n" + clean_json + "\n\nHope that helps!"

        generator2 = EditingAssistantGenerator(
            ollama_client=FakeOllamaClient(chatty)
        )

        result2 = generator2.generate(
            day_summary, scene_facts, "Sunday ride"
        )

        if result2["parse_error"]:
            raise RuntimeError(
                "JSON embedded in extra text should still parse."
            )

        # --------------------------------------------------
        # 3. Non-JSON response degrades to parse_error=True,
        #    raw_response preserved.
        # --------------------------------------------------

        generator3 = EditingAssistantGenerator(
            ollama_client=FakeOllamaClient("I can't help with that.")
        )

        result3 = generator3.generate(
            day_summary, scene_facts, "Sunday ride"
        )

        if not result3["parse_error"]:
            raise RuntimeError(
                "Non-JSON response should set parse_error=True."
            )

        if result3["raw_response"] != "I can't help with that.":
            raise RuntimeError(
                "raw_response should preserve the model's exact "
                "output on parse failure."
            )

        if result3["story_analysis"] is not None:
            raise RuntimeError(
                "story_analysis should be None when parsing fails."
            )
