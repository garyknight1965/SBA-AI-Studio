"""
============================================================
SBA AI Studio
IntelliScript Worker
ML-037-002
Version : 1.1.0
============================================================

Runs IntelliScriptEditor.build_script() (Resolve transcript ->
keep/cut + paragraph decisions via the configured AI provider ->
deterministic assembly) on a background thread, so a slow model
load or an unreachable backend doesn't freeze the GUI.

run() is deliberately plain, synchronous Python calling the
already-regression-tested IntelliScriptEditor - it can be called
directly (bypassing QThread.start()) for testing without spinning
up a real thread, matching YouTubeMetadataWorker's pattern.

Version 1.1.0 (Groq provider backlog item): IntelliScriptEditor's
default (get_ai_provider()) now reads Settings' AI Provider choice
(Ollama or Groq) and its model itself, so this worker no longer
constructs a client itself. The "model" parameter is kept ONLY for
backward compatibility with existing regression tests that still
pass it (e.g. model="llama3.2") - it is accepted but intentionally
unused; provider/model selection now happens entirely inside
IntelliScriptEditor's default. A future cleanup could remove this
parameter once those tests are updated to stop passing it.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.groq_provider import GroqError
from sba_resolve.core.services.intelliscript_editor import (
    IntelliScriptEditor,
)
from sba_resolve.core.services.ollama_client import OllamaError


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
        # Accepted for backward compatibility only - see class
        # docstring. Intentionally not used to construct anything.
        self.model = model

    def run(self) -> None:

        try:
            editor = IntelliScriptEditor()

            result = editor.build_script(self.raw_transcript_text)

        except (OllamaError, GroqError) as exc:
            self.failed.emit(str(exc))
            return

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        self.succeeded.emit(result)