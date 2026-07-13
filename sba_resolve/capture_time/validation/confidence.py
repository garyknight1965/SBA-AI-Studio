"""
SBA AI Studio
Capture Time Confidence Engine

Provides confidence scores for timestamp sources.

Author: SBA AI Studio
"""

from __future__ import annotations

from typing import Final

# ----------------------------------------------------------------------
# Confidence scores
# ----------------------------------------------------------------------

CONFIDENCE_SCORES: Final[dict[str, int]] = {
    "DateTimeOriginal": 100,
    "MediaCreateDate": 95,
    "CreateDate": 90,
    "TrackCreateDate": 80,
    "Filename": 60,
    "FileCreateDate": 40,
    "FileModifyDate": 20,
}


DEFAULT_CONFIDENCE: Final[int] = 0


def get_confidence(source: str) -> int:
    """
    Returns the confidence score for a metadata source.

    Parameters
    ----------
    source:
        Metadata field name.

    Returns
    -------
    int
        Confidence score.
    """
    return CONFIDENCE_SCORES.get(source, DEFAULT_CONFIDENCE)


def is_known_source(source: str) -> bool:
    """
    Returns True if the source is recognised.
    """
    return source in CONFIDENCE_SCORES