"""
============================================================
SBA AI Studio
ExifTool Regression Test
Version : 1.0.0
Sprint : R2
============================================================
"""

from __future__ import annotations

from regression.base_test import BaseRegressionTest


class ExifToolRegressionTest(BaseRegressionTest):

    name = "ExifTool Engine"
    category = "Metadata"
    description = "Verify bundled ExifTool is available."

    def run(self) -> None:

        from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine

        engine = ExifToolEngine()

        if engine.exiftool is None:
            raise RuntimeError("ExifTool executable not found.")

        metadata = engine.read([])

        if metadata != []:
            raise RuntimeError(
                "Expected empty list when reading zero files."
            )