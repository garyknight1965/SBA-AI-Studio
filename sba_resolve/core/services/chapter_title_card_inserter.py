"""
chapter_title_card_inserter.py

ML-055. Places one Fusion text title card per chapter on the timeline,
using the confirmed-safe mechanism from
tools/test_chapter_title_bootstrap.py (Candidate B, CONFIRMED
2026-07-20 on Gary's real Resolve setup):

    AppendToTimeline (placeholder image, explicit trackIndex/
    recordFrame, non-rippling) + ImportFusionComp (saved .comp
    template) + per-instance StyledText.

Zero manual clicks required at runtime. The saved template
(graphics_config.CHAPTER_TITLE_CARD_TEMPLATE_PATH) must exist on disk
before this runs -- it is built once, by hand, in Resolve's own Fusion
editor, then exported via TimelineItem.ExportFusionComp(). This module
does not build that template; see tools/test_chapter_title_bootstrap.py
for the export mechanism if it ever needs to be rebuilt.

Reads chapters from the live YouTube Metadata description field
(youtube_chapter_parser), NOT from IntelliScriptChapterGenerator's
internal model -- whatever Gary has actually typed/edited there is
what gets placed.
"""

import os

from sba_resolve.graphics_config import (
    CHAPTER_TITLE_CARD_TEMPLATE_PATH,
    TRACK_NAME_CHAPTER_TITLE_CARDS,
    TRACK_PREFIX_CHAPTER_TITLE_CARD,
    DEFAULT_SETTINGS,
)
from sba_resolve.resolve_graphic_inserter import GraphicInserter, GraphicRequest
from sba_resolve.core.services.youtube_chapter_parser import (
    parse_chapters_from_description,
)


class NoTemplateError(RuntimeError):
    """Raised when the saved chapter title card template doesn't exist yet."""


class NoChaptersFoundError(RuntimeError):
    """Raised when the description text has no parseable chapter lines."""


def insert_chapter_title_cards(description_text: str) -> list[str]:
    """Parses chapters out of description_text and places one title
    card per chapter on the shared 'AI Chapter Title Cards' track.

    Returns the list of clip names actually placed, in chapter order,
    so the caller can report what happened.

    Raises NoTemplateError if the template .comp hasn't been built/
    exported yet, NoChaptersFoundError if no valid chapter lines are
    found, and whatever ResolveConnectionError / AssetNotFoundError /
    GraphicPlacementError the underlying insert raises on failure.
    This is additive-only (per resolve_graphic_inserter.py's design
    constraints), so if a later chapter fails partway through, the
    earlier ones placed successfully are left in place -- that's a
    safe partial result, not a broken state -- but the error still
    propagates so Gary knows which chapters didn't make it.
    """
    if not os.path.isfile(CHAPTER_TITLE_CARD_TEMPLATE_PATH):
        raise NoTemplateError(
            f"No chapter title card template found at "
            f"'{CHAPTER_TITLE_CARD_TEMPLATE_PATH}'. Build and style it "
            f"once in Resolve's Fusion editor, then export it with "
            f"TimelineItem.ExportFusionComp() to that exact path "
            f"before running this."
        )

    chapters = parse_chapters_from_description(description_text)
    if not chapters:
        raise NoChaptersFoundError(
            "No valid chapter lines (M:SS or H:MM:SS followed by a "
            "label) were found in the description text."
        )

    inserter = GraphicInserter(settings=DEFAULT_SETTINGS)
    inserter.connect()

    placed_names = []
    for chapter in chapters:
        request = GraphicRequest(
            start_seconds=chapter.time_seconds,
            track_name=TRACK_NAME_CHAPTER_TITLE_CARDS,
            clip_name_prefix=TRACK_PREFIX_CHAPTER_TITLE_CARD,
            duration_seconds=DEFAULT_SETTINGS.chapter_title_card_duration_seconds,
            text=chapter.label,
            template_path=CHAPTER_TITLE_CARD_TEMPLATE_PATH,
        )
        clip_name = inserter.insert(request)
        placed_names.append(clip_name)

    return placed_names