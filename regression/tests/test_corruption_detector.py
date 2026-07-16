"""
============================================================
SBA AI Studio
Corruption Detector Regression Test
ML-035
Version : 1.0.0
============================================================

Verifies CorruptionDetector catches the failure modes ML-030's
header-only check missed - most importantly a missing 'moov' box,
which is what a real GoPro clip looked like after a camera freeze
mid-recording (valid 'ftyp' header, plausible file size, readable
end-to-end, but no index at all - Resolve and every other player
refused to open it, while the ML-030 check reported it clean).
"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

from regression.base_test import BaseRegressionTest


def _box(box_type: bytes, payload: bytes = b"") -> bytes:
    size = 8 + len(payload)
    return struct.pack(">I", size) + box_type + payload


class CorruptionDetectorRegressionTest(BaseRegressionTest):

    name = "Corruption Detector (ML-035)"

    category = "Scanner"

    description = (
        "Verify the ISO-BMFF box walk catches missing moov/mdat "
        "and truncated boxes, and leaves genuinely valid files "
        "alone."
    )

    def run(self) -> None:

        from sba_resolve.core.models.media_file import MediaFile
        from sba_resolve.core.services.corruption_detector import (
            CorruptionDetector,
        )

        detector = CorruptionDetector()

        with tempfile.TemporaryDirectory() as tmp:

            tmp_path = Path(tmp)

            def make_media(name: str, data: bytes) -> MediaFile:

                path = tmp_path / name
                path.write_bytes(data)

                return MediaFile(
                    filename=name,
                    full_path=path,
                    relative_path=Path(name),
                    extension=".mp4",
                    size=path.stat().st_size,
                )

            # ----------------------------------------------
            # 1. A genuinely valid file (ftyp + moov + mdat) must
            #    NOT be flagged.
            # ----------------------------------------------

            valid_data = (
                _box(
                    b"ftyp",
                    b"isom" + b"\x00\x00\x02\x00" + b"isomiso2",
                )
                + _box(b"moov", b"\x00" * 20)
                + _box(b"mdat", b"\x00" * 100)
            )

            report = detector.scan([make_media("valid.mp4", valid_data)])

            if report.corrupted:
                raise RuntimeError(
                    f"A structurally valid MP4 was flagged as "
                    f"corrupted: {report.corrupted[0].reason!r}"
                )

            # ----------------------------------------------
            # 2. The real-world case: ftyp + mdat, NO moov - the
            #    camera-freeze failure mode. Must be flagged, and
            #    the reason must mention the missing moov box.
            # ----------------------------------------------

            no_moov_data = (
                _box(
                    b"ftyp",
                    b"isom" + b"\x00\x00\x02\x00" + b"isomiso2",
                )
                + _box(b"mdat", b"\x00" * 100)
            )

            report = detector.scan(
                [make_media("no_moov.mp4", no_moov_data)]
            )

            if not report.corrupted:
                raise RuntimeError(
                    "A file with no 'moov' box was NOT flagged as "
                    "corrupted - this is the exact real-world "
                    "camera-freeze failure mode this check exists "
                    "to catch."
                )

            if "moov" not in report.corrupted[0].reason:
                raise RuntimeError(
                    f"Expected the corruption reason to mention "
                    f"the missing moov box, got: "
                    f"{report.corrupted[0].reason!r}"
                )

            # ----------------------------------------------
            # 3. A box that declares a size larger than the file
            #    actually contains (truncated mid-write) must be
            #    flagged.
            # ----------------------------------------------

            ftyp = _box(
                b"ftyp", b"isom" + b"\x00\x00\x02\x00" + b"isomiso2"
            )

            # Declares 5000 bytes but only 50 actually follow.
            bad_mdat_header = struct.pack(">I", 5000) + b"mdat"

            truncated_data = ftyp + bad_mdat_header + (b"\x00" * 50)

            report = detector.scan(
                [make_media("truncated.mp4", truncated_data)]
            )

            if not report.corrupted:
                raise RuntimeError(
                    "A file with an impossible/truncated box size "
                    "was NOT flagged as corrupted."
                )

            # ----------------------------------------------
            # 4. Zero-byte file must still be flagged (ML-030
            #    behaviour, unchanged).
            # ----------------------------------------------

            report = detector.scan([make_media("empty.mp4", b"")])

            if not report.corrupted:
                raise RuntimeError(
                    "A zero-byte file was NOT flagged as corrupted."
                )

            if report.corrupted[0].reason != "Zero-byte file":
                raise RuntimeError(
                    f"Expected 'Zero-byte file', got "
                    f"{report.corrupted[0].reason!r}."
                )
