"""
============================================================
SBA AI Studio
Corruption Detector
Version : 1.1.0
Sprint  : ML-035
============================================================

Lightweight, dependency-free integrity check for scanned media.

This is NOT a full transcode/decode validation (that would need
ffmpeg/ffprobe). It catches the failure modes that actually show
up in real-world ride footage folders:

    - Zero-byte files (recording stopped before anything was
      written - camera freeze, full card, dead battery)
    - Files that can't be opened or read at all (I/O errors,
      permission issues, a dropped USB/network connection)
    - Files whose header doesn't match their extension (a
      truncated write, or a file that never finished copying
      off the SD card)
    - Files shorter on disk than their reported size (an
      interrupted copy)
    - ISO-BMFF (MP4/MOV/BRAW) files with a broken internal box
      structure - most importantly, a missing 'moov' box, which
      is what actually happens when a camera freezes or loses
      power mid-recording: the file often looks fine at a glance
      (valid 'ftyp' header, plausible size, readable end-to-end)
      but has no index for a player/Resolve to use at all. A
      header-only check would never catch this (ML-030 didn't) -
      this version walks the top-level box structure instead.

Still no full-file hashing, no decoding of actual video/audio
payload - only box headers are read for ISO-BMFF files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sba_resolve.core.models.corruption_report import (
    CorruptedMedia,
    CorruptionReport,
)
from sba_resolve.core.models.media_file import MediaFile

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_ISO_BMFF_EXTENSIONS = {".mp4", ".mov", ".braw"}


class CorruptionDetector:
    """
    Flags scanned media files that show signs of corruption or
    an incomplete write.
    """

    def scan(
        self,
        media_files: Iterable[MediaFile],
    ) -> CorruptionReport:

        report = CorruptionReport()

        for media in media_files:

            report.checked += 1

            reason = self._check(media)

            if reason:

                report.corrupted.append(
                    CorruptedMedia(
                        full_path=media.full_path,
                        relative_path=str(
                            media.relative_path
                        ).replace("\\", "/"),
                        filename=media.filename,
                        reason=reason,
                    )
                )

        return report

    # -----------------------------------------------------

    def _check(self, media: MediaFile) -> str | None:

        if media.size == 0:
            return "Zero-byte file"

        extension = media.extension.lower()

        try:

            if extension in _ISO_BMFF_EXTENSIONS:
                return self._check_iso_bmff(media.full_path, media.size)

            with open(media.full_path, "rb") as handle:

                header = handle.read(16)

                if not header:
                    return (
                        "File truncated (no readable header "
                        "despite non-zero reported size)"
                    )

                if extension in {".jpg", ".jpeg"}:

                    if not header.startswith(_JPEG_MAGIC):
                        return "Invalid JPEG header"

                elif extension == ".png":

                    if not header.startswith(_PNG_MAGIC):
                        return "Invalid PNG header"

                elif extension == ".wav":

                    if (
                        header[0:4] != b"RIFF"
                        or header[8:12] != b"WAVE"
                    ):
                        return "Invalid WAV header"

                # Confirm the file is still readable at the end
                # too - catches a card/drive that dropped out
                # mid-copy, leaving a file whose size on disk
                # doesn't match what was reported by the
                # filesystem when it was scanned.
                try:
                    handle.seek(max(media.size - 4, 0))
                    handle.read(4)
                except OSError:
                    return (
                        "File shorter than reported size - "
                        "likely an incomplete copy"
                    )

        except PermissionError as ex:
            return f"File unreadable (permission denied): {ex}"

        except OSError as ex:
            return f"File unreadable (I/O error): {ex}"

        return None

    # -----------------------------------------------------
    # ISO-BMFF (MP4 / MOV / BRAW) box-structure walk
    # -----------------------------------------------------

    def _check_iso_bmff(
        self, path: Path, file_size: int
    ) -> str | None:
        """
        Walks the top-level box structure without decoding any
        payload. Flags:

            - a box whose declared size is impossible (runs past
              the end of the file, or is smaller than a box
              header can be) - a truncated or overwritten box
            - no 'moov' box anywhere - the file has no index,
              the single most common real failure mode for
              footage cut off by a camera freeze or power loss
            - no 'mdat' box anywhere - no actual media data
        """

        found_moov = False
        found_mdat = False

        try:

            with open(path, "rb") as handle:

                offset = 0

                while offset < file_size:

                    handle.seek(offset)

                    header = handle.read(8)

                    if len(header) < 8:

                        if file_size - offset > 8:
                            return (
                                "Truncated box header at offset "
                                f"{offset} - possible incomplete "
                                "recording"
                            )

                        break

                    box_size = int.from_bytes(header[0:4], "big")
                    box_type = header[4:8]

                    header_len = 8

                    if box_size == 1:

                        # 64-bit "largesize" - real size is the
                        # next 8 bytes.
                        largesize = handle.read(8)

                        if len(largesize) < 8:
                            return (
                                "Truncated 64-bit box size at "
                                f"offset {offset}"
                            )

                        box_size = int.from_bytes(largesize, "big")
                        header_len = 16

                    elif box_size == 0:

                        # Valid per spec ONLY for the last box:
                        # box extends to end of file.
                        box_size = file_size - offset

                    if box_size < header_len or (
                        offset + box_size > file_size
                    ):
                        return (
                            "Invalid box size for "
                            f"'{box_type.decode('latin-1', 'replace')}' "
                            f"box at offset {offset} - possible "
                            "truncated or corrupted recording"
                        )

                    if box_type == b"moov":
                        found_moov = True
                    elif box_type == b"mdat":
                        found_mdat = True

                    offset += box_size

        except PermissionError as ex:
            return f"File unreadable (permission denied): {ex}"

        except OSError as ex:
            return f"File unreadable (I/O error): {ex}"

        if not found_moov:
            return (
                "No 'moov' box found - recording likely stopped "
                "before the index was written (camera freeze or "
                "power loss mid-recording)"
            )

        if not found_mdat:
            return "No 'mdat' box found - no media data in file"

        return None
