"""
SBA AI Studio
Project Scanner
Version 4.3.0
ML-006B

High-performance recursive scanner.

Uses os.scandir() for significantly faster directory traversal.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from sba_resolve.core.cancel_token import CancellationToken
from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.scanner_stats import ScannerStatistics


SUPPORTED_EXTENSIONS = {
    ".mp4", ".mov", ".mxf", ".avi",
    ".mp3", ".wav", ".m4a", ".aac", ".flac",
    ".jpg", ".jpeg", ".png", ".dng",
    ".tif", ".tiff", ".braw",
}

SKIP_FOLDERS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vs",
    "CacheClip",
    "Proxy",
    "Optimized Media",
}


class ProjectScanner:
    """
    High-performance recursive media scanner.
    """

    def __init__(self, root_folder: str | Path):

        self.root = Path(root_folder)

        self.statistics = ScannerStatistics()

        self.cancel_token = CancellationToken()

    def cancel(self) -> None:
        self.cancel_token.cancel()

    def scan(
        self,
        progress: Callable[[Path], None] | None = None,
    ) -> list[MediaFile]:

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        self.statistics.reset()
        self.cancel_token.reset()

        media: list[MediaFile] = []

        self._scan_directory(
            self.root,
            media,
            progress,
        )

        media.sort(
            key=lambda m: str(m.relative_path).lower()
        )

        return media

    def _scan_directory(
        self,
        folder: Path,
        media: list[MediaFile],
        progress: Callable[[Path], None] | None,
    ) -> None:

        if self.cancel_token.cancelled:
            return

        self.statistics.folders_scanned += 1

        try:

            with os.scandir(folder) as entries:

                for entry in entries:

                    if self.cancel_token.cancelled:
                        return

                    try:

                        if entry.is_symlink():
                            continue

                        if entry.is_dir(follow_symlinks=False):

                            if entry.name in SKIP_FOLDERS:
                                self.statistics.folders_skipped += 1
                                continue

                            self._scan_directory(
                                Path(entry.path),
                                media,
                                progress,
                            )

                            continue

                        self.statistics.files_scanned += 1

                        path = Path(entry.path)

                        extension = path.suffix.lower()

                        if extension not in SUPPORTED_EXTENSIONS:
                            self.statistics.files_skipped += 1
                            continue

                        if progress:
                            progress(path)

                        stat = entry.stat()

                        media.append(
                            MediaFile(
                                filename=path.name,
                                full_path=path,
                                relative_path=path.relative_to(self.root),
                                extension=extension,
                                size=stat.st_size,
                            )
                        )

                        self.statistics.media_found += 1

                    except Exception as ex:

                        self.statistics.errors.append(
                            f"{entry.path}: {ex}"
                        )

        except Exception as ex:

            self.statistics.errors.append(
                f"{folder}: {ex}"
            )