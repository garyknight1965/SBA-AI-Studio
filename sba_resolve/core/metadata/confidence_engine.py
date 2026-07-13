"""
============================================================
SBA AI Studio
Confidence Engine
Version : 1.0.0
Sprint  : MI-002B
============================================================
"""

from __future__ import annotations


class ConfidenceEngine:
    """
    Provides confidence scores for timestamp sources.
    """

    _SCORES = {
        "DateTimeOriginal": 100,
        "CreateDate": 95,
        "MediaCreateDate": 90,
        "GPSDateTime": 85,
        "DJI Filename": 40,
        "Insta360 Filename": 40,
        "GoPro Filename": 35,
        "FileModified": 10,
    }

    @classmethod
    def score(cls, source: str) -> int:
        """
        Return the confidence score for a timestamp source.
        """
        return cls._SCORES.get(source, 0)