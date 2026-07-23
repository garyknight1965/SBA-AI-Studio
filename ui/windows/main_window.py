from __future__ import annotations

import contextlib
import io
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from controllers.workspace_controller import WorkspaceController
from sba_resolve.core.models.workspace import Workspace
from sba_resolve.core.services.app_settings import (
    load_gap_compression_settings,
    load_openrouteservice_api_key,
    load_theme,
)
from sba_resolve.core.services.day_detector import DayDetector
from sba_resolve.core.services.chapter_title_card_inserter import (
    NoChaptersFoundError,
    NoTemplateError,
    insert_chapter_title_cards,
)
from sba_resolve.core.services.cut_list_exporter import (
    DEFAULT_HANDLE_SECONDS,
    build_cut_list,
    format_cut_list,
)
from sba_resolve.core.services.resolve_transcript_parser import (
    ResolveTranscriptParser,
)
from sba_resolve.resolve_graphic_inserter import (
    AssetNotFoundError,
    GraphicPlacementError,
    ResolveConnectionError,
)
from ui.layout.dock_manager import DockManager
from ui.theme import apply_theme
from ui.widgets.map_widget import MapWidget
from ui.windows.settings_dialog import SettingsDialog
from ui.workers.intelliscript_worker import IntelliScriptWorker
from ui.workers.location_grouping_worker import LocationGroupingWorker
from ui.workers.route_worker import RouteWorker
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

    GUI-011 (2026-07-19) applies a real dark theme at startup
    (see ui/theme.py) - "theme" existed in config/settings.json
    before this but was never actually read anywhere.

    GUI-012 (2026-07-19) replaces the previously-empty central
    widget with a real interactive map (see ui/widgets/map_widget.py)
    - pins per clip GPS location plus a route line from
    GpxGpsLoader's full trackpoint data. Refreshed whenever the
    workspace refreshes (open project, after scan).

    ML-053 PARTIAL REVERT (2026-07-19): Gary asked to split
    "Scan && Import to Resolve" back into two separate File menu
    actions - he wasn't sure about the combined flow.
    scan_and_import_project() still exists below (unused by the
    menu now) in case it's ever wanted again.

    Groq provider backlog item: both YouTubeMetadataWorker and
    IntelliScriptWorker no longer take a "model" argument - they
    (and the generators they call) now default to get_ai_provider(),
    which reads the AI Provider choice (Ollama or Groq) straight
    from Settings itself. load_ollama_model() is no longer imported
    here since nothing in this file needs it anymore.
    """

    def __init__(self):
        super().__init__()

        # GUI-011: apply the theme before building any widgets,
        # so everything (including the dock panels built below)
        # picks up the stylesheet from its first paint - avoids
        # a visible flash of unstyled content.
        apply_theme(load_theme())

        self.workspace = Workspace("Untitled", Path.cwd())
        self.controller = WorkspaceController(self.workspace)

        self.setWindowTitle("SBA AI Studio")
        self.resize(1800, 1000)

        self._build_menu()
        self._build_toolbar()

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        # GUI-012: real map instead of an empty central QLabel.
        self.map_widget = MapWidget()
        self.setCentralWidget(self.map_widget)

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
        self._route_worker = None

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

        # GUI-012: push whatever's already in the (initially
        # empty) workspace to the map on startup, so it's in a
        # consistent state from the first frame.
        self.map_widget.set_media(self.workspace.media)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Open Project...", self.open_project)
        # ML-053 PARTIAL REVERT (2026-07-19): back to two separate
        # actions - Gary wasn't sure about the combined
        # "Scan && Import to Resolve" flow.
        file_menu.addAction("Scan Project", self.scan_project)
        file_menu.addAction("Import to Resolve", self.import_to_resolve)
        file_menu.addSeparator()
        file_menu.addAction(
            "Generate YouTube Metadata", self.generate_youtube_metadata
        )
        # ML-055: chapter title cards, built from whatever chapter
        # lines are currently in the YouTube Metadata description
        # field -- deliberately separate from "Generate YouTube
        # Metadata" above, since Gary may edit that text by hand
        # before placing the cards, and this should only ever act on
        # exactly what's on screen, never regenerate it.
        file_menu.addAction(
            "Add Chapter Title Cards to Timeline",
            self.add_chapter_title_cards,
        )
        file_menu.addSeparator()
        # ML-053: combined per Gary's UI simplification request -
        # was two separate menu items (Load Transcript..., then
        # Generate IntelliScript). Save stays a separate, explicit
        # action - Gary specifically wants no silent auto-save.
        # (Not reverted - Gary only asked about Scan & Import.)
        file_menu.addAction(
            "Load Transcript && Generate IntelliScript...",
            self.load_transcript_and_generate_intelliscript,
        )
        file_menu.addAction(
            "Save IntelliScript Script...", self.save_intelliscript_script
        )
        # Fix for Gary's real complaint (2026-07-20): manually cutting
        # using IntelliScript's exact segment timecodes was clipping
        # word start/ends, since those timecodes are Resolve's own
        # transcript-export boundaries with zero padding. This exports
        # a handle-adjusted (+/- 0.4s) cut list instead, as a separate
        # plain-text reference - deliberately not the same action as
        # Save IntelliScript Script, since that's the read-aloud script
        # text and this is cutting timecodes.
        file_menu.addAction(
            "Export Cut List...", self.export_cut_list
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
        Cancel leaves the file untouched.

        GUI-011: if the theme was changed, SettingsDialog calls
        apply_theme() itself before returning, so the change is
        visible immediately without restarting the app - nothing
        extra needed here.
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

        # GUI-012: a newly opened (as-yet-unscanned) project has
        # no media yet - clear the map rather than showing the
        # previous project's pins/route.
        self.map_widget.set_media(self.workspace.media)

        self.statusBar().showMessage(
            f"Project: {self.workspace.project_name}"
        )

    def scan_project(self):
        self._run_scan()

    def _run_scan(self) -> bool:
        """
        Does the actual scan work; returns True on success, False
        on failure (error dialog already shown). Extracted from
        scan_project() so scan_and_import_project() (ML-053, no
        longer wired to the menu as of 2026-07-19 - see class
        docstring) can chain into import_to_resolve() only if
        scanning actually succeeded, without importing on top of
        a failed/stale scan.
        """
        try:
            count = self.controller.scan_project()

            self.docks.refresh(self.workspace)

            # GUI-012: refresh the map with the newly scanned
            # media's GPS pins/route.
            self.map_widget.set_media(self.workspace.media)

            # Real road-following route (2026-07-21): the straight
            # pin-to-pin line above is drawn immediately and stays
            # as the fallback; this replaces it with a real route
            # once/if the background fetch succeeds.
            self._maybe_fetch_route()

            self.statusBar().showMessage(
                f"Scan complete: {count} files"
            )

            return True

        except Exception as exc:
            QMessageBox.critical(self, "Scan Error", str(exc))
            return False

    def scan_and_import_project(self):
        """
        ML-053: combined Scan + Import to Resolve. No longer
        wired to the File menu as of 2026-07-19 (Gary asked to
        revert to two separate buttons - he wasn't sure about the
        combined flow) - kept here, still fully working, in case
        it's wanted again later.
        """

        if not self._run_scan():
            return

        self.import_to_resolve()

    def _maybe_fetch_route(self) -> None:
        """
        Real road-following route (2026-07-21). Only attempts a
        fetch if an OpenRouteService API key is actually configured
        - with none set, this does nothing at all (no wasted network
        call, no spurious failure message), and the map's straight
        pin-to-pin line (already drawn by set_media()) stays as-is.

        Needs at least 2 GPS-located clips to form a route - same
        extraction/sort logic as MapWidget._push_update(), kept
        separate here since MapWidget's own responsibility is
        drawing, not deciding whether/what to fetch.
        """

        api_key = load_openrouteservice_api_key()
        if not api_key:
            return

        media_list = sorted(
            getattr(self.workspace, "media", []) or [],
            key=lambda m: getattr(m, "created", None) or datetime.min,
        )

        waypoints = [
            (m.gps_latitude, m.gps_longitude)
            for m in media_list
            if getattr(m, "gps_latitude", None) is not None
            and getattr(m, "gps_longitude", None) is not None
        ]

        if len(waypoints) < 2:
            return

        if self._route_worker is not None and (
            self._route_worker.isRunning()
        ):
            return

        self.statusBar().showMessage(
            "Fetching road-following route..."
        )

        self._route_worker = RouteWorker(
            waypoints=waypoints, api_key=api_key
        )
        self._route_worker.succeeded.connect(self._on_route_succeeded)
        self._route_worker.failed.connect(self._on_route_failed)
        self._route_worker.start()

    def _on_route_succeeded(self, route_points: list) -> None:
        self.map_widget.set_route(route_points)
        self.statusBar().showMessage("Road-following route loaded.")

    def _on_route_failed(self, message: str) -> None:
        # Deliberately NOT a popup - the straight-line fallback is
        # already showing correctly, this is a "nice to have didn't
        # work" case, not an error blocking anything the person
        # asked to do.
        self.statusBar().showMessage(
            f"Road-following route unavailable: {message}"
        )

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
        """
        GUI polish fix (2026-07-21): ResolveConnector.run() (and
        everything it calls - create_project, MediaPoolManager,
        create_timeline) prints a large amount of genuinely useful
        status detail to the console only - project/bin/media
        counts, ride day + placement statistics, dropped/skipped
        clip names and reasons, the "Manual Sync Required" per-
        camera report (ML-054), marker placement counts, and any
        warnings/errors. Running from source this was visible in a
        terminal; running the packaged .exe (no attached console
        window) it was invisible entirely.

        Fix: redirect stdout to a buffer for the whole try block
        (starting before connector.run(), so a mid-run exception
        still has whatever was printed up to that point available),
        then attach the full captured text via QMessageBox's native
        setDetailedText() "Show Details..." expander on every path -
        success, partial (corrupted files skipped), and failure.
        Nothing about the actual import logic changes; this is
        purely making already-existing status text visible in the
        GUI instead of only a terminal.
        """
        console_output = io.StringIO()
        try:
            if not getattr(self.workspace, "media", None):
                QMessageBox.information(
                    self,
                    "Nothing to import",
                    "Scan the project before importing to Resolve.",
                )
                return

            all_media = list(self.workspace.media)

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
                "timeline_name": self.workspace.project_name,
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
            with contextlib.redirect_stdout(console_output):
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

                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Imported (with skipped files)")
                msg_box.setText(
                    "Project imported into DaVinci Resolve.\n\n"
                    f"{len(corrupted_media)} corrupted file(s) were "
                    "skipped and never sent to Resolve:\n"
                    f"{skipped_lines}"
                )
                msg_box.setDetailedText(console_output.getvalue())
                msg_box.exec()
            else:
                self.statusBar().showMessage("Resolve import complete.")

                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Success")
                msg_box.setText("Project imported into DaVinci Resolve.")
                msg_box.setDetailedText(console_output.getvalue())
                msg_box.exec()

        except Exception as exc:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Resolve Import Error")
            msg_box.setText(str(exc))
            captured = console_output.getvalue()
            if captured:
                msg_box.setDetailedText(captured)
            msg_box.exec()

    def generate_youtube_metadata(self):
        """
        Runs YouTube metadata generation on a background thread
        (Planning Engine -> ride summary -> configured AI provider),
        so a slow model load or an unreachable backend doesn't
        freeze the GUI. This never touches Resolve at all - it
        works even with timeline creation disabled or Resolve not
        connected.

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

    def add_chapter_title_cards(self):
        """
        ML-055. Reads whatever is currently in the YouTube Metadata
        description field (NOT a fresh generation - exactly what's on
        screen, including any hand-edits Gary has made) and places one
        Fusion text title card per chapter onto the shared "AI Chapter
        Title Cards" track, via the confirmed-safe AppendToTimeline +
        ImportFusionComp mechanism (see resolve_graphic_inserter.py,
        GraphicInserter._insert_templated_text -- Candidate B,
        CONFIRMED 2026-07-20 on Gary's real Resolve setup).

        Deliberately separate from generate_youtube_metadata() above -
        this never regenerates the description, it only reads whatever
        text is already sitting in the panel right now.

        Runs synchronously (no worker thread) since this is a direct,
        short Resolve scripting call, not a slow model call - matching
        import_to_resolve()'s pattern, not generate_youtube_metadata()'s.

        Every failure path shows a clear message box rather than
        failing silently, per Gary's rules - a partially-placed batch
        (if a later chapter fails) is safe (additive-only, per
        resolve_graphic_inserter.py's design constraints) but should
        never be silent.
        """

        description_text = self.docks.youtube_panel.description_field.toPlainText()

        try:
            placed_names = insert_chapter_title_cards(description_text)
        except NoTemplateError as exc:
            QMessageBox.warning(self, "No Template Found", str(exc))
            return
        except NoChaptersFoundError as exc:
            QMessageBox.information(self, "No Chapters Found", str(exc))
            return
        except (ResolveConnectionError, AssetNotFoundError, GraphicPlacementError) as exc:
            QMessageBox.critical(self, "Chapter Title Cards Error", str(exc))
            return

        self.statusBar().showMessage(
            f"Placed {len(placed_names)} chapter title card(s) on "
            f"'AI Chapter Title Cards'."
        )
        QMessageBox.information(
            self,
            "Chapter Title Cards Placed",
            f"Placed {len(placed_names)} chapter title card(s):\n\n"
            + "\n".join(f"  - {name}" for name in placed_names),
        )

    def export_cut_list(self):
        """
        Fix for Gary's real complaint (2026-07-20): manually cutting
        using IntelliScript's exact segment timecodes was clipping
        word start/ends, since those timecodes are Resolve's own
        transcript-export boundaries, passed through completely
        unmodified with zero built-in handle/padding. See
        sba_resolve/core/services/cut_list_exporter.py.

        Re-parses the currently loaded transcript text (cheap,
        deterministic) rather than requiring IntelliScriptWorker's
        result shape to change - all_segments isn't otherwise kept on
        self. Requires a real fps from scanned media, since Resolve's
        HH:MM:SS:FF timecodes need a frame rate to convert to/from
        seconds accurately - refuses rather than guessing a default
        fps if none is available.
        """

        if not self._intelliscript_result or self._intelliscript_result.get(
            "parse_error"
        ):
            QMessageBox.information(
                self,
                "Nothing to export",
                "Generate an IntelliScript before exporting a cut list.",
            )
            return

        if not self._loaded_transcript_text:
            QMessageBox.information(
                self,
                "Nothing to export",
                "No transcript is currently loaded.",
            )
            return

        fps = next(
            (
                m.fps
                for m in getattr(self.workspace, "media", [])
                if getattr(m, "fps", 0.0)
            ),
            0.0,
        )
        if not fps:
            QMessageBox.warning(
                self,
                "No Frame Rate Found",
                "Could not find a frame rate from the scanned media - "
                "scan the project first so a real fps is available "
                "for accurate timecode math.",
            )
            return

        all_segments = ResolveTranscriptParser().parse(
            self._loaded_transcript_text
        )
        decisions = self._intelliscript_result.get("decisions", {})

        entries = build_cut_list(all_segments, decisions, fps)

        if not entries:
            QMessageBox.information(
                self,
                "Nothing to export",
                "No kept segments were found to build a cut list from.",
            )
            return

        text = format_cut_list(entries, DEFAULT_HANDLE_SECONDS)

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Cut List",
            "",
            "Text Files (*.txt);;All Files (*)",
        )

        if not path:
            return

        try:
            Path(path).write_text(text, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(
                self, "Could Not Save Cut List", str(exc)
            )
            return

        self.statusBar().showMessage(f"Cut list saved: {Path(path).name}")

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
        # new transcript's text with stale decisions from the one,
        # silently producing wrong chapter timing.
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
        Runs IntelliScriptEditor on a background thread (the
        configured AI provider decides keep/cut + paragraph
        grouping only; the exact original wording is reassembled
        deterministically - see IntelliScriptAssembler). Never
        touches Resolve.
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