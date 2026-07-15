"""
============================================================
SBA AI Studio
GoPro Chapter Resequencer
ML-022-001
Version : 1.0.0 Alpha
============================================================

GoPro splits a single continuous recording into multiple
"chapter" files once it exceeds a size/duration limit, using
the filename convention G{H|X}{chapter:2d}{session:4d}.MP4 -
e.g. GH010145.MP4, GH020145.MP4, GH030145.MP4 are chapters 1, 2,
and 3 of the SAME continuous recording (session "0145").

Critically, GoPro embeds the SAME creation timestamp (the start
of chapter 1) into every chapter's own metadata - so without
correction, every chapter after the first reports an IDENTICAL
capture time. That collapses them onto the exact same timeline
position instead of playing back-to-back, which is why multiple
real, distinct chapter files were landing on the exact same
frame and silently failing to place (confirmed via the ML-017/
ML-018 placement diagnostics: a real, data-level bug, not a
Resolve API quirk).

This service groups files by (camera, session number), sorts by
chapter number, and recomputes each chapter-after-the-first's
capture time as the previous chapter's (possibly already
corrected) time plus the previous chapter's duration - chaining
them into their real, sequential positions.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from typing import Iterable

# G{H|X}{chapter:2d}{session:4d}.MP4 - e.g. GH010145.MP4.
_CHAPTER_PATTERN = re.compile(
    r"^G[HX](\d{2})(\d{4})\.MP4$", re.IGNORECASE
)


class GoProChapterResequencer:
    """
    Corrects capture timestamps for multi-chapter GoPro
    recordings in place.
    """

    def resequence(self, media_files: Iterable) -> None:
        """
        Mutates `media.created` in place for any GoPro chapter
        file after the first chapter of its recording session.
        """

        groups: dict[tuple[str, str], list[tuple[int, object]]] = (
            defaultdict(list)
        )

        for media in media_files:

            match = _CHAPTER_PATTERN.match(media.filename)

            if not match:
                continue

            if getattr(media, "created", None) is None:
                continue

            chapter = int(match.group(1))
            session = match.group(2)

            camera = self._camera_signature(media)

            groups[(camera, session)].append((chapter, media))

        for members in groups.values():

            if len(members) < 2:
                # A lone chapter (session number happens to
                # match the pattern but there's only one file) -
                # nothing to resequence.
                continue

            members.sort(key=lambda pair: pair[0])

            # Chapter 1 keeps its real, metadata-derived
            # timestamp as the anchor. Every later chapter chains
            # off the PREVIOUS chapter's (possibly already
            # corrected) time plus that chapter's duration.
            previous_media = members[0][1]

            for _chapter, media in members[1:]:

                previous_time = getattr(
                    previous_media, "created", None
                )

                if previous_time is None:
                    previous_media = media
                    continue

                previous_duration = self._duration_seconds(
                    previous_media
                )

                media.created = previous_time + timedelta(
                    seconds=previous_duration
                )

                previous_media = media

    @staticmethod
    def _camera_signature(media) -> str:

        return (
            getattr(media, "camera_display_name", None)
            or getattr(media, "camera_model", None)
            or "Unknown"
        )

    @staticmethod
    def _duration_seconds(media) -> float:

        raw_duration = getattr(media, "duration", "")

        try:
            return float(raw_duration)
        except (TypeError, ValueError):
            return 0.0
