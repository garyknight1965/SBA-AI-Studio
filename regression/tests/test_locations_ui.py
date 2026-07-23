"""
============================================================
SBA AI Studio
Locations UI Regression Test
ML-040
Version : 1.0.0
============================================================

Verifies:
- LocationsWidget's set_generating()/set_groups()/set_error()/
  clear() all update the right fields.
- LocationGroupingWorker emits `succeeded` with LocationGroup
  results on success, and `failed` with a clear message on error -
  tested by calling run() directly (bypassing QThread.start()) with
  LocationGrouper's geocoder faked, so this never spins a real
  thread or makes a real network call.
- DockManager creates and exposes the Locations panel, and clears
  it on refresh (matching the other panels' behaviour).
"""

from __future__ import annotations

import os
from pathlib import Path

from regression.base_test import BaseRegressionTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FakeGeocoder:
    def __init__(self, table: dict) -> None:
        self.table = table

    def place_name(self, latitude, longitude):
        return self.table.get((latitude, longitude))


class LocationsUiRegressionTest(BaseRegressionTest):

    name = "Locations UI (ML-040)"

    requires_gui = True

    category = "Resolve"

    description = (
        "Verify the Locations panel's display logic and the "
        "location grouping worker's signal emission, using real "
        "headless Qt widgets and a directly-invoked worker.run() "
        "(no real thread, no real network calls)."
    )

    def _make_media(self, filename, latitude, longitude):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            gps_latitude=latitude,
            gps_longitude=longitude,
        )

    def run(self) -> None:

        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        # --------------------------------------------------
        # 1. Widget display logic.
        # --------------------------------------------------

        from ui.widgets.locations_widget import LocationsWidget

        widget = LocationsWidget()

        if not widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should start enabled."
            )

        if widget.location_list.count() != 1:
            raise RuntimeError(
                "Locations list should start with exactly one "
                "placeholder item."
            )

        widget.set_generating(True)

        if widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be disabled while "
                "generating."
            )

        from sba_resolve.core.models.location_group import (
            UNKNOWN_LOCATION,
            LocationGroup,
        )

        groups = [
            LocationGroup(
                place_name="Aachen, North Rhine-Westphalia, Germany",
                clips=["clip1.mp4"],
            ),
            LocationGroup(
                place_name=UNKNOWN_LOCATION,
                clips=["clip2.mp4", "clip3.mp4"],
            ),
        ]

        widget.set_groups(groups)
        widget.set_generating(False)

        if not widget.generate_button.isEnabled():
            raise RuntimeError(
                "Generate button should be re-enabled after "
                "set_generating(False)."
            )

        if widget.location_list.count() != 2:
            raise RuntimeError(
                f"Expected 2 items in the location list, got "
                f"{widget.location_list.count()}."
            )

        first_item_text = widget.location_list.item(0).text()

        if "Aachen" not in first_item_text or "1 clip" not in first_item_text:
            raise RuntimeError(
                f"Expected the Aachen group to show its clip "
                f"count, got {first_item_text!r}."
            )

        if "1 known location" not in widget.status_label.text():
            raise RuntimeError(
                f"Expected the status label to report 1 known "
                f"location, got {widget.status_label.text()!r}."
            )

        widget.set_error("Could not reach the geocoding service.")

        if (
            "Could not reach the geocoding service"
            not in widget.status_label.text()
        ):
            raise RuntimeError(
                "set_error() should surface the error message in "
                "the status label."
            )

        widget.clear()

        if (
            widget.location_list.count() != 1
            or "No locations generated yet"
            not in widget.location_list.item(0).text()
        ):
            raise RuntimeError("clear() did not reset the location list.")

        # --------------------------------------------------
        # 2. Worker signal emission (run() called directly - no
        #    real thread, no real network call).
        # --------------------------------------------------

        import ui.workers.location_grouping_worker as worker_module
        from ui.workers.location_grouping_worker import (
            LocationGroupingWorker,
        )

        whithorn_clip = self._make_media(
            "clip1.mp4", 54.73, -4.42
        )
        no_gps_clip = self._make_media("clip2.mp4", None, None)

        fake_geocoder = FakeGeocoder(
            {(54.73, -4.42): "Whithorn, Scotland, United Kingdom"}
        )

        original_grouper = worker_module.LocationGrouper

        class FakeGrouperFactory:
            def __init__(self, *a, **k):
                self._real = original_grouper(geocoder=fake_geocoder)

            def group(self, media_files):
                return self._real.group(media_files)

        worker_module.LocationGrouper = FakeGrouperFactory

        try:
            worker = LocationGroupingWorker(
                media_list=[whithorn_clip, no_gps_clip]
            )

            succeeded_calls = []
            failed_calls = []

            worker.succeeded.connect(
                lambda groups: succeeded_calls.append(groups)
            )
            worker.failed.connect(
                lambda message: failed_calls.append(message)
            )

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

            result_groups = succeeded_calls[0]

            if len(result_groups) != 2:
                raise RuntimeError(
                    f"Expected 2 groups (Whithorn + Unknown), got "
                    f"{len(result_groups)}."
                )

            if result_groups[0].place_name != (
                "Whithorn, Scotland, United Kingdom"
            ):
                raise RuntimeError(
                    f"Expected Whithorn first, got "
                    f"{result_groups[0].place_name!r}."
                )

            if not result_groups[1].is_unknown:
                raise RuntimeError(
                    "Expected the second group to be "
                    "UNKNOWN_LOCATION."
                )

            # --------------------------------------------------
            # Failure path.
            # --------------------------------------------------

            class ExplodingGrouperFactory:
                def __init__(self, *a, **k):
                    pass

                def group(self, media_files):
                    raise RuntimeError("Simulated grouping failure")

            worker_module.LocationGrouper = ExplodingGrouperFactory

            worker2 = LocationGroupingWorker(
                media_list=[whithorn_clip]
            )

            succeeded_calls2 = []
            failed_calls2 = []

            worker2.succeeded.connect(
                lambda groups: succeeded_calls2.append(groups)
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

            if "Simulated grouping failure" not in failed_calls2[0]:
                raise RuntimeError(
                    f"Expected the error message to be passed "
                    f"through, got {failed_calls2[0]!r}."
                )

        finally:
            worker_module.LocationGrouper = original_grouper

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

        if not hasattr(dock_manager, "locations_panel"):
            raise RuntimeError(
                "DockManager did not create a locations_panel."
            )

        dock_manager.locations_panel.set_groups(groups)

        dock_manager.refresh(workspace)

        if dock_manager.locations_panel.location_list.count() != 1 or (
            "No locations generated yet"
            not in dock_manager.locations_panel.location_list.item(
                0
            ).text()
        ):
            raise RuntimeError(
                "DockManager.refresh() should clear the Locations "
                "panel (matching the other panels' behaviour on "
                "project switch), but stale data remained."
            )