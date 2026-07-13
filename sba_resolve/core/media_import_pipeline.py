"""
============================================================
SBA AI Studio
Media Import Pipeline
Version : 1.0.0
Sprint : ML-007
============================================================

Orchestrates the complete media import workflow.

Pipeline

ProjectScanner
        ↓
ExifToolEngine
        ↓
MetadataNormalizer
        ↓
MetadataMapper
        ↓
MediaFile[]
"""

from __future__ import annotations

from pathlib import Path

from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine
from sba_resolve.core.metadata.metadata_mapper import MetadataMapper
from sba_resolve.core.metadata.metadata_normalizer import MetadataNormalizer
from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.project_scanner import ProjectScanner


class MediaImportPipeline:
    """
    High-level media ingestion pipeline.

    This class coordinates the complete import process but
    contains no business logic itself.
    """

    def __init__(self, exiftool_path: str | None = None):

        self.scanner = None

        self.exif = ExifToolEngine(exiftool_path)

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
        # Read metadata
        # --------------------------------------------------

        metadata = self.exif.read(
            [m.full_path for m in scanned]
        )

        # --------------------------------------------------
        # Step 3
        # Normalize
        # --------------------------------------------------

        metadata = MetadataNormalizer.normalize(
            metadata
        )

        # --------------------------------------------------
        # Step 4
        # Map
        # --------------------------------------------------

        media = MetadataMapper.map_many(
            metadata,
            project_root,
        )

        return media

    @property
    def statistics(self):

        if self.scanner is None:
            return None

        return self.scanner.statistics