"""
============================================================
SBA AI Studio
Reverse Geocoder
ML-026-001
Version : 1.0.0 Alpha
============================================================

Turns GPS coordinates (already captured on MediaFile via
gps_latitude/gps_longitude) into a human-readable place name,
using OpenStreetMap's free Nominatim reverse-geocoding API.

No API key required, but Nominatim's usage policy requires:
    - A descriptive User-Agent identifying the application.
    - No more than ~1 request/second.

This never raises on network failure - a missing/unreachable
network, a bad response, or no GPS data all just result in None,
so YouTube metadata generation degrades gracefully to "no
location" rather than crashing.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

USER_AGENT = "SBA-AI-Studio/1.0 (motorcycle ride reconstruction tool)"

# Nominatim's usage policy asks for no more than ~1 request per
# second from a single client.
MIN_SECONDS_BETWEEN_REQUESTS = 1.1


class ReverseGeocoder:
    """
    Reverse-geocodes (latitude, longitude) pairs into place
    names, with an in-memory cache (rounded to ~1km precision)
    so a whole day's worth of nearby clips only costs one real
    request.
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._cache: dict[tuple[float, float], str | None] = {}
        self._last_request_time: float = 0.0

    def place_name(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> str | None:
        """
        Returns a short place name (e.g. "Whithorn, Scotland,
        United Kingdom") for the given coordinates, or None if
        coordinates are missing, invalid, or the lookup fails for
        any reason (offline, rate-limited, bad response, etc).
        """

        if latitude is None or longitude is None:
            return None

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return None

        # Round to ~1km precision for cache keys - nearby clips
        # from the same stop shouldn't each cost a real request.
        cache_key = (round(latitude, 2), round(longitude, 2))

        if cache_key in self._cache:
            return self._cache[cache_key]

        place = self._lookup(latitude, longitude)

        self._cache[cache_key] = place

        return place

    def _lookup(self, latitude: float, longitude: float) -> str | None:

        self._respect_rate_limit()

        params = urllib.parse.urlencode(
            {
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 14,
            }
        )

        request = urllib.request.Request(
            f"{NOMINATIM_URL}?{params}",
            headers={"User-Agent": USER_AGENT},
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError):
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None

        return self._extract_place_name(data)

    def _respect_rate_limit(self) -> None:

        elapsed = time.monotonic() - self._last_request_time

        if elapsed < MIN_SECONDS_BETWEEN_REQUESTS:
            time.sleep(MIN_SECONDS_BETWEEN_REQUESTS - elapsed)

        self._last_request_time = time.monotonic()

    @staticmethod
    def _extract_place_name(data: dict) -> str | None:
        """
        Builds a short "Town, Region, Country" style name from
        Nominatim's address breakdown, preferring the most
        specific settlement-level field available.
        """

        address = data.get("address")

        if not isinstance(address, dict):
            return None

        settlement = (
            address.get("town")
            or address.get("village")
            or address.get("city")
            or address.get("hamlet")
            or address.get("municipality")
        )

        region = address.get("state") or address.get("county")

        country = address.get("country")

        parts = [part for part in (settlement, region, country) if part]

        if not parts:
            return None

        return ", ".join(parts)
