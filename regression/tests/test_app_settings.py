"""
============================================================
SBA AI Studio
App Settings Loader Regression Test
ML-019
Version : 1.0.0
============================================================

Verifies load_gap_compression_settings():
- A missing settings file falls back to disabled defaults.
- Malformed JSON falls back to disabled defaults.
- A valid "gap_compression" section is read correctly.
- Invalid values (e.g. compressed_gap_seconds > threshold,
  which GapCompressionSettings itself rejects) fall back to
  disabled defaults rather than raising.
- A missing "gap_compression" section entirely falls back to
  disabled defaults.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from regression.base_test import BaseRegressionTest


class AppSettingsRegressionTest(BaseRegressionTest):

    name = "App Settings Loader (ML-019)"

    category = "Planning"

    description = (
        "Verify Gap Compression settings load correctly from "
        "config/settings.json, and fall back safely to disabled "
        "defaults for any missing, malformed, or invalid input."
    )

    def run(self) -> None:

        from sba_resolve.core.services.app_settings import (
            load_gap_compression_settings,
        )

        with tempfile.TemporaryDirectory() as tmp:

            tmp_path = Path(tmp)

            # 1. Missing file entirely.
            missing = load_gap_compression_settings(
                tmp_path / "does_not_exist.json"
            )

            if missing.enabled:
                raise RuntimeError(
                    "A missing settings file must fall back to "
                    "disabled, got enabled=True."
                )

            # 2. Malformed JSON.
            malformed_path = tmp_path / "malformed.json"
            malformed_path.write_text("{not valid json", encoding="utf-8")

            malformed = load_gap_compression_settings(malformed_path)

            if malformed.enabled:
                raise RuntimeError(
                    "Malformed JSON must fall back to disabled, "
                    "got enabled=True."
                )

            # 3. Valid file, no gap_compression section at all.
            no_section_path = tmp_path / "no_section.json"
            no_section_path.write_text(
                json.dumps({"theme": "dark"}), encoding="utf-8"
            )

            no_section = load_gap_compression_settings(no_section_path)

            if no_section.enabled:
                raise RuntimeError(
                    "A missing gap_compression section must fall "
                    "back to disabled, got enabled=True."
                )

            # 4. Valid, fully specified section.
            valid_path = tmp_path / "valid.json"
            valid_path.write_text(
                json.dumps(
                    {
                        "gap_compression": {
                            "enabled": True,
                            "gap_threshold_seconds": 30,
                            "compressed_gap_seconds": 5,
                        }
                    }
                ),
                encoding="utf-8",
            )

            valid = load_gap_compression_settings(valid_path)

            if not valid.enabled:
                raise RuntimeError(
                    "Expected enabled=True from a valid section, "
                    f"got {valid.enabled!r}."
                )

            if valid.gap_threshold_seconds != 30.0:
                raise RuntimeError(
                    "Expected gap_threshold_seconds=30.0, got "
                    f"{valid.gap_threshold_seconds!r}."
                )

            if valid.compressed_gap_seconds != 5.0:
                raise RuntimeError(
                    "Expected compressed_gap_seconds=5.0, got "
                    f"{valid.compressed_gap_seconds!r}."
                )

            # 5. Invalid combination (compressed > threshold) -
            # GapCompressionSettings itself rejects this via
            # __post_init__; the loader must catch that and fall
            # back rather than raise.
            invalid_path = tmp_path / "invalid.json"
            invalid_path.write_text(
                json.dumps(
                    {
                        "gap_compression": {
                            "enabled": True,
                            "gap_threshold_seconds": 5,
                            "compressed_gap_seconds": 30,
                        }
                    }
                ),
                encoding="utf-8",
            )

            invalid = load_gap_compression_settings(invalid_path)

            if invalid.enabled:
                raise RuntimeError(
                    "An invalid gap_compression combination must "
                    "fall back to disabled, got enabled=True."
                )

        # 6. The real project settings.json must load without
        # raising, regardless of its current values.
        real_settings = load_gap_compression_settings()

        if not isinstance(real_settings.enabled, bool):
            raise RuntimeError(
                "Loading the real config/settings.json did not "
                "produce a valid GapCompressionSettings."
            )
