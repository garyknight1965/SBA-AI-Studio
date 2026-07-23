"""
============================================================
SBA AI Studio
YouTube Metadata UI Regression Test
ML-028
Version : 1.0.0
============================================================

Verifies:
- YouTubeMetadataWidget's set_metadata()/set_generating()/
  set_error()/clear() all update the right fields, including
  the parse_error fallback (raw response shown, no crash).
- YouTubeMetadataWorker emits `succeeded` with the generated
  metadata on success, and `failed` with a clear message on
  error - tested by calling run() directly (bypassing
  QThread.start()) with the underlying services monkeypatched,
  so this never spins a real thread or touches a real Ollama
  instance.
- DockManager creates and exposes the YouTube panel, and clears
  it on refresh (matching the Metadata panel's behaviour).
"""

from __future__ import annotations

import os

from regression.base_test import BaseRegressionTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class YouTubeMetadataUiRegressionTest(BaseRegressionTest):

    name = "YouTube Metadata UI (ML-028)"

    requires_gui = True

    category = "Resolve"

    description = (
        "Verify the YouTube Metadata panel's display logic and "
        "the background worker's signal emission, using real "
        "headless Qt widgets and a directly-invoked worker.run() "
        "(no real thread, no real Ollama)."
    )

    def run(self) -> None:

        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        # --------------------------------------------------
        # 1. Widget display logic.
        # --------------------------------------------------

        from ui.widgets.youtube_metadata_widget import YouTubeMetadataWidget

        widget = YouTubeMetadataWidget()

        if widget.additional_notes() != "":
            raise RuntimeError(
                "additional_notes() should start empty."
            )

        widget.notes_field.setText("stopped at Stirling Castle")

        if widget.additional_notes() != "stopped at Stirling Castle":
            raise RuntimeError(
                f"Expected additional_notes() to return the typed "
                f"text, got {widget.additional_notes()!r}."
            )

        widget.set_generating(True)

        if widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be disabled while "
                "generating."
            )

        clean_metadata = {
            "title": "Whithorn Castle Ride",
            "description": "A day's ride to Whithorn.",
            "tags": ["motorcycle", "scotland"],
            "raw_response": "...",
            "parse_error": False,
        }

        widget.set_metadata(clean_metadata)
        widget.set_generating(False)

        if not widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be re-enabled after "
                "set_generating(False)."
            )

        if widget.title_field.text() != "Whithorn Castle Ride":
            raise RuntimeError(
                f"Expected title field to show 'Whithorn Castle "
                f"Ride', got {widget.title_field.text()!r}."
            )

        if widget.tags_field.text() != "motorcycle, scotland":
            raise RuntimeError(
                f"Expected tags field 'motorcycle, scotland', got "
                f"{widget.tags_field.text()!r}."
            )

        # parse_error fallback: raw response shown, title/tags
        # blanked rather than showing stale data.
        parse_error_metadata = {
            "title": None,
            "description": None,
            "tags": [],
            "raw_response": "I can't help with that.",
            "parse_error": True,
        }

        widget.set_metadata(parse_error_metadata)

        if widget.description_field.toPlainText() != (
            "I can't help with that."
        ):
            raise RuntimeError(
                "Expected the raw response to be shown in the "
                "description field on parse_error."
            )

        if widget.title_field.text() != "":
            raise RuntimeError(
                "Title field should be cleared on parse_error, "
                f"not show stale data, got "
                f"{widget.title_field.text()!r}."
            )

        widget.set_error("Could not reach Ollama.")

        if "Could not reach Ollama" not in widget.status_label.text():
            raise RuntimeError(
                "set_error() should surface the error message in "
                "the status label."
            )

        widget.clear()

        if (
            widget.title_field.text() != ""
            or widget.status_label.text() != ""
            or widget.additional_notes() != ""
        ):
            raise RuntimeError("clear() did not reset all fields.")

        # --------------------------------------------------
        # 2. Worker signal emission (run() called directly - no
        #    real thread, no real Ollama).
        # --------------------------------------------------

        from datetime import datetime
        from pathlib import Path

        from sba_resolve.core.models.camera_profile import (
            CameraManufacturer,
            CameraProfile,
            CameraType,
        )
        from sba_resolve.core.models.media_file import MediaFile

        profile = CameraProfile(
            manufacturer=CameraManufacturer.GOPRO,
            model="HERO13 Black",
            family="Hero",
            camera_type=CameraType.ACTION,
            confidence=100,
            detection_method="Test Fixture",
        )

        media = MediaFile(
            filename="clip1.mp4",
            full_path=Path("/fake/clip1.mp4"),
            relative_path=Path("clip1.mp4"),
            extension=".mp4",
            size=1024,
            camera_model="HERO13 Black",
            camera_profile=profile,
            created=datetime(2026, 7, 1, 9, 0, 0),
            duration="60",
            fps=25.0,
        )

        import ui.workers.youtube_metadata_worker as worker_module
        from ui.workers.youtube_metadata_worker import YouTubeMetadataWorker

        class FakeGeneratorSuccess:
            def __init__(self, *a, **k):
                pass

            def generate(
                self, summary, project_name, extra_notes="", chapter_days=None
            ):
                return {
                    "title": "Test Title",
                    "description": "Test description.",
                    "tags": ["test"],
                    "raw_response": "{}",
                    "parse_error": False,
                }

        original_generator = worker_module.YouTubeMetadataGenerator

        worker_module.YouTubeMetadataGenerator = FakeGeneratorSuccess

        try:
            worker = YouTubeMetadataWorker(
                media_list=[media],
                project_name="Test Project",
                model="llama3.2",
            )

            succeeded_calls = []
            failed_calls = []

            worker.succeeded.connect(
                lambda metadata: succeeded_calls.append(metadata)
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

            if succeeded_calls[0]["title"] != "Test Title":
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

            class FakeGeneratorFailure:
                def __init__(self, *a, **k):
                    pass

                def generate(
                    self, summary, project_name, extra_notes="", chapter_days=None
                ):
                    raise OllamaError("Could not reach Ollama at test.")

            worker_module.YouTubeMetadataGenerator = FakeGeneratorFailure

            worker2 = YouTubeMetadataWorker(
                media_list=[media],
                project_name="Test Project",
                model="llama3.2",
            )

            succeeded_calls2 = []
            failed_calls2 = []

            worker2.succeeded.connect(
                lambda metadata: succeeded_calls2.append(metadata)
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
            worker_module.YouTubeMetadataGenerator = original_generator

        # --------------------------------------------------
        # 3. DockManager wiring.
        # --------------------------------------------------

        from pathlib import Path as _Path

        from PySide6.QtWidgets import QMainWindow

        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.models.workspace import Workspace
        from ui.layout.dock_manager import DockManager

        library = MediaLibrary()
        library.add(media)

        workspace = Workspace(
            project_name="Test Project",
            project_root=_Path("/fake/project"),
            media=library,
        )

        # This is the exact attribute access that crashed
        # generate_youtube_metadata() in real use -
        # MediaLibrary has no is_empty attribute, only
        # __len__/__iter__, so Workspace.is_empty must not
        # reach into media.is_empty directly.
        if workspace.is_empty:
            raise RuntimeError(
                "Workspace.is_empty should be False when media "
                "has been added."
            )

        empty_workspace = Workspace(
            project_name="Empty",
            project_root=_Path("/fake/empty"),
        )

        if not empty_workspace.is_empty:
            raise RuntimeError(
                "Workspace.is_empty should be True for a freshly "
                "constructed, empty workspace."
            )

        main_window = QMainWindow()

        dock_manager = DockManager(main_window)
        dock_manager.build(workspace)

        if not hasattr(dock_manager, "youtube_panel"):
            raise RuntimeError(
                "DockManager did not create a youtube_panel."
            )

        dock_manager.youtube_panel.set_metadata(clean_metadata)

        dock_manager.refresh(workspace)

        if dock_manager.youtube_panel.title_field.text() != "":
            raise RuntimeError(
                "DockManager.refresh() should clear the YouTube "
                "panel (matching the Metadata panel's behaviour "
                "on project switch), but stale data remained."
            )