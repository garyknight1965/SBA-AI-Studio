"""
Workspace Controller
Version 5.2.0
ML-022 GoPro Chapter Resequencing
"""

from __future__ import annotations
from pathlib import Path

from sba_resolve.core.models.media_validation_report import (
    MediaValidationReport,
)
from sba_resolve.core.models.workspace import Workspace
from sba_resolve.core.project_scanner import ProjectScanner
from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine
from sba_resolve.core.metadata.metadata_mapper import MetadataMapper
from sba_resolve.core.services.gopro_chapter_resequencer import (
    GoProChapterResequencer,
)
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

        # Populated by the most recent scan_project() call, so
        # callers (CLI, GUI) can inspect or display what was
        # rejected and why.
        self.last_validation_report: MediaValidationReport | None = (
            None
        )

        try:
            self.metadata = ExifToolEngine(exiftool_path) if exiftool_path else ExifToolEngine()
        except Exception:
            self.metadata = None

    def scan_project(self) -> int:
        self.scanner = ProjectScanner(self.workspace.project_root)

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

            print(f"[SBA] Mapper produced {len(media)} MediaFile objects")
            if media:
                m = media[0]
                print("[SBA] First media")
                print("  Camera :", m.camera_model)
                print("  Make   :", m.camera_make)
                print("  Size   :", m.width, "x", m.height)
                print("  FPS    :", m.fps)
                print("  Codec  :", m.codec)

        self.workspace.media.clear()
        self.workspace.media.add_many(media)
        self.workspace.touch()

        return self.workspace.total_files

    @property
    def library(self):
        return self.workspace.media
