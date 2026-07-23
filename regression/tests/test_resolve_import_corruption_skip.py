"""
============================================================
SBA AI Studio
Resolve Import Corruption Skip Regression Test
ML-036
Version : 1.0.0
============================================================

Verifies MainWindow._split_media_by_corruption(): files the
Corruption Detector flagged (MediaFile.corrupted, set during
WorkspaceController.scan_project() - ML-035) are separated out of
the media handed to Resolve's import step, rather than reaching
Resolve's ImportMedia and failing there with no usable reason -
this is the exact real-world case GX010219.MP4 hit.

Tested via the pure static method directly - no QMessageBox, no
real Resolve connection, no event loop risk.
"""

from __future__ import annotations

import os
from pathlib import Path

from regression.base_test import BaseRegressionTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ResolveImportCorruptionSkipRegressionTest(BaseRegressionTest):

    name = "Resolve Import Corruption Skip (ML-036)"

    requires_gui = True

    category = "Resolve"

    description = (
        "Verify corrupted media (ML-035) is excluded from what "
        "gets sent to Resolve's import step."
    )

    def _make_media(self, filename, corrupted, reason=""):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            corrupted=corrupted,
            corruption_reason=reason,
        )

    def run(self) -> None:

        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        from ui.windows.main_window import MainWindow

        clean_clip = self._make_media("clean.mp4", corrupted=False)

        corrupted_clip = self._make_media(
            "GX010219.MP4",
            corrupted=True,
            reason=(
                "No 'moov' box found - recording likely stopped "
                "before the index was written"
            ),
        )

        # --------------------------------------------------
        # 1. Mixed list: one clean, one corrupted.
        # --------------------------------------------------

        clean, corrupted = MainWindow._split_media_by_corruption(
            [clean_clip, corrupted_clip]
        )

        if clean != [clean_clip]:
            raise RuntimeError(
                f"Expected only the clean clip in the clean list, "
                f"got {[m.filename for m in clean]!r}."
            )

        if corrupted != [corrupted_clip]:
            raise RuntimeError(
                f"Expected only the corrupted clip in the "
                f"corrupted list, got "
                f"{[m.filename for m in corrupted]!r}."
            )

        # --------------------------------------------------
        # 2. All clean: nothing should end up in `corrupted`.
        # --------------------------------------------------

        clean2, corrupted2 = MainWindow._split_media_by_corruption(
            [clean_clip]
        )

        if corrupted2:
            raise RuntimeError(
                "Expected no corrupted files when every input file "
                f"is clean, got {[m.filename for m in corrupted2]!r}."
            )

        # --------------------------------------------------
        # 3. All corrupted: nothing should end up in `clean` -
        #    this is the "nothing to import" path in
        #    import_to_resolve().
        # --------------------------------------------------

        clean3, corrupted3 = MainWindow._split_media_by_corruption(
            [corrupted_clip]
        )

        if clean3:
            raise RuntimeError(
                "Expected no clean files when every input file is "
                f"corrupted, got {[m.filename for m in clean3]!r}."
            )

        if len(corrupted3) != 1:
            raise RuntimeError(
                f"Expected 1 corrupted file, got {len(corrupted3)}."
            )