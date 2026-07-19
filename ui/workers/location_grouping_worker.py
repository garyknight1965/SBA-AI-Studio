"""
============================================================
SBA AI Studio
Location Grouping Worker
ML-040-002
Version : 1.0.0
============================================================

Runs LocationGrouper.group() on a background thread.
ReverseGeocoder makes real network calls (rate-limited to ~1
request/second per distinct location cluster), so this must never
run on the GUI thread - same reasoning as YouTubeMetadataWorker.

run() is deliberately plain, synchronous Python calling the
already-regression-tested LocationGrouper - it can be called
directly (bypassing QThread.start()) for testing without spinning
up a real thread or making real network calls (with a fake
geocoder injected).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.location_grouper import LocationGrouper


class LocationGroupingWorker(QThread):

    succeeded = Signal(list)

    failed = Signal(str)

    def __init__(self, media_list, parent=None) -> None:
        super().__init__(parent)
        self.media_list = list(media_list)

    def run(self) -> None:

        try:
            groups = LocationGrouper().group(self.media_list)

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        self.succeeded.emit(groups)
