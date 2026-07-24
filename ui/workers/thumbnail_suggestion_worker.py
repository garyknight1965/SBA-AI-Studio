"""
============================================================
SBA AI Studio
Thumbnail Suggestion Worker
ML-061
Version : 1.0.0
============================================================

Runs ThumbnailFrameExtractor.suggest_candidates() on a background
thread - decoding several video files to grab candidate frames can
take a noticeable moment, so this must never run on the GUI thread,
same reasoning as every other worker in this project.

run() is deliberately plain, synchronous Python calling the
already-regression-tested ThumbnailFrameExtractor - it can be called
directly (bypassing QThread.start()) for testing without spinning up
a real thread or reading real video files (with a fake frame_reader
injected).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.thumbnail_generator import (
    ThumbnailFrameExtractor,
)


class ThumbnailSuggestionWorker(QThread):

    succeeded = Signal(list)

    failed = Signal(str)

    def __init__(self, media_list, count=5, parent=None) -> None:
        super().__init__(parent)
        self.media_list = list(media_list)
        self.count = count

    def run(self) -> None:

        try:
            candidates = ThumbnailFrameExtractor().suggest_candidates(
                self.media_list, count=self.count
            )

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        if not candidates:
            self.failed.emit(
                "Could not extract any candidate frames from this "
                "project's footage."
            )
            return

        self.succeeded.emit(candidates)
