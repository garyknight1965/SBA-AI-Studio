"""
Workspace Controller
Version 5.4.0
ML-030 Project Database & Corruption Detection
"""

from __future__ import annotations
from pathlib import Path

from sba_resolve.core.database.project_database import ProjectDatabase
from sba_resolve.core.models.media_validation_report import (
    MediaValidationReport,
)
from sba_resolve.core.models.corruption_report import CorruptionReport
from sba_resolve.core.models.scan_diff import ScanDiff
from sba_resolve.core.models.workspace import Workspace
from sba_resolve.core.project_scanner import ProjectScanner
from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine
from sba_resolve.core.metadata.metadata_mapper import MetadataMapper
from sba_resolve.core.services.corruption_detector import (
    CorruptionDetector,
)
from sba_resolve.core.services.gopro_chapter_resequencer import (
    GoProChapterResequencer,
)
from sba_resolve.core.services.gpx_gps_loader import GpxGpsLoader
from sba_resolve.core.services.insta360_view_assigner import (
    Insta360ViewAssigner,
)
from sba_resolve.core.services.source_media_validator import (
    SourceMediaValidator,
)


class WorkspaceController:

    def __init__(self, workspace: Workspace, exiftool_path: str | None = None):
        self.workspace = workspace
        self.scanner = ProjectScanner(workspace.project_root)
        self.validator = SourceMediaValidator()
        self.view_assigner = Insta360ViewAssigner()
        self.chapter_resequencer = GoProChapterResequencer()
        self.gpx_gps_loader = GpxGpsLoader()
        self.corruption_detector = CorruptionDetector()
        self.project_database = ProjectDatabase(workspace.project_root)

        # Populated by the most recent scan_project() call, so
        # callers (CLI, GUI) can inspect or display what was
        # rejected and why.
        self.last_validation_report: MediaValidationReport | None = (
            None
        )

        # Populated by the most recent scan_project() call - the
        # integrity results from the Corruption Detector and the
        # Project Database diff (new / missing / corrupted files
        # since the previous scan).
        self.last_corruption_report: CorruptionReport | None = None
        self.last_scan_diff: ScanDiff | None = None

        try:
            self.metadata = ExifToolEngine(exiftool_path) if exiftool_path else ExifToolEngine()
        except Exception:
            self.metadata = None

    def scan_project(self) -> int:
        self.scanner = ProjectScanner(self.workspace.project_root)
        self.project_database = ProjectDatabase(
            self.workspace.project_root
        )

        if self.metadata is None:
            media = self.scanner.scan()
            print("[SBA] ExifTool unavailable - scanner mode")
        else:
            # --------------------------------------------------
            # Scan, then validate BEFORE any metadata is read.
            # Previously this read the entire project folder with
            # ExifTool directly (read_folder), with no filtering -
            # images, GoPro .THM thumbnails, and any other
            # non-footage file ExifTool could parse were included
            # as "media" alongside real camera footage. Only
            # scanned, ACCEPTED files are now sent to ExifTool.
            # --------------------------------------------------

            scanned = self.scanner.scan()

            self.last_validation_report = self.validator.validate(
                scanned
            )

            self.last_validation_report.print_report()

            accepted_paths = [
                m.full_path for m in self.last_validation_report.accepted
            ]

            raw = self.metadata.read(accepted_paths) if accepted_paths else []

            print(f"[SBA] ExifTool returned {len(raw)} records")

            media = MetadataMapper.map_many(
                raw,
                Path(self.workspace.project_root),
            )

            # --------------------------------------------------
            # Distinguish paired same-moment Insta360 views (e.g.
            # dual-lens exports) so they get separate tracks
            # instead of colliding on the timeline.
            # --------------------------------------------------

            self.view_assigner.assign(media)

            # --------------------------------------------------
            # Correct multi-chapter GoPro recording timestamps.
            # GoPro embeds the SAME creation time into every
            # chapter of one continuous recording (e.g.
            # GH010145/GH020145/GH030145.MP4), so without this,
            # every chapter after the first collides on the exact
            # same timeline frame instead of playing back-to-back.
            # --------------------------------------------------

            self.chapter_resequencer.resequence(media)

            # --------------------------------------------------
            # Load GPS from sibling .gpx files (e.g.
            # GH010167.MP4 -> GH010167.gpx) for footage without
            # embedded GPS metadata - most GoPro clips don't
            # expose GPS as a simple EXIF tag, so a separate GPX
            # telemetry export is often the only source.
            # --------------------------------------------------

            gps_before = sum(
                1 for m in media if m.gps_latitude is not None
            )

            self.gpx_gps_loader.load(media)

            gps_after = sum(
                1 for m in media if m.gps_latitude is not None
            )

            if gps_after > gps_before:
                print(
                    f"[SBA] GPX GPS loaded for "
                    f"{gps_after - gps_before} clip(s)"
                )

            print(f"[SBA] Mapper produced {len(media)} MediaFile objects")
            if media:
                m = media[0]
                print("[SBA] First media")
                print("  Camera :", m.camera_model)
                print("  Make   :", m.camera_make)
                print("  Size   :", m.width, "x", m.height)
                print("  FPS    :", m.fps)
                print("  Codec  :", m.codec)

        # ------------------------------------------------------
        # Integrity check + Project Database (ML-030).
        #
        # Runs on whatever was scanned this pass (accepted media
        # when ExifTool is available, or the raw scan otherwise),
        # then diffs against the previous Project Database to
        # surface files that vanished or newly failed an
        # integrity check since the last scan of this project.
        # ------------------------------------------------------

        self.last_corruption_report = self.corruption_detector.scan(
            media
        )

        self.last_corruption_report.print_report()

        for corrupted in self.last_corruption_report.corrupted:
            for m in media:
                if m.full_path == corrupted.full_path:
                    m.corrupted = True
                    m.corruption_reason = corrupted.reason
                    break

        previous_records = self.project_database.load()

        current_records = self.project_database.build_records(
            media,
            self.last_corruption_report,
            previous_records,
        )

        self.last_scan_diff = self.project_database.diff(
            previous_records,
            current_records,
        )

        self.last_scan_diff.print_report()

        self.project_database.save(current_records)

        self.workspace.media.clear()
        self.workspace.media.add_many(media)
        self.workspace.touch()

        return self.workspace.total_files

    @property
    def library(self):
        return self.workspace.media
