"""
============================================================
SBA AI Studio
Source Media Validator
ML-014-002
Version : 1.0.0 Alpha
============================================================

Only original camera footage should enter the Planning Engine.

This service inspects already-scanned files (ProjectScanner
output) and splits them into:

    - accepted: original camera footage, recognised by a known
      filename pattern
    - rejected: everything else, each with a human-readable
      reason (image, sidecar file, audio, cache/proxy leftover,
      or a video file that doesn't match any known
      original-camera naming convention - most likely a
      rendered/exported file rather than raw footage)

This is a filename/extension-only decision - it runs on the
raw scan results, BEFORE ExifTool metadata is read, so rejected
files never cost a metadata read.

Filename patterns implemented:

    GoPro     : GX*.MP4 / GH*.MP4
    Insta360  : VID_YYYYMMDD_HHMMSS_....MP4 (Insta360 Studio
                export naming)
    DJI       : dji_fly_YYYYMMDD_HHMMSS_seq_epochms_video_beautify.mp4
                (confirmed DJI Fly app export naming - this is
                the only copy of this footage, so it's treated
                as original camera footage). The matching
                _video_cache variant is the app's own internal
                preview/scratch file and is always rejected.
                DJI_####.MP4 (a plain SD-card-style naming) is
                also accepted as a secondary pattern, though
                unconfirmed against real footage.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from sba_resolve.core.models.media_validation_report import (
    MediaValidationReport,
    RejectedMedia,
)

# Extensions that are never original camera footage, with the
# reason reported for each.
REJECTED_EXTENSIONS: dict[str, str] = {
    ".jpg": "Image file, not video footage",
    ".jpeg": "Image file, not video footage",
    ".png": "Image file, not video footage",
    ".heic": "Image file, not video footage",
    ".thm": "GoPro thumbnail sidecar file",
    ".xml": "Sidecar/metadata file",
    ".cube": "LUT file",
    ".mp3": "Audio-only file",
    ".wav": "Audio-only file",
    ".m4a": "Audio-only file",
    ".aac": "Audio-only file",
    ".flac": "Audio-only file",
}

# Folder name fragments that mean "not original footage",
# checked against the file's relative path. ProjectScanner
# already skips CacheClip/Proxy/Optimized Media entirely, so
# these mostly guard against files reaching this validator by
# some other route.
REJECTED_FOLDER_KEYWORDS: tuple[str, ...] = (
    "cacheclip",
    "proxy",
    "optimized media",
    "$recycle.bin",
    "recycle.bin",
    "trash",
)


class SourceMediaValidator:
    """
    Splits scanned files into accepted (original camera
    footage) and rejected (everything else), with a reason for
    every rejection.
    """

    _GOPRO_PATTERN = re.compile(r"^(GX|GH)\d+\.MP4$", re.IGNORECASE)

    _INSTA360_PATTERN = re.compile(
        r"^VID_\d{8}_\d{6}.*\.MP4$", re.IGNORECASE
    )

    # Original DJI camera naming convention (e.g. straight off an
    # SD card). Unconfirmed against real footage - kept as a
    # secondary pattern in case some DJI source uses it.
    _DJI_PATTERN = re.compile(r"^DJI_\d+\.MP4$", re.IGNORECASE)

    # DJI Fly app export naming, confirmed against real DJI Flip
    # footage: dji_fly_YYYYMMDD_HHMMSS_seq_epochms_video_beautify.mp4
    # This is Gary's only copy of this footage (no separate raw
    # original), so it's treated as original camera footage.
    _DJI_FLY_PATTERN = re.compile(
        r"^dji_fly_\d{8}_\d{6}_\d+_\d+_video_beautify\.mp4$",
        re.IGNORECASE,
    )

    # DJI Fly app's own internal preview/scratch file for the same
    # recording - never the file Gary wants on the timeline.
    _DJI_FLY_CACHE_PATTERN = re.compile(
        r"^dji_fly_.*_video_cache\.mp4$", re.IGNORECASE
    )

    def validate(self, media_files: Iterable) -> MediaValidationReport:

        report = MediaValidationReport()

        for media in media_files:

            reason = self._reject_reason(media)

            if reason is None:
                report.accepted.append(media)
                continue

            report.rejected.append(
                RejectedMedia(
                    full_path=getattr(
                        media, "full_path", Path(media.filename)
                    ),
                    filename=media.filename,
                    reason=reason,
                )
            )

        return report

    def _reject_reason(self, media) -> str | None:
        """
        Return None if `media` is accepted, otherwise a
        human-readable rejection reason.
        """

        filename = media.filename

        extension = (
            getattr(media, "extension", "")
            or Path(filename).suffix
        ).lower()

        relative_path = (
            str(getattr(media, "relative_path", ""))
            .replace("\\", "/")
            .lower()
        )

        for keyword in REJECTED_FOLDER_KEYWORDS:
            if keyword in relative_path:
                return f"Located in a '{keyword}' folder"

        if filename.lower().startswith(".trashed-"):
            return (
                "Soft-deleted file (.trashed- prefix, likely a "
                "cloud-sync or file-manager trash marker)"
            )

        if extension in REJECTED_EXTENSIONS:
            return REJECTED_EXTENSIONS[extension]

        if self._DJI_FLY_CACHE_PATTERN.match(filename):
            return (
                "DJI Fly app cache/preview file, not final "
                "footage"
            )

        if extension != ".mp4":
            # Only .mp4 original-camera patterns are recognised
            # today. Other video containers (.mov, .mxf, .avi)
            # aren't yet an accepted original-camera format for
            # this camera set - reject rather than silently
            # guess.
            return (
                f"Unrecognised video container '{extension}', "
                f"not a known original-camera format"
            )

        if self._GOPRO_PATTERN.match(filename):
            return None

        if self._INSTA360_PATTERN.match(filename):
            return None

        if self._DJI_PATTERN.match(filename):
            return None

        if self._DJI_FLY_PATTERN.match(filename):
            return None

        return (
            "Filename doesn't match a known original-camera "
            "pattern (GoPro GX/GH, DJI, or Insta360 VID_ "
            "export) - likely a rendered or exported file"
        )
