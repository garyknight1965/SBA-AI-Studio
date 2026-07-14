"""
Workspace Controller
Version 4.3.2 Alpha
CORE-008 Diagnostic
"""

from __future__ import annotations
from pathlib import Path

from sba_resolve.core.models.workspace import Workspace
from sba_resolve.core.project_scanner import ProjectScanner
from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine
from sba_resolve.core.metadata.metadata_mapper import MetadataMapper


class WorkspaceController:

    def __init__(self, workspace: Workspace, exiftool_path: str | None = None):
        self.workspace = workspace
        self.scanner = ProjectScanner(workspace.project_root)

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
            raw = self.metadata.read_folder(self.workspace.project_root)
            print(f"[SBA] ExifTool returned {len(raw)} records")

            media = MetadataMapper.map_many(
                raw,
                Path(self.workspace.project_root),
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

        self.workspace.media.clear()
        self.workspace.media.add_many(media)
        self.workspace.touch()

        return self.workspace.total_files

    @property
    def library(self):
        return self.workspace.media
