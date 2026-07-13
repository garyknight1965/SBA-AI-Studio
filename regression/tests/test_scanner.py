"""
============================================================
SBA AI Studio
Scanner Regression Test
Version : 1.0.0
Sprint : R2
============================================================
"""

from __future__ import annotations

from pathlib import Path

from regression.base_test import BaseRegressionTest


class ScannerRegressionTest(BaseRegressionTest):

    name = "Project Scanner"

    category = "Scanner"

    description = "Verify recursive scanner."

    def run(self):

        from sba_resolve.core.project_scanner import ProjectScanner

        folder = Path(r"D:\Movies\ABR")

        if not folder.exists():
            raise FileNotFoundError(folder)

        scanner = ProjectScanner(folder)

        media = scanner.scan()

        if len(media) == 0:
            raise RuntimeError(
                "Scanner returned no media."
            )

        if scanner.statistics.media_found != len(media):
            raise RuntimeError(
                "Statistics mismatch."
            )

        if scanner.statistics.errors:
            raise RuntimeError(
                f"{len(scanner.statistics.errors)} scan errors."
            )