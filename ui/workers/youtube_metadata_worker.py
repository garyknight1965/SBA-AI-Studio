"""
============================================================
SBA AI Studio
YouTube Metadata Worker
ML-028-002
Version : 1.0.0 Alpha
============================================================

Runs YouTube metadata generation (Planning Engine -> ride
summary -> Ollama) on a background thread, so a slow model load
or an unreachable Ollama instance doesn't freeze the GUI.

run() is deliberately plain, synchronous Python calling
already-regression-tested services (TimelinePlanningService,
RideSummaryBuilder, YouTubeMetadataGenerator) - it can be called
directly (bypassing QThread.start()) for testing without
spinning up a real thread.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.ollama_client import OllamaClient, OllamaError
from sba_resolve.core.services.ride_summary_builder import RideSummaryBuilder
from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)
from sba_resolve.core.services.youtube_metadata_generator import (
    YouTubeMetadataGenerator,
)


class YouTubeMetadataWorker(QThread):

    succeeded = Signal(dict)

    failed = Signal(str)

    def __init__(
        self,
        media_list,
        project_name: str,
        model: str = "llama3.2",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.media_list = list(media_list)
        self.project_name = project_name
        self.model = model

    def run(self) -> None:

        try:
            result = TimelinePlanningService().plan(self.media_list)

            summary = RideSummaryBuilder().build(result)

            generator = YouTubeMetadataGenerator(
                ollama_client=OllamaClient(model=self.model)
            )

            metadata = generator.generate(summary, self.project_name)

        except OllamaError as exc:
            self.failed.emit(str(exc))
            return

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        self.succeeded.emit(metadata)
