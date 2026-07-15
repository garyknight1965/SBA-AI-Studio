"""
============================================================
SBA AI Studio
Metadata Mapper Regression Test
Version : 1.0.0
Sprint : R2
============================================================
"""

from __future__ import annotations

from pathlib import Path

from regression.base_test import BaseRegressionTest


class MetadataMapperRegressionTest(BaseRegressionTest):

    name = "Metadata Mapper"
    category = "Metadata"
    description = "Verify metadata maps correctly to MediaFile."

    def run(self) -> None:

        from sba_resolve.core.metadata.metadata_mapper import MetadataMapper

        sample = {
            "SourceFile": "D:/Movies/Test/GX010001.MP4",
            "FileSize": 1024000,
            "ImageWidth": 3840,
            "ImageHeight": 2160,
            "VideoFrameRate": 59.94,
            "Duration": "00:00:15",
            "CompressorName": "H.265",
            "AvgBitrate": 120000000,
            "AudioChannels": 2,
            "AudioSampleRate": 48000,
            "Model": "HERO13 Black",
            "Make": "GoPro",
        }

        media = MetadataMapper.map(
            sample,
            Path("D:/Movies/Test"),
        )

        assert media.filename == "GX010001.MP4"
        assert media.camera_make == "GoPro"
        assert media.is_video
        assert media.width == 3840
        assert media.height == 2160
        assert media.fps == 59.94
        assert media.codec == "H.265"
        assert media.audio_channels == 2
        assert media.sample_rate == 48000