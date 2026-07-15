"""
============================================================
SBA AI Studio
Resolve Module Locator Regression Test
ML-021
Version : 1.0.0
============================================================

Verifies the Resolve module locator's OWN resolution logic
deterministically - without depending on whether real DaVinci
Resolve happens to be installed on the machine running this
test (it may or may not be, on any given dev or CI machine):

- The "already importable" short-circuit returns None and never
  touches sys.path.
- _settings_path() reads "resolve_module_path" from a controlled
  settings.json, and returns None for a missing file, malformed
  JSON, or an empty/absent value.
- _candidates() yields an env-var-derived path (RESOLVE_SCRIPT_API
  + "/Modules") first when that variable is set.
- DEFAULT_CANDIDATES has a non-empty, sensible entry for every
  major OS - this data structure is what real-world portability
  depends on, so a typo or empty list here would silently break
  it on that OS without any test ever catching it.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from regression.base_test import BaseRegressionTest


class ResolveLocatorRegressionTest(BaseRegressionTest):

    name = "Resolve Module Locator (ML-021)"

    category = "Resolve"

    description = (
        "Verify the Resolve scripting module locator's own "
        "resolution logic (env var, settings.json, default "
        "candidates), independent of whether Resolve is "
        "actually installed on this machine."
    )

    def run(self) -> None:

        import sba_resolve.core.services.resolve_locator as locator

        # --------------------------------------------------
        # 1. Already importable - short circuit, no sys.path
        #    mutation.
        # --------------------------------------------------

        original_find_spec = locator.importlib.util.find_spec

        sys_path_before = list(sys.path)

        try:
            locator.importlib.util.find_spec = (
                lambda name: object()
            )

            result = locator.ensure_resolve_module_importable()

            if result is not None:
                raise RuntimeError(
                    "Expected None when the module is already "
                    f"importable, got {result!r}."
                )

            if sys.path != sys_path_before:
                raise RuntimeError(
                    "sys.path should not be touched when the "
                    "module is already importable."
                )

        finally:
            locator.importlib.util.find_spec = original_find_spec

        # --------------------------------------------------
        # 2. _settings_path()
        # --------------------------------------------------

        with tempfile.TemporaryDirectory() as tmp:

            tmp_path = Path(tmp)

            original_settings_path = locator.DEFAULT_SETTINGS_PATH

            try:
                # Missing file entirely.
                locator.DEFAULT_SETTINGS_PATH = (
                    tmp_path / "does_not_exist.json"
                )

                if locator._settings_path() is not None:
                    raise RuntimeError(
                        "A missing settings file should yield "
                        "None."
                    )

                # Malformed JSON.
                malformed = tmp_path / "malformed.json"
                malformed.write_text("{not json", encoding="utf-8")
                locator.DEFAULT_SETTINGS_PATH = malformed

                if locator._settings_path() is not None:
                    raise RuntimeError(
                        "Malformed JSON should yield None."
                    )

                # No resolve_module_path key at all.
                no_key = tmp_path / "no_key.json"
                no_key.write_text(
                    json.dumps({"theme": "dark"}), encoding="utf-8"
                )
                locator.DEFAULT_SETTINGS_PATH = no_key

                if locator._settings_path() is not None:
                    raise RuntimeError(
                        "A missing resolve_module_path key "
                        "should yield None."
                    )

                # Empty string value.
                empty_value = tmp_path / "empty.json"
                empty_value.write_text(
                    json.dumps({"resolve_module_path": ""}),
                    encoding="utf-8",
                )
                locator.DEFAULT_SETTINGS_PATH = empty_value

                if locator._settings_path() is not None:
                    raise RuntimeError(
                        "An empty resolve_module_path value "
                        "should yield None (treated as unset)."
                    )

                # Valid value.
                valid = tmp_path / "valid.json"
                valid.write_text(
                    json.dumps(
                        {"resolve_module_path": "/some/custom/path"}
                    ),
                    encoding="utf-8",
                )
                locator.DEFAULT_SETTINGS_PATH = valid

                if locator._settings_path() != "/some/custom/path":
                    raise RuntimeError(
                        f"Expected '/some/custom/path', got "
                        f"{locator._settings_path()!r}."
                    )

            finally:
                locator.DEFAULT_SETTINGS_PATH = original_settings_path

        # --------------------------------------------------
        # 3. _candidates() includes the env-var-derived path
        #    first, when RESOLVE_SCRIPT_API is set.
        # --------------------------------------------------

        original_env = os.environ.get("RESOLVE_SCRIPT_API")

        try:
            os.environ["RESOLVE_SCRIPT_API"] = "/fake/resolve/api"

            candidates = list(locator._candidates())

            expected_first = str(
                Path("/fake/resolve/api") / "Modules"
            )

            if not candidates or candidates[0] != expected_first:
                got = candidates[0] if candidates else None
                raise RuntimeError(
                    f"Expected the first candidate to be "
                    f"{expected_first!r} when RESOLVE_SCRIPT_API "
                    f"is set, got {got!r}."
                )

        finally:
            if original_env is None:
                os.environ.pop("RESOLVE_SCRIPT_API", None)
            else:
                os.environ["RESOLVE_SCRIPT_API"] = original_env

        # --------------------------------------------------
        # 4. DEFAULT_CANDIDATES sanity check - every major OS
        #    must have at least one non-empty entry, or
        #    portability silently breaks on that OS.
        # --------------------------------------------------

        for os_name in ("Windows", "Darwin", "Linux"):

            entries = locator.DEFAULT_CANDIDATES.get(os_name)

            if not entries:
                raise RuntimeError(
                    f"DEFAULT_CANDIDATES has no entries for "
                    f"{os_name!r}."
                )

            if not all(isinstance(e, str) and e for e in entries):
                raise RuntimeError(
                    f"DEFAULT_CANDIDATES for {os_name!r} contains "
                    f"an empty or non-string entry: {entries!r}"
                )
