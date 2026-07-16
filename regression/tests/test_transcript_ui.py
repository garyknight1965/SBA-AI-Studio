"""
============================================================
SBA AI Studio
Transcript UI Regression Test
ML-037
Version : 1.0.0
============================================================

Verifies:
- TranscriptWidget's set_loaded_file()/set_generating()/
  set_result()/set_error()/clear() all update the right fields,
  including the parse_error fallback (raw response shown, Save
  disabled rather than treating it as a usable script).
- IntelliScriptWorker emits `succeeded` with the generated result
  on success, and `failed` with a clear message on error - tested
  by calling run() directly (bypassing QThread.start()), so this
  never spins a real thread or touches a real Ollama instance.
- DockManager creates and exposes the Transcript panel, and clears
  it on refresh (matching the YouTube panel's behaviour).
"""

from __future__ import annotations

import os

from regression.base_test import BaseRegressionTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class TranscriptUiRegressionTest(BaseRegressionTest):

    name = "Transcript UI (ML-037)"

    category = "Resolve"

    description = (
        "Verify the Transcript panel's display logic and the "
        "IntelliScript worker's signal emission, using real "
        "headless Qt widgets and a directly-invoked worker.run() "
        "(no real thread, no real Ollama)."
    )

    def run(self) -> None:

        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        # --------------------------------------------------
        # 1. Widget display logic.
        # --------------------------------------------------

        from ui.widgets.transcript_widget import TranscriptWidget

        widget = TranscriptWidget()

        if widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should start disabled - no "
                "transcript has been loaded yet."
            )

        if widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should start disabled - nothing has "
                "been generated yet."
            )

        widget.set_loaded_file("sunday.txt")

        if not widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be enabled once a "
                "transcript is loaded."
            )

        if "sunday.txt" not in widget.file_label.text():
            raise RuntimeError(
                f"Expected the loaded filename in file_label, got "
                f"{widget.file_label.text()!r}."
            )

        widget.set_generating(True)

        if widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be disabled while "
                "generating."
            )

        if widget.load_button.isEnabled():
            raise RuntimeError(
                "Load button should be disabled while generating, "
                "to avoid swapping the transcript mid-request."
            )

        clean_result = {
            "script": "I tell you about my positive things.\n",
            "decisions": {0: {"keep": True, "paragraph_break_before": True}},
            "raw_response": "{...}",
            "parse_error": False,
            "segment_count": 1,
            "kept_count": 1,
        }

        widget.set_result(clean_result)
        widget.set_generating(False)

        if not widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be re-enabled after "
                "set_generating(False)."
            )

        if not widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should be enabled after a successful "
                "generation with a non-empty script."
            )

        if widget.current_script() != clean_result["script"]:
            raise RuntimeError(
                f"Expected current_script() to return the "
                f"generated script, got "
                f"{widget.current_script()!r}."
            )

        # parse_error fallback: raw response shown, Save disabled -
        # a raw, unparsed model response is not a usable script.
        parse_error_result = {
            "script": "",
            "decisions": {},
            "raw_response": "I can't help with that.",
            "parse_error": True,
            "segment_count": 1,
            "kept_count": 0,
        }

        widget.set_result(parse_error_result)

        if widget.current_script() != "I can't help with that.":
            raise RuntimeError(
                "Expected the raw response to be shown on "
                "parse_error."
            )

        if widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should be disabled on parse_error - "
                "a raw model response is not a usable script."
            )

        widget.set_error("Could not reach Ollama.")

        if "Could not reach Ollama" not in widget.status_label.text():
            raise RuntimeError(
                "set_error() should surface the error message in "
                "the status label."
            )

        if widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should be disabled after a failed "
                "generation."
            )

        widget.clear()

        if (
            widget.generate_button.isEnabled()
            or widget.save_button.isEnabled()
            or widget.status_label.text() != ""
            or widget.current_script() != ""
        ):
            raise RuntimeError("clear() did not reset all fields.")

        # --------------------------------------------------
        # 2. Worker signal emission (run() called directly - no
        #    real thread, no real Ollama).
        # --------------------------------------------------

        import ui.workers.intelliscript_worker as worker_module
        from ui.workers.intelliscript_worker import IntelliScriptWorker

        class FakeEditorSuccess:
            def __init__(self, *a, **k):
                pass

            def build_script(self, raw_text):
                return {
                    "script": "Test script.\n",
                    "decisions": {},
                    "raw_response": "{}",
                    "parse_error": False,
                    "segment_count": 3,
                    "kept_count": 2,
                }

        original_editor = worker_module.IntelliScriptEditor

        worker_module.IntelliScriptEditor = FakeEditorSuccess

        try:
            worker = IntelliScriptWorker(
                raw_transcript_text="[00:00:00:00 - 00:00:01:00]\n"
                "Speaker 1\n Hello.\n",
                model="llama3.2",
            )

            succeeded_calls = []
            failed_calls = []

            worker.succeeded.connect(
                lambda result: succeeded_calls.append(result)
            )
            worker.failed.connect(
                lambda message: failed_calls.append(message)
            )

            # Direct call, not .start() - runs synchronously on
            # this thread, no real QThread involved.
            worker.run()

            if len(succeeded_calls) != 1:
                raise RuntimeError(
                    f"Expected exactly 1 'succeeded' emission, got "
                    f"{len(succeeded_calls)}."
                )

            if failed_calls:
                raise RuntimeError(
                    "Expected no 'failed' emissions on the "
                    f"success path, got {failed_calls}."
                )

            if succeeded_calls[0]["script"] != "Test script.\n":
                raise RuntimeError(
                    f"Unexpected succeeded payload: "
                    f"{succeeded_calls[0]!r}"
                )

            # --------------------------------------------------
            # Failure path.
            # --------------------------------------------------

            from sba_resolve.core.services.ollama_client import (
                OllamaError,
            )

            class FakeEditorFailure:
                def __init__(self, *a, **k):
                    pass

                def build_script(self, raw_text):
                    raise OllamaError("Could not reach Ollama at test.")

            worker_module.IntelliScriptEditor = FakeEditorFailure

            worker2 = IntelliScriptWorker(
                raw_transcript_text="[00:00:00:00 - 00:00:01:00]\n"
                "Speaker 1\n Hello.\n",
                model="llama3.2",
            )

            succeeded_calls2 = []
            failed_calls2 = []

            worker2.succeeded.connect(
                lambda result: succeeded_calls2.append(result)
            )
            worker2.failed.connect(
                lambda message: failed_calls2.append(message)
            )

            worker2.run()

            if len(failed_calls2) != 1:
                raise RuntimeError(
                    f"Expected exactly 1 'failed' emission, got "
                    f"{len(failed_calls2)}."
                )

            if succeeded_calls2:
                raise RuntimeError(
                    "Expected no 'succeeded' emissions on the "
                    f"failure path, got {succeeded_calls2}."
                )

            if "Could not reach Ollama" not in failed_calls2[0]:
                raise RuntimeError(
                    f"Expected the OllamaError message to be "
                    f"passed through, got {failed_calls2[0]!r}."
                )

        finally:
            worker_module.IntelliScriptEditor = original_editor

        # --------------------------------------------------
        # 3. DockManager wiring.
        # --------------------------------------------------

        from pathlib import Path as _Path

        from PySide6.QtWidgets import QMainWindow

        from sba_resolve.core.models.workspace import Workspace
        from ui.layout.dock_manager import DockManager

        workspace = Workspace(
            project_name="Test Project",
            project_root=_Path("/fake/project"),
        )

        main_window = QMainWindow()

        dock_manager = DockManager(main_window)
        dock_manager.build(workspace)

        if not hasattr(dock_manager, "transcript_panel"):
            raise RuntimeError(
                "DockManager did not create a transcript_panel."
            )

        dock_manager.transcript_panel.set_result(clean_result)

        dock_manager.refresh(workspace)

        if dock_manager.transcript_panel.current_script() != "":
            raise RuntimeError(
                "DockManager.refresh() should clear the "
                "Transcript panel (matching the YouTube panel's "
                "behaviour on project switch), but stale data "
                "remained."
            )
