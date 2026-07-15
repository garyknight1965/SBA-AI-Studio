"""
============================================================
SBA AI Studio
YouTube Metadata Generator
ML-026-004
Version : 1.0.0 Alpha
============================================================

Generates a DRAFT YouTube title, description, and tags from a
ride summary (see RideSummaryBuilder), using a local Ollama
model. This is a starting point for the channel owner to edit,
not an auto-publish pipeline - the model only knows what the
ride summary tells it (dates, duration, cameras, scene count,
GPS-derived place names), not the actual footage content, so it
can't invent specific moments, riders, or events.

Per the project's "AI Roadmap": local AI (Ollama) by default,
cloud AI optional (not built here yet).
"""

from __future__ import annotations

import json
import re

from sba_resolve.core.services.ollama_client import OllamaClient

# Editable brand-voice guidance for the "Scottish Biker Abroad"
# channel. Tune this directly if the tone drifts - it's plain
# text, not something buried in code logic.
BRAND_VOICE_GUIDANCE = """
Channel: Scottish Biker Abroad - European motorcycle touring,
gear reviews, and ride vlogs.

Tone: irreverent British humour, self-aware about motorcycle
culture (don't take the "adventure biker" persona too
seriously), but genuinely informative for riders planning
similar trips.

Titles: SEO-focused and specific rather than vague - name the
actual place/route/landmark instead of generic phrases like
"epic ride" or "amazing day". If the ride touches WWII history
sites, castles, or other tourism crossover angles, that's worth
naming directly in the title - those searches perform well for
this channel.

Description: first 2 lines should work as a hook even if
YouTube truncates them. Include the places visited, roughly
how long/how many days, and the cameras used if that's
relevant to a gear-curious audience.
"""


class YouTubeMetadataGenerator:
    """
    Generates draft YouTube title/description/tags from a ride
    summary dict (see RideSummaryBuilder.build()).
    """

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.ollama_client = ollama_client or OllamaClient()

    def generate(self, ride_summary: dict, project_name: str) -> dict:
        """
        Returns:
            {
                "title": str | None,
                "description": str | None,
                "tags": list[str],
                "raw_response": str,
                "parse_error": bool,
            }

        parse_error is True if the model's response couldn't be
        parsed as the requested JSON structure - raw_response is
        still returned in full so nothing is lost, the caller
        just has to read it themselves instead of getting
        structured fields.
        """

        prompt = self._build_prompt(ride_summary, project_name)

        raw_response = self.ollama_client.generate(prompt)

        return self._parse_response(raw_response)

    def _build_prompt(self, ride_summary: dict, project_name: str) -> str:

        day_lines = []

        for day in ride_summary.get("days", []):

            parts = [f"Day {day['day']}"]

            if day.get("date"):
                parts.append(day["date"])

            parts.append(f"{day['duration_minutes']:.0f} min of footage")

            if day.get("places"):
                parts.append("places: " + ", ".join(day["places"]))

            if day.get("cameras"):
                parts.append("cameras: " + ", ".join(day["cameras"]))

            parts.append(f"{day['scene_count']} scene(s)")

            day_lines.append(" | ".join(parts))

        days_text = "\n".join(day_lines) or "No day data available."

        total_days = ride_summary.get("total_days", 0)

        return f"""{BRAND_VOICE_GUIDANCE}

Project name: {project_name}
Total riding days: {total_days}

Day-by-day facts (this is everything you know about this ride -
do not invent places, events, or details not listed here):
{days_text}

Generate YouTube metadata for this ride video. Respond with
ONLY a JSON object, no other text, in exactly this shape:

{{
  "title": "a single SEO-focused title, under 100 characters",
  "description": "a 3-5 paragraph description",
  "tags": ["tag1", "tag2", "..."]
}}
"""

    @staticmethod
    def _parse_response(raw_response: str) -> dict:

        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group(0))

                return {
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "tags": data.get("tags", []),
                    "raw_response": raw_response,
                    "parse_error": False,
                }
            except json.JSONDecodeError:
                pass

        return {
            "title": None,
            "description": None,
            "tags": [],
            "raw_response": raw_response,
            "parse_error": True,
        }
