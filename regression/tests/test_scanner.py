"""
============================================================
SBA AI Studio
Scanner Regression Test
Version : 2.0.0
Sprint : R2 / ML-021
============================================================

Version 2.0 (ML-021) replaces the previous hardcoded dependency
on a real project folder (D:\\Movies\\ABR) with a self-contained
synthetic fixture, so this test runs identically on any machine
- it no longer requires Gary's actual footage to exist at a
fixed path.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from regression.base_test import BaseRegressionTest


class ScannerRegressionTest(BaseRegressionTest):

    name = "Project Scanner"

    category = "Scanner"

    description = "Verify recursive scanner."

    def run(self):

        from sba_resolve.core.project_scanner import ProjectScanner

        with tempfile.TemporaryDirectory() as tmp:

            project_root = Path(tmp)

            # A couple of accepted original-camera files...
            (project_root / "GX010001.MP4").write_bytes(b"\x00")
            (project_root / "GH010002.MP4").write_bytes(b"\x00")

            # ...nested a folder deep, to verify recursion...
            subfolder = project_root / "DCIM" / "100GOPRO"
            subfolder.mkdir(parents=True)
            (subfolder / "GX010003.MP4").write_bytes(b"\x00")

            # ...and a Proxy folder, which ProjectScanner must
            # skip entirely regardless of what's inside it.
            proxy_folder = project_root / "Proxy"
            proxy_folder.mkdir()
            (proxy_folder / "GX010001.MP4").write_bytes(b"\x00")

            scanner = ProjectScanner(project_root)

            media = scanner.scan()

            if len(media) != 3:
                raise RuntimeError(
                    f"Expected 3 scanned files (Proxy folder "
                    f"contents must be skipped), got {len(media)}: "
                    f"{[m.filename for m in media]}"
                )

            if scanner.statistics.media_found != len(media):
                raise RuntimeError(
                    "Statistics mismatch."
                )

            if scanner.statistics.errors:
                raise RuntimeError(
                    f"{len(scanner.statistics.errors)} scan errors."
                )