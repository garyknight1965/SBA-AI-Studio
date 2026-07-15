"""
============================================================
SBA AI Studio
Generate YouTube Metadata
ML-026
============================================================

Standalone entry point: scans a footage folder, runs the
Planning Engine, and generates a DRAFT YouTube title/
description/tags via a local Ollama model - all without
needing DaVinci Resolve connected at all.

Usage:
    python generate_youtube_metadata.py "D:\\Movies\\12-05-2026 castle"

Requires Ollama running locally (default: http://localhost:11434).
Install/pull a model first if you haven't, e.g.:
    ollama pull llama3.2

To use a different model, edit MODEL_NAME below.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sba_resolve.core.media_import_pipeline import MediaImportPipeline
from sba_resolve.core.services.ollama_client import OllamaClient, OllamaError
from sba_resolve.core.services.ride_summary_builder import RideSummaryBuilder
from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)
from sba_resolve.core.services.youtube_metadata_generator import (
    YouTubeMetadataGenerator,
)

# Change this to whatever model you have pulled in Ollama.
MODEL_NAME = "llama3.2"


def main() -> int:

    if len(sys.argv) < 2:
        print("Usage: python generate_youtube_metadata.py <footage_folder>")
        return 1

    folder = Path(sys.argv[1])

    if not folder.exists():
        print(f"Folder not found: {folder}")
        return 1

    project_name = folder.name

    print("=" * 60)
    print("Scanning footage")
    print("=" * 60)

    pipeline = MediaImportPipeline()

    media = pipeline.import_folder(folder)

    if pipeline.last_validation_report:
        pipeline.last_validation_report.print_report()

    if not media:
        print("No usable media found - nothing to summarise.")
        return 1

    print()
    print("=" * 60)
    print("Running Planning Engine")
    print("=" * 60)

    result = TimelinePlanningService().plan(media)

    print(f"Ride days : {result.statistics.ride_days}")
    print(f"Scenes    : {result.statistics.scenes}")

    print()
    print("=" * 60)
    print("Building ride summary")
    print("=" * 60)
    print("(reverse-geocoding GPS coordinates, if present - this")
    print("can take a moment, ~1 request/second)")
    print()

    summary = RideSummaryBuilder().build(result)

    for day in summary["days"]:
        print(
            f"Day {day['day']} | {day['date'] or 'unknown date'} | "
            f"{day['duration_minutes']:.0f} min | "
            f"{day['scene_count']} scene(s) | "
            f"cameras: {', '.join(day['cameras']) or 'unknown'} | "
            f"places: {', '.join(day['places']) or 'none found'}"
        )

    print()
    print("=" * 60)
    print(f"Generating YouTube metadata (model: {MODEL_NAME})")
    print("=" * 60)

    generator = YouTubeMetadataGenerator(
        ollama_client=OllamaClient(model=MODEL_NAME)
    )

    try:
        metadata = generator.generate(summary, project_name)
    except OllamaError as exc:
        print(f"ERROR: {exc}")
        return 1

    if metadata["parse_error"]:
        print(
            "WARNING: could not parse a clean title/description/tags "
            "structure from the model's response. Raw response:"
        )
        print()
        print(metadata["raw_response"])
        return 0

    print()
    print("Title:")
    print(f"  {metadata['title']}")
    print()
    print("Description:")
    print(metadata["description"])
    print()
    print("Tags:")
    print(f"  {', '.join(metadata['tags'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
