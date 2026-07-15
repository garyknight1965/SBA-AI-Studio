"""
============================================================
SBA AI Studio
Media Import Pipeline
Version : 2.0.0
Sprint : ML-014
============================================================

Orchestrates the complete media import workflow.

Pipeline

ProjectScanner
        ↓
SourceMediaValidator
        ↓
ExifToolEngine (accepted files only)
        ↓
MetadataNormalizer
        ↓
MetadataMapper
        ↓
MediaFile[]

Version 2.0.0 (ML-014) inserts Source Media Validation
between scanning and metadata reading. Only original camera
footage (recognised by filename pattern - GoPro GX/GH,
Insta360 VID_ export, DJI) reaches ExifTool; everything else
(images, sidecar files, cache/proxy leftovers, rendered
exports) is rejected up front, with a reason recorded in
`last_validation_report`, and never costs a metadata read.
"""

from __future__ import annotations

from pathlib import Path

from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine
from sba_resolve.core.metadata.metadata_mapper import MetadataMapper
from sba_resolve.core.metadata.metadata_normalizer import MetadataNormalizer
from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.models.media_validation_report import (
    MediaValidationReport,
)
from sba_resolve.core.project_scanner import ProjectScanner
from sba_resolve.core.services.insta360_view_assigner import (
    Insta360ViewAssigner,
)
from sba_resolve.core.services.source_media_validator import (
    SourceMediaValidator,
)


class MediaImportPipeline:
    """
    High-level media ingestion pipeline.

    This class coordinates the complete import process but
    contains no business logic itself.
    """

    def __init__(self, exiftool_path: str | None = None):

        self.scanner = None

        self.exif = ExifToolEngine(exiftool_path)

        self.validator = SourceMediaValidator()

        self.view_assigner = Insta360ViewAssigner()

        # Populated by the most recent import_folder() call, so
        # callers (CLI, GUI) can print or inspect what was
        # rejected and why.
        self.last_validation_report: MediaValidationReport | None = (
            None
        )

    def import_folder(
        self,
        folder: str | Path,
        progress=None,
    ) -> list[MediaFile]:

        project_root = Path(folder)

        self.scanner = ProjectScanner(project_root)

        # --------------------------------------------------
        # Step 1
        # Scan media
        # --------------------------------------------------

        scanned = self.scanner.scan(progress)

        if not scanned:
            return []

        # --------------------------------------------------
        # Step 2
        # Validate source media
        # --------------------------------------------------

        self.last_validation_report = self.validator.validate(scanned)

        accepted = self.last_validation_report.accepted

        if not accepted:
            return []

        # --------------------------------------------------
        # Step 3
        # Read metadata (accepted files only)
        # --------------------------------------------------

        metadata = self.exif.read(
            [m.full_path for m in accepted]
        )

        # --------------------------------------------------
        # Step 4
        # Normalize
        # --------------------------------------------------

        metadata = MetadataNormalizer.normalize(
            metadata
        )

        # --------------------------------------------------
        # Step 5
        # Map
        # --------------------------------------------------

        media = MetadataMapper.map_many(
            metadata,
            project_root,
        )

        # --------------------------------------------------
        # Step 6
        # Distinguish paired same-moment Insta360 views (e.g.
        # dual-lens exports) so they get separate tracks
        # instead of colliding.
        # --------------------------------------------------

        self.view_assigner.assign(media)

        return media

    @property
    def statistics(self):

        if self.scanner is None:
            return None

        return self.scanner.statistics