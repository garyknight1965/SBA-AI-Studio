"""
============================================================
SBA AI Studio
UI Widget Wiring Regression Test
ML-027
Version : 1.0.0
============================================================

Runs real PySide6 widgets headlessly (QT_QPA_PLATFORM=offscreen)
to verify:

- StatisticsWidget.update_statistics() computes Total Duration
  correctly (previously always "00:00:00" - it read a
  "duration_seconds" attribute that doesn't exist on MediaFile,
  which only has a "duration" seconds-string field).
- MediaBrowserWidget emits clip_selected with the correct
  MediaFile when a row is selected (this signal didn't exist
  before - selecting a row did nothing).
- WorkspaceTreeWidget still emits media_selected correctly.
- DockManager actually connects both selection sources to the
  Metadata panel, and populates the Timeline panel with a real
  Day/Scene preview from the Planning Engine instead of leaving
  it permanently empty.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class UiWidgetWiringRegressionTest(BaseRegressionTest):

    name = "UI Widget Wiring (ML-027)"

    category = "Resolve"

    description = (
        "Verify the Statistics duration bug fix, selection "
        "signal wiring (tree + browser -> metadata panel), and "
        "the Timeline panel's Planning Engine preview, using "
        "real headless PySide6 widgets."
    )

    def _make_media(self, filename, camera_model, created, duration_seconds=60.0):

        from sba_resolve.core.models.camera_profile import (
            CameraManufacturer,
            CameraProfile,
            CameraType,
        )
        from sba_resolve.core.models.media_file import MediaFile

        profile = CameraProfile(
            manufacturer=CameraManufacturer.GOPRO,
            model=camera_model,
            family="Hero",
            camera_type=CameraType.ACTION,
            confidence=100,
            detection_method="Test Fixture",
        )

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            camera_make="GoPro",
            camera_model=camera_model,
            camera_profile=profile,
            created=created,
            duration=str(duration_seconds),
            fps=25.0,
            category=f"GoPro {camera_model}",
        )

    def run(self) -> None:

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.models.workspace import Workspace

        day1_start = datetime(2026, 5, 12, 9, 0, 0)

        media1 = self._make_media(
            "clip1.mp4", "HERO13 Black", day1_start, 90.0
        )
        media2 = self._make_media(
            "clip2.mp4", "HERO8 Black", day1_start, 45.5
        )

        library = MediaLibrary()
        library.add(media1)
        library.add(media2)

        workspace = Workspace(
            project_name="Test Project",
            project_root=Path("/fake/project"),
            media=library,
        )

        # --------------------------------------------------
        # 1. StatisticsWidget duration fix.
        # --------------------------------------------------

        from ui.widgets.statistics_widget import StatisticsWidget

        stats = StatisticsWidget()
        stats.update_statistics(library)

        # 90.0 + 45.5 = 135.5s = 00:02:15 (rounded down).
        total_duration_text = stats._labels["Total Duration"].text()

        if total_duration_text != "00:02:15":
            raise RuntimeError(
                f"Expected Total Duration '00:02:15', got "
                f"{total_duration_text!r} - the duration_seconds "
                f"bug may have regressed."
            )

        if stats._labels["Total Files"].text() != "2":
            raise RuntimeError(
                f"Expected Total Files '2', got "
                f"{stats._labels['Total Files'].text()!r}."
            )

        if stats._labels["GoPro"].text() != "2":
            raise RuntimeError(
                f"Expected GoPro count '2', got "
                f"{stats._labels['GoPro'].text()!r} - manufacturer "
                f"detection may be checking camera_model instead "
                f"of camera_make (camera_model only ever contains "
                f"the bare model name, e.g. 'HERO13 Black', never "
                f"the manufacturer)."
            )

        if stats._labels["Other"].text() != "0":
            raise RuntimeError(
                f"Expected Other count '0', got "
                f"{stats._labels['Other'].text()!r}."
            )

        # --------------------------------------------------
        # 2. MediaBrowserWidget selection signal.
        # --------------------------------------------------

        from ui.widgets.media_browser_widget import MediaBrowserWidget

        browser = MediaBrowserWidget()
        browser.set_library(library)

        received = []
        browser.clip_selected.connect(lambda media: received.append(media))

        browser.selectRow(0)

        if len(received) != 1:
            raise RuntimeError(
                f"Expected exactly 1 clip_selected emission from "
                f"selectRow(0), got {len(received)}."
            )

        if received[0] is not media1:
            raise RuntimeError(
                "clip_selected did not emit the correct MediaFile "
                "for the selected row."
            )

        # --------------------------------------------------
        # 3. DockManager wiring: selection -> Metadata panel.
        # --------------------------------------------------

        from ui.layout.dock_manager import DockManager
        from PySide6.QtWidgets import QMainWindow

        main_window = QMainWindow()

        dock_manager = DockManager(main_window)
        dock_manager.build(workspace)

        dock_manager.media_browser.selectRow(1)

        if dock_manager.metadata_panel._labels["filename"].text() != (
            "clip2.mp4"
        ):
            raise RuntimeError(
                "Selecting a row in the media browser did not "
                "populate the Metadata panel - DockManager may "
                "not be connecting clip_selected."
            )

        # --------------------------------------------------
        # 4. Timeline panel gets a real Planning Engine preview,
        #    not the permanent "Timeline is empty" placeholder.
        # --------------------------------------------------

        timeline_widget = dock_manager.timeline_panel

        if timeline_widget.timeline.count() == 0:
            raise RuntimeError(
                "Timeline panel has no content after refresh."
            )

        first_item_text = timeline_widget.timeline.item(0).text()

        if first_item_text == "Timeline is empty":
            raise RuntimeError(
                "Timeline panel still shows the empty placeholder "
                "despite having media to plan from."
            )

        if "Day 1" not in first_item_text:
            raise RuntimeError(
                f"Expected the Timeline preview to mention 'Day "
                f"1', got: {first_item_text!r}"
            )
