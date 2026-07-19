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
from ui.windows.settings_dialog import SettingsDialog
from ui.workers.intelliscript_worker import IntelliScriptWorker
from ui.workers.location_grouping_worker import LocationGroupingWorker
from ui.workers.youtube_metadata_worker import YouTubeMetadataWorker
from sba_resolve.connector import ResolveConnector


class MainWindow(QMainWindow):
    """
    GUI-001 Integration v2

    DockManager is created ONCE.
    Opening a project refreshes the existing widgets instead
    of creating new docks.

    GUI-010 (2026-07-19) adds a Settings dialog (Edit menu ->
    Settings...) so config/settings.json's important toggles can
    be edited through the app instead of by hand.
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

        self.setCentralWidget(QLabel("", alignment=Qt.AlignCenter))

        self.docks = DockManager(self)
        self.docks.build(self.workspace)

        self.docks.youtube_panel.generate_requested.connect(
            self.generate_youtube_metadata
        )
        self.docks.transcript_panel.load_requested.connect(
            self.load_transcript
        )
        self.docks.transcript_panel.generate_requested.connect(
            self.generate_intelliscript
        )
        self.docks.transcript_panel.save_requested.connect(
            self.save_intelliscript_script
        )
        self.docks.locations_panel.generate_requested.connect(
            self.generate_locations
        )

        # Held here so the QThread isn't garbage-collected mid-run.
        self._youtube_worker = None
        self._intelliscript_worker = None
        self._location_worker = None

        # Set by load_transcript() once a file is chosen - the raw
        # text sent to IntelliScriptWorker on Generate.
        self._loaded_transcript_text: str | None = None

        # ML-052: set by _on_intelliscript_succeeded() once
        # IntelliScript generation finishes - the full result dict
        # (script/decisions/etc.), kept here (not just handed to
        # the transcript panel for display) so generate_youtube_metadata()
        # can later pass its "decisions" through to
        # YouTubeMetadataWorker for real edited-video chapter timing.
        self._intelliscript_result: dict | None = None

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Open Project...", self.open_project)
        # ML-053: combined per Gary's UI simplification request -
        # was two separate menu items (Scan Project, then Import to
        # Resolve). scan_and_import_project() runs both in sequence,
        # stopping before import if scanning fails. The individual
        # scan_project()/import_to_resolve() methods still exist
        # unchanged underneath, in case anything else calls them
        # directly.
        file_menu.addAction(
            "Scan && Import to Resolve", self.scan_and_import_project
        )
        file_menu.addSeparator()
        file_menu.addAction(
            "Generate YouTube Metadata", self.generate_youtube_metadata
        )
        file_menu.addSeparator()
        # ML-053: combined per Gary's UI simplification request -
        # was two separate menu items (Load Transcript..., then
        # Generate IntelliScript). Save stays a separate, explicit
        # action - Gary specifically wants no silent auto-save.
        file_menu.addAction(
            "Load Transcript && Generate IntelliScript...",
            self.load_transcript_and_generate_intelliscript,
        )
        file_menu.addAction(
            "Save IntelliScript Script...", self.save_intelliscript_script
        )
        file_menu.addSeparator()
        file_menu.addAction("Group by Location", self.generate_locations)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        # GUI-010: a real Settings dialog, so config/settings.json's
        # toggles don't need to be hand-edited.
        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction("Settings...", self.open_settings)

    def _build_toolbar(self):
        self.addToolBar(QToolBar("Main"))

    def open_settings(self):
        """
        GUI-010: opens the Settings dialog. Settings are written
        to config/settings.json immediately on OK (see
        SettingsDialog._on_accept / app_settings.save_settings) -
        Cancel leaves the file untouched. Nothing else needs to
        be refreshed here: every setting is re-read fresh from
        disk wherever it's used (load_gap_compression_settings(),
        etc. are all called at the point of use, never cached on
        MainWindow).
        """

        dialog = SettingsDialog(self)
        dialog.exec()

    def open_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project")
        if not folder:
            return

        self.workspace.project_root = Path(folder)
        self.workspace.project_name = Path(folder).name
        self.controller = WorkspaceController(self.workspace)

        # ML-052: a transcript (and any IntelliScript result
        # generated from it) belongs to the PREVIOUS project - carrying
        # it forward into a newly opened project would silently
        # apply the wrong project's transcript/chapters. Confirmed
        # this wasn't being cleared before; fixed here.
        self._loaded_transcript_text = None
        self._intelliscript_result = None
        self.docks.transcript_panel.set_loaded_file("")

        # Refresh existing widgets instead of rebuilding docks
        self.docks.refresh(self.workspace)

        self.statusBar().showMessage(
            f"Project: {self.workspace.project_name}"
        )

    def scan_project(self):
        self._run_scan()

    def _run_scan(self) -> bool:
        """
        Does the actual scan work; returns True on success, False
        on failure (error dialog already shown). Extracted from
        scan_project() so scan_and_import_project() (ML-053) can
        chain into import_to_resolve() only if scanning actually
        succeeded, without importing on top of a failed/stale scan.
        """
        try:
            count = self.controller.scan_project()

            self.docks.refresh(self.workspace)

            self.statusBar().showMessage(
                f"Scan complete: {count} files"
            )

            return True

        except Exception as exc:
            QMessageBox.critical(self, "Scan Error", str(exc))
            return False

    def scan_and_import_project(self):
        """
        ML-053: combined Scan + Import to Resolve, per Gary's UI
        simplification request. Only proceeds to import if scanning
        actually succeeded - importing on top of a failed scan would
        just import stale or empty media.
        """

        if not self._run_scan():
            return

        self.import_to_resolve()

    @staticmethod
    def _split_media_by_corruption(media_list):
        """
        Splits scanned media into (clean, corrupted), based on
        the `.corrupted` flag the Corruption Detector sets during
        WorkspaceController.scan_project() (ML-035).

        Pure and side-effect-free on purpose, so this can be
        regression-tested directly without touching Qt/QMessageBox
        or a real Resolve connection at all.
        """

        clean = [
            m for m in media_list if not getattr(m, "corrupted", False)
        ]
        corrupted = [
            m for m in media_list if getattr(m, "corrupted", False)
        ]

        return clean, corrupted

    def import_to_resolve(self):
        try:
            if not getattr(self.workspace, "media", None):
                QMessageBox.information(
                    self,
                    "Nothing to import",
                    "Scan the project before importing to Resolve.",
                )
                return

            all_media = list(self.workspace.media)

            # --------------------------------------------------
            # ML-036: never hand a file the Corruption Detector
            # already flagged (ML-035, set during scan_project())
            # to Resolve's own import. Resolve's ImportMedia API
            # returns nothing useful on failure - it would just
            # fail again here with no explanation, the way
            # GX010219.MP4 did before ML-035 existed. Skipping it
            # at this point means the editor finds out WHY a clip
            # is missing, in plain language, instead of a bare
            # "Errors: 1" in the Resolve report.
            # --------------------------------------------------

            media_list, corrupted_media = self._split_media_by_corruption(
                all_media
            )

            if not media_list:
                QMessageBox.warning(
                    self,
                    "Nothing to import",
                    "Every scanned file is flagged as corrupted - "
                    "there's nothing to send to Resolve. See the "
                    "Corruption Detector output from the last scan "
                    "for details on each file.",
                )
                return

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

            if corrupted_media:
                names = ", ".join(m.filename for m in corrupted_media)
                self.statusBar().showMessage(
                    f"Importing into Resolve - skipping "
                    f"{len(corrupted_media)} corrupted file(s): {names}"
                )
            else:
                self.statusBar().showMessage("Importing into Resolve...")

            connector = ResolveConnector(project_data)
            connector.run()

            if corrupted_media:
                skipped_lines = "\n".join(
                    f"  - {m.filename} ({m.corruption_reason})"
                    for m in corrupted_media
                )

                self.statusBar().showMessage(
                    f"Resolve import complete. Skipped "
                    f"{len(corrupted_media)} corrupted file(s)."
                )

                QMessageBox.information(
                    self,
                    "Imported (with skipped files)",
                    "Project imported into DaVinci Resolve.\n\n"
                    f"{len(corrupted_media)} corrupted file(s) were "
                    "skipped and never sent to Resolve:\n"
                    f"{skipped_lines}",
                )
            else:
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

        ML-052: also passes through the currently loaded transcript
        text and IntelliScript decisions (if both are available for
        this project), so YouTubeMetadataWorker can append a
        chapters section built from real edited-video timing rather
        than raw footage. If IntelliScript hasn't been generated yet
        for this project, no chapters section is added at all - the
        worker deliberately does not fall back to raw-footage
        timing, since that was confirmed wrong for real videos.
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

        intelliscript_decisions = None

        if self._intelliscript_result and not self._intelliscript_result.get(
            "parse_error"
        ):
            intelliscript_decisions = self._intelliscript_result.get(
                "decisions"
            )

        self._youtube_worker = YouTubeMetadataWorker(
            media_list=list(self.workspace.media),
            project_name=self.workspace.project_name,
            model=load_ollama_model(),
            extra_notes=self.docks.youtube_panel.additional_notes(),
            raw_transcript_text=self._loaded_transcript_text,
            intelliscript_decisions=intelliscript_decisions,
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

    def load_transcript(self):
        """
        Loads a DaVinci Resolve transcript export (plain .txt) from
        disk. Reading happens here, not in the worker, so a bad
        file path or encoding error surfaces immediately rather
        than only once Generate is clicked.
        """
        self._run_load_transcript()

    def _run_load_transcript(self) -> bool:
        """
        Does the actual file-dialog + read work; returns True if a
        transcript was successfully loaded, False if the dialog was
        cancelled or reading failed (error dialog already shown in
        the failure case). Extracted from load_transcript() so
        load_transcript_and_generate_intelliscript() (ML-053) can
        chain into generate_intelliscript() only when there's
        actually a transcript to generate from.
        """

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Transcript",
            "",
            "Text Files (*.txt);;All Files (*)",
        )

        if not path:
            return False

        try:
            self._loaded_transcript_text = Path(path).read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            QMessageBox.critical(
                self, "Could Not Read Transcript", str(exc)
            )
            return False

        # ML-052: a newly loaded transcript invalidates any
        # IntelliScript result generated from a DIFFERENT transcript
        # - otherwise generate_youtube_metadata() could pair this
        # new transcript's text with stale decisions from the old
        # one, silently producing wrong chapter timing.
        self._intelliscript_result = None

        self.docks.transcript_panel.set_loaded_file(Path(path).name)
        self.statusBar().showMessage(f"Transcript loaded: {Path(path).name}")

        return True

    def load_transcript_and_generate_intelliscript(self):
        """
        ML-053: combined Load Transcript + Generate IntelliScript,
        per Gary's UI simplification request. Only proceeds to
        generate if a transcript was actually loaded - cancelling
        the file dialog, or a read failure, should not attempt to
        generate from stale/missing transcript text.
        """

        if not self._run_load_transcript():
            return

        self.generate_intelliscript()

    def generate_intelliscript(self):
        """
        Runs IntelliScriptEditor on a background thread (Ollama
        decides keep/cut + paragraph grouping only; the exact
        original wording is reassembled deterministically - see
        IntelliScriptAssembler). Never touches Resolve.
        """

        if not self._loaded_transcript_text:
            QMessageBox.information(
                self,
                "Nothing to generate",
                "Load a transcript export before generating an "
                "IntelliScript.",
            )
            return

        if self._intelliscript_worker is not None and (
            self._intelliscript_worker.isRunning()
        ):
            QMessageBox.information(
                self,
                "Already generating",
                "An IntelliScript generation request is already "
                "in progress.",
            )
            return

        self.docks.transcript_panel.set_generating(True)
        self.statusBar().showMessage("Generating IntelliScript...")

        self._intelliscript_worker = IntelliScriptWorker(
            raw_transcript_text=self._loaded_transcript_text,
            model=load_ollama_model(),
        )
        self._intelliscript_worker.succeeded.connect(
            self._on_intelliscript_succeeded
        )
        self._intelliscript_worker.failed.connect(
            self._on_intelliscript_failed
        )
        self._intelliscript_worker.start()

    def _on_intelliscript_succeeded(self, result: dict):
        self.docks.transcript_panel.set_generating(False)
        self.docks.transcript_panel.set_result(result)

        # ML-052: kept here (not just handed to the transcript panel
        # for display) so generate_youtube_metadata() can later use
        # result["decisions"] for real edited-video chapter timing.
        self._intelliscript_result = result

        if result.get("parse_error"):
            self.statusBar().showMessage(
                "IntelliScript generation finished, but the "
                "model's response wasn't clean JSON - showing raw "
                "output."
            )
        else:
            self.statusBar().showMessage(
                f"IntelliScript generated - kept "
                f"{result.get('kept_count', 0)} of "
                f"{result.get('segment_count', 0)} segments."
            )

    def _on_intelliscript_failed(self, message: str):
        self.docks.transcript_panel.set_generating(False)
        self.docks.transcript_panel.set_error(message)
        self.statusBar().showMessage("IntelliScript generation failed.")
        QMessageBox.critical(self, "IntelliScript Error", message)

    def save_intelliscript_script(self):
        """
        Saves the CURRENT contents of the script editor (including
        any manual tweaks made after generation), not a cached
        copy from generation time.
        """

        script = self.docks.transcript_panel.current_script()

        if not script.strip():
            QMessageBox.information(
                self,
                "Nothing to save",
                "Generate an IntelliScript before saving.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save IntelliScript",
            "",
            "Text Files (*.txt);;All Files (*)",
        )

        if not path:
            return

        try:
            Path(path).write_text(script, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(
                self, "Could Not Save Script", str(exc)
            )
            return

        self.statusBar().showMessage(f"Script saved: {Path(path).name}")

    def generate_locations(self):
        """
        Runs LocationGrouper on a background thread
        (LocationGroupingWorker), since ReverseGeocoder makes real
        network calls. Never touches Resolve.
        """

        if (
            not getattr(self.workspace, "media", None)
            or self.workspace.is_empty
        ):
            QMessageBox.information(
                self,
                "Nothing to group",
                "Scan the project before grouping by location.",
            )
            return

        if self._location_worker is not None and (
            self._location_worker.isRunning()
        ):
            QMessageBox.information(
                self,
                "Already generating",
                "A location grouping request is already in "
                "progress.",
            )
            return

        self.docks.locations_panel.set_generating(True)
        self.statusBar().showMessage("Grouping by location...")

        self._location_worker = LocationGroupingWorker(
            media_list=list(self.workspace.media),
        )
        self._location_worker.succeeded.connect(
            self._on_locations_succeeded
        )
        self._location_worker.failed.connect(self._on_locations_failed)
        self._location_worker.start()

    def _on_locations_succeeded(self, groups: list):
        self.docks.locations_panel.set_generating(False)
        self.docks.locations_panel.set_groups(groups)
        self.statusBar().showMessage(
            f"Location grouping complete - {len(groups)} group(s)."
        )

    def _on_locations_failed(self, message: str):
        self.docks.locations_panel.set_generating(False)
        self.docks.locations_panel.set_error(message)
        self.statusBar().showMessage("Location grouping failed.")
        QMessageBox.critical(self, "Location Grouping Error", message)


if __name__ == "__main__":
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()