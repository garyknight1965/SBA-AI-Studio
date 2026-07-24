"""
============================================================
SBA AI Studio
Editing Assistant Generator
ML-030-002 / ML-068 (AI provider wiring fix)
Version : 1.1.0 Alpha
============================================================

Generates a narrative-structure suggestion ("story analysis")
and concrete editing suggestions from ride reconstruction facts
(per-day AND per-scene), via the app's configured AI provider
(Ollama or Groq - see ai_provider_factory.py).

Like YouTubeMetadataGenerator, this only knows what the facts
tell it - it can't watch the footage, so it reasons about
STRUCTURE (scene durations, camera counts, multicam windows,
HERO13 audio availability), never about content (what actually
happens in any scene).

ML-068 (2026-07-24, bug fix): this generator previously imported
OllamaClient directly and defaulted to a bare OllamaClient() with
no model argument whenever no client was passed in - which
silently ignored config/settings.json's "ai_provider" and
"ollama_model" settings entirely (falling back to OllamaClient's
own hardcoded "llama3.2" default no matter what Settings said).
Same bug, same fix as youtube_metadata_generator.py: defaults to
get_ai_provider() instead. The constructor parameter is
deliberately still named "ollama_client" (not renamed) for
regression-test backward compat.
"""

from __future__ import annotations

import json
import re

from sba_resolve.core.services.ai_provider import AIProvider
from sba_resolve.core.services.ai_provider_factory import get_ai_provider

GUIDANCE = """
You are helping a motorcycle vlogger (channel: Scottish Biker
Abroad) plan how to edit raw ride footage into a video. You
have NOT seen the footage - you only know its structure (scene
count, durations, camera usage, multicam windows, audio
availability). Reason about PACING and STRUCTURE only. You
cannot know what actually happens in any scene, so never
describe or assume specific events, scenery, or actions.
"""


class EditingAssistantGenerator:
    """
    Generates story analysis + editing suggestions from ride
    reconstruction facts.
    """

    def __init__(self, ollama_client: AIProvider | None = None) -> None:
        self.ollama_client = ollama_client or get_ai_provider()

    def generate(
        self,
        day_summary: dict,
        scene_facts: list[dict],
        project_name: str,
    ) -> dict:
        """
        Returns:
            {
                "story_analysis": str | None,
                "editing_suggestions": list[str],
                "raw_response": str,
                "parse_error": bool,
            }
        """

        prompt = self._build_prompt(day_summary, scene_facts, project_name)

        raw_response = self.ollama_client.generate(prompt)

        return self._parse_response(raw_response)

    def _build_prompt(
        self,
        day_summary: dict,
        scene_facts: list[dict],
        project_name: str,
    ) -> str:

        day_lines = []

        for day in day_summary.get("days", []):
            parts = [f"Day {day['day']}"]
            parts.append(f"{day['duration_minutes']:.0f} min total")
            parts.append(f"{day['scene_count']} scene(s)")
            if day.get("places"):
                parts.append("places: " + ", ".join(day["places"]))
            day_lines.append(" | ".join(parts))

        days_text = "\n".join(day_lines) or "No day data available."

        scene_lines = []

        for scene in scene_facts:
            parts = [
                f"Day {scene['ride_day']} Scene {scene['scene']}",
                f"{scene['duration_minutes']:.0f} min",
                f"{scene['clip_count']} clip(s)",
                "MULTICAM" if scene["is_multicam"] else "single camera",
                (
                    "has HERO13 audio"
                    if scene["has_hero13_audio"]
                    else "no HERO13 audio"
                ),
            ]
            scene_lines.append(" | ".join(parts))

        scenes_text = "\n".join(scene_lines) or "No scene data available."

        return f"""{GUIDANCE}

Project name: {project_name}

Day-by-day facts:
{days_text}

Scene-by-scene facts (this is EVERYTHING you know about the
footage - do not invent what happens in any scene):
{scenes_text}

CRITICAL: base every suggestion only on the structural facts
above (durations, camera counts, multicam presence, audio
availability). Do not invent scene content, locations not
listed, or events.

Respond with ONLY a JSON object, no other text, in exactly this
shape:

{{
  "story_analysis": "2-4 sentences suggesting a narrative structure for the edit, based only on the day/scene structure above",
  "editing_suggestions": ["suggestion 1", "suggestion 2", "..."]
}}
"""

    @staticmethod
    def _parse_response(raw_response: str) -> dict:

        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group(0))

                return {
                    "story_analysis": data.get("story_analysis"),
                    "editing_suggestions": data.get(
                        "editing_suggestions", []
                    ),
                    "raw_response": raw_response,
                    "parse_error": False,
                }
            except json.JSONDecodeError:
                pass

        return {
            "story_analysis": None,
            "editing_suggestions": [],
            "raw_response": raw_response,
            "parse_error": True,
        }
