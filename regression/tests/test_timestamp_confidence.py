"""
============================================================
SBA AI Studio
Timestamp Confidence Regression Test
ML-031
Version : 1.0.0
============================================================

Verifies:
- TimestampResolver.resolve_with_source() reports the correct
  source name for each resolution path (metadata field, DJI
  filename, Insta360 filename, file-modified fallback) - this
  feeds ConfidenceEngine.score(), which was previously wired to
  nothing at all.
- MetadataMapper.map() actually populates
  MediaFile.timestamp_source/timestamp_confidence end to end,
  not just in the resolver alone.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest


class TimestampConfidenceRegressionTest(BaseRegressionTest):

    name = "Timestamp Confidence (ML-031)"

    category = "Metadata"

    description = (
        "Verify resolve_with_source() reports the correct "
        "source per resolution path, and that MetadataMapper "
        "actually wires timestamp confidence onto MediaFile."
    )

    def run(self) -> None:

        from sba_resolve.core.metadata.confidence_engine import (
            ConfidenceEngine,
        )
        from sba_resolve.core.metadata.timestamp_resolver import (
            TimestampResolver,
        )

        # --------------------------------------------------
        # 1. Metadata field resolution reports the field name.
        # --------------------------------------------------

        dt, source = TimestampResolver.resolve_with_source(
            {"CreateDate": "2026:07:01 09:00:00"}
        )

        if source != "CreateDate":
            raise RuntimeError(
                f"Expected source 'CreateDate', got {source!r}."
            )

        if dt != datetime(2026, 7, 1, 9, 0, 0):
            raise RuntimeError(f"Unexpected datetime: {dt!r}")

        # CreateDate takes priority per DATE_FIELDS order even
        # when other date fields are ALSO present.
        dt2, source2 = TimestampResolver.resolve_with_source(
            {
                "CreateDate": "2026:07:01 09:00:00",
                "MediaCreateDate": "2026:07:01 09:05:00",
                "DateTimeOriginal": "2026:07:01 09:10:00",
            }
        )

        if source2 != "CreateDate":
            raise RuntimeError(
                f"Expected CreateDate to win (first in "
                f"DATE_FIELDS), got {source2!r}."
            )

        # --------------------------------------------------
        # 2. DJI / Insta360 filename fallback reports the
        #    correct, specific source name.
        # --------------------------------------------------

        _, dji_source = TimestampResolver.resolve_with_source(
            {"SourceFile": "/fake/DJI_20250626_094438_0001.MP4"}
        )

        if dji_source != "DJI Filename":
            raise RuntimeError(
                f"Expected source 'DJI Filename', got {dji_source!r}."
            )

        _, insta_source = TimestampResolver.resolve_with_source(
            {"SourceFile": "/fake/VID_20250626_094438_001.mp4"}
        )

        if insta_source != "Insta360 Filename":
            raise RuntimeError(
                f"Expected source 'Insta360 Filename', got "
                f"{insta_source!r}."
            )

        # --------------------------------------------------
        # 3. File-modified-time fallback, for a real temp file
        #    with no metadata and an unparseable filename.
        # --------------------------------------------------

        with tempfile.TemporaryDirectory() as tmp:

            real_file = Path(tmp) / "unrecognised_name.mp4"
            real_file.write_bytes(b"\x00")

            _, file_source = TimestampResolver.resolve_with_source(
                {"SourceFile": str(real_file)}
            )

            if file_source != "FileModified":
                raise RuntimeError(
                    f"Expected source 'FileModified', got "
                    f"{file_source!r}."
                )

        # A nonexistent file with an unparseable name resolves
        # to nothing at all, not a crash.
        none_dt, none_source = TimestampResolver.resolve_with_source(
            {"SourceFile": "/fake/does_not_exist_at_all.mp4"}
        )

        if none_dt is not None or none_source is not None:
            raise RuntimeError(
                "Expected (None, None) for an unresolvable, "
                f"nonexistent file, got ({none_dt!r}, "
                f"{none_source!r})."
            )

        # --------------------------------------------------
        # 4. Confidence scores match expectations - metadata
        #    fields score highest, filename fallbacks lower,
        #    file-modified lowest.
        # --------------------------------------------------

        if ConfidenceEngine.score("CreateDate") <= ConfidenceEngine.score(
            "DJI Filename"
        ):
            raise RuntimeError(
                "A real metadata field should score higher than "
                "a filename-parsed fallback."
            )

        if ConfidenceEngine.score(
            "DJI Filename"
        ) <= ConfidenceEngine.score("FileModified"):
            raise RuntimeError(
                "A filename-parsed fallback should score higher "
                "than the file-modified-time fallback."
            )

        # --------------------------------------------------
        # 5. End to end: MetadataMapper actually populates
        #    MediaFile.timestamp_source/timestamp_confidence,
        #    not just the resolver in isolation.
        # --------------------------------------------------

        from sba_resolve.core.metadata.metadata_mapper import (
            MetadataMapper,
        )

        item = {
            "SourceFile": "/fake/project/GX010001.MP4",
            "CreateDate": "2026:07:01 09:00:00",
            "FileSize": 1024,
        }

        media = MetadataMapper.map(item, Path("/fake/project"))

        if media.timestamp_source != "CreateDate":
            raise RuntimeError(
                f"Expected MediaFile.timestamp_source "
                f"'CreateDate', got {media.timestamp_source!r} - "
                f"MetadataMapper may not be wired to "
                f"resolve_with_source()."
            )

        expected_confidence = ConfidenceEngine.score("CreateDate")

        if media.timestamp_confidence != expected_confidence:
            raise RuntimeError(
                f"Expected MediaFile.timestamp_confidence "
                f"{expected_confidence}, got "
                f"{media.timestamp_confidence!r}."
            )
