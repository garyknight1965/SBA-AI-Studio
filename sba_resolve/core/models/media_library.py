"""
============================================================
SBA AI Studio
Media Library
Version : 1.0.0
Sprint : ML-008
============================================================

Central media collection.

The MediaLibrary is the single source of truth for every
MediaFile imported into SBA AI Studio.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from sba_resolve.core.models.media_file import MediaFile


class MediaLibrary:
    """
    Central collection of MediaFile objects.

    Maintains indexes for extremely fast lookups.
    """

    def __init__(self) -> None:

        self._media: list[MediaFile] = []

        self._by_path: dict[Path, MediaFile] = {}

        self._by_filename: defaultdict[str, list[MediaFile]] = defaultdict(list)

        self._by_extension: defaultdict[str, list[MediaFile]] = defaultdict(list)

        self._by_camera: defaultdict[str, list[MediaFile]] = defaultdict(list)

        self._by_category: defaultdict[str, list[MediaFile]] = defaultdict(list)

    # -----------------------------------------------------
    # Core
    # -----------------------------------------------------

    def add(self, media: MediaFile) -> None:

        if media.full_path in self._by_path:
            return

        self._media.append(media)

        self._by_path[media.full_path] = media

        self._by_filename[media.filename].append(media)

        self._by_extension[media.extension.lower()].append(media)

        self._by_camera[media.camera_display_name].append(media)

        self._by_category[media.category].append(media)

    def add_many(
        self,
        media_files: Iterable[MediaFile],
    ) -> None:

        for media in media_files:
            self.add(media)

    def remove(
        self,
        media: MediaFile,
    ) -> bool:

        if media.full_path not in self._by_path:
            return False

        self._media.remove(media)

        del self._by_path[media.full_path]

        self._by_filename[media.filename].remove(media)

        self._by_extension[media.extension.lower()].remove(media)

        self._by_camera[media.camera_display_name].remove(media)

        self._by_category[media.category].remove(media)

        return True

    def clear(self) -> None:

        self._media.clear()

        self._by_path.clear()

        self._by_filename.clear()

        self._by_extension.clear()

        self._by_camera.clear()

        self._by_category.clear()

    # -----------------------------------------------------
    # Queries
    # -----------------------------------------------------

    def find_by_path(
        self,
        path: str | Path,
    ) -> MediaFile | None:

        return self._by_path.get(Path(path))

    def by_camera(
        self,
        camera: str,
    ) -> list[MediaFile]:

        return list(self._by_camera.get(camera, []))

    def by_extension(
        self,
        extension: str,
    ) -> list[MediaFile]:

        return list(
            self._by_extension.get(
                extension.lower(),
                [],
            )
        )

    def by_category(
        self,
        category: str,
    ) -> list[MediaFile]:

        return list(
            self._by_category.get(
                category,
                [],
            )
        )

    def by_filename(
        self,
        filename: str,
    ) -> list[MediaFile]:

        return list(
            self._by_filename.get(
                filename,
                [],
            )
        )

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------

    @property
    def total_files(self) -> int:
        return len(self._media)

    @property
    def total_size(self) -> int:
        return sum(m.size for m in self._media)

    @property
    def video_files(self) -> list[MediaFile]:
        return [m for m in self._media if m.is_video]

    @property
    def image_files(self) -> list[MediaFile]:
        return [m for m in self._media if m.is_image]

    @property
    def audio_files(self) -> list[MediaFile]:
        return [m for m in self._media if m.is_audio]

    @property
    def favorites(self) -> list[MediaFile]:
        return [m for m in self._media if m.favorite]

    @property
    def rejected(self) -> list[MediaFile]:
        return [m for m in self._media if m.rejected]

    @property
    def cameras(self) -> list[str]:
        return sorted(self._by_camera.keys())

    @property
    def categories(self) -> list[str]:
        return sorted(self._by_category.keys())

    # -----------------------------------------------------
    # Iteration
    # -----------------------------------------------------

    def __len__(self) -> int:
        return len(self._media)

    def __iter__(self):
        return iter(self._media)

    def __getitem__(
        self,
        index: int,
    ) -> MediaFile:
        return self._media[index]

    # -----------------------------------------------------

    def sort_by_capture_time(self) -> None:

        self._media.sort(
            key=lambda m: (
                m.created is None,
                m.created,
                m.filename.lower(),
            )
        )

    def sort_by_filename(self) -> None:

        self._media.sort(
            key=lambda m: m.filename.lower()
        )

    def sort_by_path(self) -> None:

        self._media.sort(
            key=lambda m: str(m.relative_path).lower()
        )

    # -----------------------------------------------------

    def summary(self) -> dict:

        return {
            "files": self.total_files,
            "videos": len(self.video_files),
            "images": len(self.image_files),
            "audio": len(self.audio_files),
            "favorites": len(self.favorites),
            "rejected": len(self.rejected),
            "cameras": len(self.cameras),
            "categories": len(self.categories),
            "size": self.total_size,
        }