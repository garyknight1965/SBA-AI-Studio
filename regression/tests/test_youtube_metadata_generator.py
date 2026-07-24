"""
============================================================
SBA AI Studio
YouTube Metadata Generator Regression Test
ML-026 / ML-051 (chapter wiring) / ML-058 (editable guidance) / ML-059 (rich SEO output)
Version : 1.3.0
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

Also verifies ML-058's editable guidance: the default brand-voice
guidance (loaded via app_settings.load_youtube_metadata_guidance())
instructs the model to naturally mention SBA AI Studio and DaVinci
Resolve in the prompt itself - NOT as a deterministically-appended
fixed line in the output - and a settings.json-configured override
actually reaches the prompt.

Also verifies ML-059's richer output schema: 5 title options
("title" still returned as a single backward-compatible best pick),
15 tags, a filename suggestion, a pinned comment, and thumbnail
overlay text - all parsed correctly, and all cleanly None/empty on
parse_error rather than raising or leaving stale data.
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
        "client, plus chapter-appending, editable guidance, "
        "and the richer ML-059 output schema."
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
        # 1. Clean JSON response, full ML-059 schema.
        # --------------------------------------------------

        clean_json = json.dumps(
            {
                "titles": [
                    "Whithorn Castle Ride - Scottish Biker Abroad",
                    "Chasing History in Whithorn on Two Wheels",
                    "A Scottish Biker's Whithorn Castle Detour",
                    "Whithorn: Scotland's Hidden Castle Ride",
                    "Motorcycle Touring Whithorn, Scotland",
                ],
                "description": "A day riding to Whithorn...",
                "tags": [
                    "motorcycle", "scotland", "whithorn", "touring",
                    "adventure biker", "gopro", "hero13", "castle",
                    "scottish biker abroad", "motovlog", "road trip",
                    "biker vlog", "scotland travel", "motorcycle tour",
                    "whithorn castle",
                ],
                "filename_suggestion": "whithorn-castle-ride-day1.mp4",
                "pinned_comment": (
                    "Ever ridden to Whithorn? Drop your favourite "
                    "Scottish castle route below!"
                ),
                "thumbnail_text": "WHITHORN CASTLE RIDE",
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
                f"Unexpected title (should be the first of "
                f"'titles', for backward compat): {result['title']!r}"
            )

        if len(result["titles"]) != 5:
            raise RuntimeError(
                f"Expected 5 title options, got "
                f"{len(result['titles'])}: {result['titles']!r}"
            )

        if len(result["tags"]) != 15:
            raise RuntimeError(
                f"Expected 15 tags, got {len(result['tags'])}: "
                f"{result['tags']!r}"
            )

        if result["filename_suggestion"] != "whithorn-castle-ride-day1.mp4":
            raise RuntimeError(
                f"Unexpected filename_suggestion: "
                f"{result['filename_suggestion']!r}"
            )

        if "Whithorn" not in (result["pinned_comment"] or ""):
            raise RuntimeError(
                f"Unexpected pinned_comment: {result['pinned_comment']!r}"
            )

        if result["thumbnail_text"] != "WHITHORN CASTLE RIDE":
            raise RuntimeError(
                f"Unexpected thumbnail_text: "
                f"{result['thumbnail_text']!r}"
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
        #    with the raw response preserved (nothing lost) and
        #    every ML-059 field cleanly empty/None.
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

        if result3["titles"] != []:
            raise RuntimeError(
                f"titles should be an empty list when parsing "
                f"fails, got {result3['titles']!r}."
            )

        for field in (
            "filename_suggestion",
            "pinned_comment",
            "thumbnail_text",
        ):
            if result3[field] is not None:
                raise RuntimeError(
                    f"{field} should be None when parsing fails, "
                    f"got {result3[field]!r}."
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
        # 8. ML-058: the DEFAULT guidance (loaded via
        #    app_settings.load_youtube_metadata_guidance(), no
        #    settings.json override) must be present in the
        #    prompt sent to the model, including the instruction
        #    to naturally mention SBA AI Studio and DaVinci
        #    Resolve - NOT a deterministically-appended fixed
        #    line in the output.
        # --------------------------------------------------

        generator8 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient(clean_json)
        )

        result8_default = generator8.generate(
            ride_summary, "12-05-2026 castle"
        )

        prompt8 = generator8.ollama_client.last_prompt

        if "SBA AI Studio" not in prompt8:
            raise RuntimeError(
                "Expected the default guidance to instruct the "
                "model to mention SBA AI Studio - not found in "
                "the prompt."
            )

        if "DaVinci Resolve" not in prompt8:
            raise RuntimeError(
                "Expected the default guidance to instruct the "
                "model to mention DaVinci Resolve - not found in "
                "the prompt."
            )

        # The credit must NOT be deterministically appended to
        # the description itself - it's purely a prompt
        # instruction, so a fake model response that doesn't
        # mention it should not have it added afterward.
        if "SBA AI Studio" in (result8_default["description"] or ""):
            raise RuntimeError(
                "The editor credit should come from the model's "
                "own response (per the prompt instruction), not "
                "be deterministically appended in code."
            )

        # --------------------------------------------------
        # 9. ML-058: a custom guidance override (as if saved via
        #    Settings -> YouTube Metadata Prompt) must actually
        #    reach the prompt, proving the editable-guidance
        #    wiring works end to end.
        # --------------------------------------------------

        import tempfile
        from pathlib import Path as _Path

        custom_guidance = (
            "CUSTOM TEST GUIDANCE - mention llamas in every title."
        )

        with tempfile.TemporaryDirectory() as tmp_dir:

            settings_path = _Path(tmp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {"youtube_metadata_prompt_guidance": custom_guidance}
                ),
                encoding="utf-8",
            )

            import sba_resolve.core.services.app_settings as app_settings_module

            original_default_path = (
                app_settings_module.DEFAULT_SETTINGS_PATH
            )

            app_settings_module.DEFAULT_SETTINGS_PATH = settings_path

            try:
                generator9 = YouTubeMetadataGenerator(
                    ollama_client=FakeOllamaClient(clean_json)
                )

                generator9.generate(ride_summary, "12-05-2026 castle")

                prompt9 = generator9.ollama_client.last_prompt

                if custom_guidance not in prompt9:
                    raise RuntimeError(
                        "Expected a settings.json-configured custom "
                        "guidance override to reach the prompt - "
                        "the editable-guidance wiring may be broken."
                    )

            finally:
                app_settings_module.DEFAULT_SETTINGS_PATH = (
                    original_default_path
                )

        # --------------------------------------------------
        # 10. ML-051: chapters must still be appended (to
        #     raw_response) even when the model's own response
        #     fails to parse - nothing should be silently lost.
        # --------------------------------------------------

        generator10 = YouTubeMetadataGenerator(
            ollama_client=FakeOllamaClient("I can't help with that.")
        )

        result10 = generator10.generate(
            ride_summary,
            "12-05-2026 castle",
            chapter_days=chapter_days,
        )

        if not result10["parse_error"]:
            raise RuntimeError(
                "This response should still fail to parse as JSON."
            )

        if "Chapters" not in result10["raw_response"]:
            raise RuntimeError(
                "Chapters should still be appended (to raw_response) "
                "even when the model's response fails to parse."
            )
