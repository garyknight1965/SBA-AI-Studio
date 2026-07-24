"""
============================================================
SBA AI Studio
Thumbnail UI Regression Test
ML-061
Version : 1.0.0
============================================================

Runs the real (headless, offscreen) ThumbnailWidget to verify:

- set_candidates() creates one clickable preview button per
  candidate, and resets selection/preview state.
- Clicking a candidate composites it and enables Save.
- set_suggested_text() only pre-fills the text field when it's
  currently empty - never clobbers something Gary already typed.
- set_logo_path() recomputes the preview with the new logo.
- set_error() surfaces the message; clear() resets every field.
- DockManager creates and exposes the Thumbnail panel, and clears
  it on refresh (matching the other panels' behaviour).
"""

from __future__ import annotations

import os

from regression.base_test import BaseRegressionTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ThumbnailUiRegressionTest(BaseRegressionTest):

    name = "Thumbnail UI (ML-061)"

    requires_gui = True

    category = "Resolve"

    description = (
        "Verify the Thumbnail panel's candidate selection/preview "
        "logic using real headless Qt widgets and synthetic "
        "in-memory frames (no real video files)."
    )

    def _make_candidates(self, count=3):

        import numpy as np

        from sba_resolve.core.services.thumbnail_generator import (
            ThumbnailCandidate,
        )

        candidates = []

        for i in range(count):
            image = np.full((360, 640, 3), (10, 20, 30 + i), dtype=np.uint8)
            candidates.append(
                ThumbnailCandidate(
                    clip_name=f"clip{i}.mp4",
                    timestamp_seconds=float(i * 10),
                    image=image,
                )
            )

        return candidates

    def run(self) -> None:

        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        # --------------------------------------------------
        # 1. Widget display logic.
        # --------------------------------------------------

        from ui.widgets.thumbnail_widget import ThumbnailWidget

        widget = ThumbnailWidget()

        if widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should start disabled - nothing has "
                "been suggested/selected yet."
            )

        candidates = self._make_candidates(3)

        widget.set_candidates(candidates)

        if widget.candidates_row.count() != 3:
            raise RuntimeError(
                f"Expected 3 candidate buttons, got "
                f"{widget.candidates_row.count()}."
            )

        if widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should still be disabled - a "
                "candidate hasn't been selected yet, only "
                "suggested."
            )

        # Simulate clicking the second candidate.
        widget._select_candidate(1)

        if not widget.save_button.isEnabled():
            raise RuntimeError(
                "Save button should be enabled once a candidate "
                "is selected and composited."
            )

        if widget._composed_image is None:
            raise RuntimeError(
                "Expected a composed preview image after "
                "selecting a candidate."
            )

        if widget._composed_image.size != (1280, 720):
            raise RuntimeError(
                f"Expected the composed preview to be 1280x720, "
                f"got {widget._composed_image.size!r}."
            )

        # --------------------------------------------------
        # 2. set_suggested_text() only pre-fills when empty.
        # --------------------------------------------------

        widget2 = ThumbnailWidget()

        widget2.set_suggested_text("WHITHORN CASTLE RIDE")

        if widget2.text_field.text() != "WHITHORN CASTLE RIDE":
            raise RuntimeError(
                "Expected set_suggested_text() to pre-fill an "
                "empty text field."
            )

        widget2.set_suggested_text("SOMETHING ELSE ENTIRELY")

        if widget2.text_field.text() != "WHITHORN CASTLE RIDE":
            raise RuntimeError(
                "set_suggested_text() should NOT overwrite text "
                "the field already has - it should only pre-fill "
                "when empty."
            )

        # --------------------------------------------------
        # 3. set_logo_path() recomputes the preview (no crash
        #    with a candidate already selected).
        # --------------------------------------------------

        widget.set_logo_path("/definitely/does/not/exist.png")

        if widget._composed_image is None:
            raise RuntimeError(
                "Expected the preview to still be composed after "
                "set_logo_path() with a missing file (handled "
                "gracefully, not cleared)."
            )

        # --------------------------------------------------
        # 4. set_error() surfaces the message.
        # --------------------------------------------------

        widget.set_error("Could not decode any frames.")

        if "Could not decode any frames" not in widget.status_label.text():
            raise RuntimeError(
                "set_error() should surface the error message in "
                "the status label."
            )

        # --------------------------------------------------
        # 5. clear() resets everything.
        # --------------------------------------------------

        widget.clear()

        if (
            widget.candidates_row.count() != 0
            or widget.save_button.isEnabled()
            or widget.text_field.text() != ""
            or widget.status_label.text() != ""
            or widget._composed_image is not None
        ):
            raise RuntimeError("clear() did not reset all fields.")

        # --------------------------------------------------
        # 6. DockManager wiring.
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

        if not hasattr(dock_manager, "thumbnail_panel"):
            raise RuntimeError(
                "DockManager did not create a thumbnail_panel."
            )

        dock_manager.thumbnail_panel.set_candidates(candidates)
        dock_manager.thumbnail_panel._select_candidate(0)

        dock_manager.refresh(workspace)

        if (
            dock_manager.thumbnail_panel.candidates_row.count() != 0
            or dock_manager.thumbnail_panel._composed_image is not None
        ):
            raise RuntimeError(
                "DockManager.refresh() should clear the Thumbnail "
                "panel (matching the other panels' behaviour on "
                "project switch), but stale data remained."
            )
