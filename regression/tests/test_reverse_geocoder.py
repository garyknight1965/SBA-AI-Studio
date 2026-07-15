"""
============================================================
SBA AI Studio
Reverse Geocoder Regression Test
ML-026
Version : 1.0.0
============================================================

Verifies ReverseGeocoder without any real network access - all
urlopen calls are mocked:

- Missing/invalid coordinates return None without a network
  call at all.
- A successful Nominatim-shaped response is parsed into a
  "Town, Region, Country" place name.
- The same (rounded) coordinates are only looked up once - the
  second call is served from cache, no second network call.
- Network failures (connection errors, timeouts, bad JSON)
  degrade to None rather than raising.
"""

from __future__ import annotations

import json

from regression.base_test import BaseRegressionTest


class ReverseGeocoderRegressionTest(BaseRegressionTest):

    name = "Reverse Geocoder (ML-026)"

    category = "Planning"

    description = (
        "Verify reverse geocoding, caching, and graceful "
        "degradation on network failure, using a mocked HTTP "
        "layer (no real network calls)."
    )

    def run(self) -> None:

        import urllib.error

        import sba_resolve.core.services.reverse_geocoder as geocoder_module
        from sba_resolve.core.services.reverse_geocoder import (
            ReverseGeocoder,
        )

        original_urlopen = geocoder_module.urllib.request.urlopen

        try:
            # --------------------------------------------------
            # 1. Missing coordinates - no network call at all.
            # --------------------------------------------------

            call_count = {"count": 0}

            def counting_urlopen(*args, **kwargs):
                call_count["count"] += 1
                raise AssertionError(
                    "Should not attempt a network call for "
                    "missing coordinates."
                )

            geocoder_module.urllib.request.urlopen = counting_urlopen

            geocoder = ReverseGeocoder(timeout_seconds=1.0)
            geocoder._respect_rate_limit = lambda: None  # skip sleeps

            if geocoder.place_name(None, None) is not None:
                raise RuntimeError(
                    "Missing coordinates should return None."
                )

            if call_count["count"] != 0:
                raise RuntimeError(
                    "Missing coordinates should not trigger a "
                    "network call."
                )

            # --------------------------------------------------
            # 2. Successful lookup, parsed correctly, then cached.
            # --------------------------------------------------

            class FakeResponse:
                def __init__(self, body: bytes):
                    self._body = body

                def read(self):
                    return self._body

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            success_body = json.dumps(
                {
                    "address": {
                        "town": "Whithorn",
                        "county": "Dumfries and Galloway",
                        "country": "United Kingdom",
                    }
                }
            ).encode("utf-8")

            lookup_calls = {"count": 0}

            def success_urlopen(*args, **kwargs):
                lookup_calls["count"] += 1
                return FakeResponse(success_body)

            geocoder_module.urllib.request.urlopen = success_urlopen

            place = geocoder.place_name(54.7319, -4.4180)

            if place != "Whithorn, Dumfries and Galloway, United Kingdom":
                raise RuntimeError(
                    f"Expected 'Whithorn, Dumfries and Galloway, "
                    f"United Kingdom', got {place!r}."
                )

            if lookup_calls["count"] != 1:
                raise RuntimeError(
                    "Expected exactly 1 network call for the "
                    "first lookup."
                )

            # Same coordinates again (even with tiny jitter within
            # the ~1km rounding) - must be served from cache, no
            # second network call.
            place_again = geocoder.place_name(54.7321, -4.4179)

            if place_again != place:
                raise RuntimeError(
                    "Cached lookup returned a different result."
                )

            if lookup_calls["count"] != 1:
                raise RuntimeError(
                    "Expected the second lookup to be served from "
                    f"cache (still 1 network call), got "
                    f"{lookup_calls['count']}."
                )

            # --------------------------------------------------
            # 3. Network failure degrades to None, not an
            #    exception.
            # --------------------------------------------------

            def failing_urlopen(*args, **kwargs):
                raise urllib.error.URLError("no route to host")

            geocoder_module.urllib.request.urlopen = failing_urlopen

            offline_place = geocoder.place_name(10.0, 10.0)

            if offline_place is not None:
                raise RuntimeError(
                    "A network failure should degrade to None, "
                    f"got {offline_place!r}."
                )

            # --------------------------------------------------
            # 4. Malformed JSON also degrades to None.
            # --------------------------------------------------

            def malformed_json_urlopen(*args, **kwargs):
                return FakeResponse(b"{not valid json")

            geocoder_module.urllib.request.urlopen = (
                malformed_json_urlopen
            )

            malformed_place = geocoder.place_name(20.0, 20.0)

            if malformed_place is not None:
                raise RuntimeError(
                    "Malformed JSON should degrade to None, got "
                    f"{malformed_place!r}."
                )

        finally:
            geocoder_module.urllib.request.urlopen = original_urlopen
