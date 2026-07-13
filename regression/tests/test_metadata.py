"""
============================================================
SBA AI Studio
Metadata Regression Test
Version : 1.0.0
Sprint : R2
============================================================
"""

from __future__ import annotations

from regression.base_test import BaseRegressionTest


class MetadataRegressionTest(BaseRegressionTest):

    name = "Metadata Normalizer"

    category = "Metadata"

    description = "Verify metadata normalization."

    def run(self):

        from sba_resolve.core.metadata.metadata_normalizer import (
            MetadataNormalizer,
        )

        sample = {
            "FileSize": "1024 MB",
            "ImageWidth": "3840",
            "ImageHeight": "2160",
            "VideoFrameRate": "59.94",
            "AvgBitrate": "120000000",
            "AudioChannels": "2",
            "AudioSampleRate": "48000",
            "Model": "HERO13 Black",
        }

        result = MetadataNormalizer.normalize_item(sample)

        assert result["FileSize"] > 0
        assert result["ImageWidth"] == 3840
        assert result["ImageHeight"] == 2160
        assert result["VideoFrameRate"] == 59.94
        assert result["AudioChannels"] == 2
        assert result["AudioSampleRate"] == 48000
        assert result["Make"] == "GoPro"