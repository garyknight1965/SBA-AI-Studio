from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from controllers.workspace_controller import WorkspaceController
from sba_resolve.core.models.workspace import Workspace
from sba_resolve.core.services.app_settings import (
    load_gap_compression_settings,
    load_ollama_model,
)
from sba_resolve.core.services.day_detector import DayDetector
from ui.layout.dock_manager import DockManager
from ui.workers.youtube_metadata_worker import YouTubeMetadataWorker
from sba_resolve.connector import ResolveConnector


class MainWindow(QMainWindow):
    """
    GUI-001 Integration v2

    DockManager is created ONCE.
    Opening a project refreshes the existing widgets instead
    of creating new docks.
    """

    def __init__(self):
        super().__init__()

        self.workspace = Workspace("Untitled", Path.cwd())
        self.controller = WorkspaceController(self.workspace)

        self.setWindowTitle("SBA AI Studio")
        self.resize(1800, 1000)

        self._build_menu()
        self._build_toolbar()

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self.setCentralWidget(QLabel("Timeline Preview", alignment=Qt.AlignCenter))

        self.docks = DockManager(self)
        self.docks.build(self.workspace)

        self.docks.youtube_panel.generate_requested.connect(
            self.generate_youtube_metadata
        )

        # Held here so the QThread isn't garbage-collected mid-run.
        self._youtube_worker = None

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Open Project...", self.open_project)
        file_menu.addAction("Scan Project", self.scan_project)
        file_menu.addAction("Import to Resolve", self.import_to_resolve)
        file_menu.addSeparator()
        file_menu.addAction(
            "Generate YouTube Metadata", self.generate_youtube_metadata
        )
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

    def _build_toolbar(self):
        self.addToolBar(QToolBar("Main"))

    def open_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project")
        if not folder:
            return

        self.workspace.project_root = Path(folder)
        self.workspace.project_name = Path(folder).name
        self.controller = WorkspaceController(self.workspace)

        # Refresh existing widgets instead of rebuilding docks
        self.docks.refresh(self.workspace)

        self.statusBar().showMessage(
            f"Project: {self.workspace.project_name}"
        )

    def scan_project(self):
        try:
            count = self.controller.scan_project()

            self.docks.refresh(self.workspace)

            self.statusBar().showMessage(
                f"Scan complete: {count} files"
            )

        except Exception as exc:
            QMessageBox.critical(self, "Scan Error", str(exc))

    def import_to_resolve(self):
        try:
            if not getattr(self.workspace, "media", None):
                QMessageBox.information(
                    self,
                    "Nothing to import",
                    "Scan the project before importing to Resolve.",
                )
                return

            media_list = list(self.workspace.media)

            # --------------------------------------------------
            # Determine which Ride Day each clip belongs to, so
            # bins can be organized as "Day N/Camera" instead of
            # one flat list of camera bins. This only needs
            # DayDetector's gap-based grouping - not the full
            # Planning Engine (Scene Detection, segments,
            # multicam, placement) - since bin naming only cares
            # about the day number.
            # --------------------------------------------------

            ride_days = DayDetector().detect(media_list)

            day_by_media_id: dict[int, int] = {}

            for ride_day in ride_days:
                for clip in ride_day.clips:
                    day_by_media_id[id(clip)] = ride_day.index

            def bin_path_for(media) -> str:
                day = day_by_media_id.get(id(media), 1)
                camera = (
                    getattr(media, "camera_display_name", None)
                    or getattr(media, "camera_model", None)
                    or "Unknown"
                )
                return f"Day {day}/{camera}"

            # Every distinct bin_path referenced by scanned media must be
            # requested here, or sync_bins() will create nothing and every
            # import will fail with "Media Pool folder not found".
            bin_paths_by_media = {
                id(m): bin_path_for(m) for m in media_list
            }

            bin_names = [
                path
                for _day, path in sorted(
                    {
                        (day_by_media_id.get(id(m), 1), bin_paths_by_media[id(m)])
                        for m in media_list
                    }
                )
            ]

            project_data = {
                "project_name": self.workspace.project_name,
                "bins": bin_names,
                "media": [
                    {
                        "file": str(m.full_path),
                        "bin_path": bin_paths_by_media[id(m)],
                    }
                    for m in media_list
                ],
                "media_objects": media_list,
                "timeline_name": f"{self.workspace.project_name} Master",
                "gap_compression": load_gap_compression_settings(),
            }

            self.statusBar().showMessage("Importing into Resolve...")

            connector = ResolveConnector(project_data)
            connector.run()

            self.statusBar().showMessage("Resolve import complete.")

            QMessageBox.information(
                self,
                "Success",
                "Project imported into DaVinci Resolve.",
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Resolve Import Error",
                str(exc),
            )

    def generate_youtube_metadata(self):
        """
        Runs YouTube metadata generation on a background thread
        (Planning Engine -> ride summary -> local Ollama model),
        so a slow model load or an unreachable Ollama instance
        doesn't freeze the GUI. This never touches Resolve at
        all - it works even with timeline creation disabled or
        Resolve not connected.
        """

        if (
            not getattr(self.workspace, "media", None)
            or self.workspace.is_empty
        ):
            QMessageBox.information(
                self,
                "Nothing to summarise",
                "Scan the project before generating YouTube metadata.",
            )
            return

        if self._youtube_worker is not None and (
            self._youtube_worker.isRunning()
        ):
            QMessageBox.information(
                self,
                "Already generating",
                "A YouTube metadata generation request is already "
                "in progress.",
            )
            return

        self.docks.youtube_panel.set_generating(True)
        self.statusBar().showMessage("Generating YouTube metadata...")

        self._youtube_worker = YouTubeMetadataWorker(
            media_list=list(self.workspace.media),
            project_name=self.workspace.project_name,
            model=load_ollama_model(),
        )
        self._youtube_worker.succeeded.connect(
            self._on_youtube_metadata_succeeded
        )
        self._youtube_worker.failed.connect(
            self._on_youtube_metadata_failed
        )
        self._youtube_worker.start()

    def _on_youtube_metadata_succeeded(self, metadata: dict):
        self.docks.youtube_panel.set_generating(False)
        self.docks.youtube_panel.set_metadata(metadata)

        if metadata.get("parse_error"):
            self.statusBar().showMessage(
                "YouTube metadata generated, but the model's "
                "response wasn't clean JSON - showing raw output."
            )
        else:
            self.statusBar().showMessage("YouTube metadata generated.")

    def _on_youtube_metadata_failed(self, message: str):
        self.docks.youtube_panel.set_generating(False)
        self.docks.youtube_panel.set_error(message)
        self.statusBar().showMessage("YouTube metadata generation failed.")
        QMessageBox.critical(self, "YouTube Metadata Error", message)


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
