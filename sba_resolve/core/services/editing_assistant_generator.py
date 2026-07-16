"""
============================================================
SBA AI Studio
Editing Assistant Generator
ML-030-002
Version : 1.0.0 Alpha
============================================================

Generates a narrative-structure suggestion ("story analysis")
and concrete editing suggestions from ride reconstruction facts
(per-day AND per-scene), via a local Ollama model.

Like YouTubeMetadataGenerator, this only knows what the facts
tell it - it can't watch the footage, so it reasons about
STRUCTURE (scene durations, camera counts, multicam windows,
HERO13 audio availability), never about content (what actually
happens in any scene).
"""

from __future__ import annotations

import json
import re

from sba_resolve.core.services.ollama_client import OllamaClient

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

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.ollama_client = ollama_client or OllamaClient()

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
