"""
============================================================
SBA AI Studio
Camera Recognition Engine Regression Test
ML-054 (Step 1)
Version: 1.0.0
============================================================

Verifies:
- Insta360 X3 real-world filenames (with and without the
  trailing 6-digit suffix) are correctly detected via the new
  filename-pattern rule, even with zero identifying metadata -
  covers the real gap found in ML-054 (Insta360 Studio-exported
  files carry no Make/Model/handler tags at all).
- GoPro HERO13/HERO8 metadata detection is unchanged.
- DJI Flip / other DJI detection is unchanged.
- A file sitting in a "/360/" folder but with a non-matching
  filename still falls back correctly to the folder rule
  (confidence 75), confirming the new filename check doesn't
  swallow that path.
- A completely unrecognized file still returns an unrecognized
  CameraProfile() (manufacturer UNKNOWN) - never a false
  positive.
- GoPro/DJI-style filenames never accidentally match the new
  Insta360 filename pattern (no false positives introduced).
"""

from __future__ import annotations

from regression.base_test import BaseRegressionTest


class CameraRecognitionEngineRegressionTest(BaseRegressionTest):

    name = "Camera Recognition Engine (ML-054 Step 1)"

    category = "Metadata"

    description = (
        "Verify Insta360 X3 filename-pattern detection works on "
        "real-world filenames with zero identifying metadata, "
        "without breaking existing GoPro/DJI/folder-rule "
        "detection."
    )

    def run(self) -> None:

        from sba_resolve.core.models.camera_profile import (
            CameraManufacturer,
            CameraType,
        )
        from sba_resolve.core.services.camera_recognition_engine import (
            CameraRecognitionEngine,
        )

        profile = CameraRecognitionEngine.detect(
            {}, r"D:\Movies\Friday 17\VID_20260717_114753_10_002.mp4"
        )

        if profile.manufacturer != CameraManufacturer.INSTA360:
            raise RuntimeError(
                "Real X3 filename (no suffix) must be detected as "
                "Insta360, got " + repr(profile.manufacturer)
            )

        if profile.confidence != 85:
            raise RuntimeError(
                "Filename-pattern detection must report confidence "
                "85, got " + repr(profile.confidence)
            )

        if profile.detection_method != "Filename Pattern":
            raise RuntimeError(
                "Expected detection_method 'Filename Pattern', got "
                + repr(profile.detection_method)
            )

        profile_suffixed = CameraRecognitionEngine.detect(
            {},
            r"D:\Movies\Friday 17\VID_20260717_152440_00_008_204150.mp4",
        )

        if profile_suffixed.manufacturer != CameraManufacturer.INSTA360:
            raise RuntimeError(
                "Real X3 filename (with suffix) must be detected as "
                "Insta360, got " + repr(profile_suffixed.manufacturer)
            )

        if profile_suffixed.detection_method != "Filename Pattern":
            raise RuntimeError(
                "Suffixed X3 filename must also use 'Filename "
                "Pattern' detection, got "
                + repr(profile_suffixed.detection_method)
            )

        gopro_profile = CameraRecognitionEngine.detect(
            {"Model": "HERO13 Black"}, r"D:\Movies\Friday 17\GX010071.MP4"
        )

        if gopro_profile.manufacturer != CameraManufacturer.GOPRO:
            raise RuntimeError(
                "GoPro metadata detection must be unaffected by "
                "the new filename rule, got "
                + repr(gopro_profile.manufacturer)
            )

        if gopro_profile.camera_type != CameraType.ACTION:
            raise RuntimeError(
                "GoPro camera_type must still resolve to ACTION, "
                "got " + repr(gopro_profile.camera_type)
            )

        dji_profile = CameraRecognitionEngine.detect(
            {"Make": "DJI", "MetaFormat": "djmd"},
            r"D:\Movies\drone\DJI_0001.mp4",
        )

        if dji_profile.manufacturer != CameraManufacturer.DJI:
            raise RuntimeError(
                "DJI detection must be unaffected by the new "
                "filename rule, got " + repr(dji_profile.manufacturer)
            )

        folder_rule_profile = CameraRecognitionEngine.detect(
            {}, r"D:\Movies\360\clip001.mp4"
        )

        if folder_rule_profile.manufacturer != CameraManufacturer.INSTA360:
            raise RuntimeError(
                "Non-matching filename inside a 360 folder must "
                "still be detected via the folder rule, got "
                + repr(folder_rule_profile.manufacturer)
            )

        if folder_rule_profile.confidence != 75:
            raise RuntimeError(
                "Folder-rule detection must report confidence 75, "
                "got " + repr(folder_rule_profile.confidence)
            )

        if folder_rule_profile.detection_method != "Folder Rule":
            raise RuntimeError(
                "Expected detection_method 'Folder Rule', got "
                + repr(folder_rule_profile.detection_method)
            )

        unknown_profile = CameraRecognitionEngine.detect(
            {}, r"D:\Movies\misc\random_clip.mp4"
        )

        if unknown_profile.manufacturer != CameraManufacturer.UNKNOWN:
            raise RuntimeError(
                "A completely unrecognized file must return an "
                "empty CameraProfile with manufacturer UNKNOWN, "
                "got " + repr(unknown_profile.manufacturer)
            )

        false_positive_check = CameraRecognitionEngine.detect(
            {}, r"D:\Movies\Friday 17\GX010071.MP4"
        )

        if false_positive_check.manufacturer == CameraManufacturer.INSTA360:
            raise RuntimeError(
                "GoPro-style filename GX010071.MP4 must NOT match "
                "the Insta360 filename pattern - false positive "
                "detected."
            )