"""
============================================================
SBA AI Studio
IntelliScript Worker
ML-037-002
Version : 1.0.0
============================================================

Runs IntelliScriptEditor.build_script() (Resolve transcript ->
keep/cut + paragraph decisions via Ollama -> deterministic
assembly) on a background thread, so a slow model load or an
unreachable Ollama instance doesn't freeze the GUI.

run() is deliberately plain, synchronous Python calling the
already-regression-tested IntelliScriptEditor - it can be called
directly (bypassing QThread.start()) for testing without spinning
up a real thread, matching YouTubeMetadataWorker's pattern.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.intelliscript_editor import (
    IntelliScriptEditor,
)
from sba_resolve.core.services.ollama_client import OllamaClient, OllamaError


class IntelliScriptWorker(QThread):

    succeeded = Signal(dict)

    failed = Signal(str)

    def __init__(
        self,
        raw_transcript_text: str,
        model: str = "llama3.2",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.raw_transcript_text = raw_transcript_text
        self.model = model

    def run(self) -> None:

        try:
            editor = IntelliScriptEditor(
                ollama_client=OllamaClient(model=self.model)
            )

            result = editor.build_script(self.raw_transcript_text)

        except OllamaError as exc:
            self.failed.emit(str(exc))
            return

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        self.succeeded.emit(result)
