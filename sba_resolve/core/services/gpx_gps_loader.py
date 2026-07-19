"""
============================================================
SBA AI Studio
GPX GPS Loader
ML-029-001
Version : 1.1.0
============================================================

GoPro's embedded GPMF telemetry generally isn't exposed by
ExifTool as a simple GPSLatitude/GPSLongitude tag, so GPS
location for GoPro footage often only exists in a separate
per-clip .gpx sidecar file (e.g. exported via a telemetry
extraction tool) - GH010167.MP4 -> GH010167.gpx, same folder,
same filename stem.

This loader picks that up as a fallback: for any MediaFile that
doesn't already have GPS coordinates (e.g. from embedded EXIF),
it looks for a sibling .gpx file and, if found, stamps a
representative trackpoint's coordinates onto it.

Trackpoint quality varies a lot within one file - GPS often
hasn't locked on yet at the very start of a recording, reporting
a frozen, unreliable position with a very high PDOP (dilution of
precision - lower is better; ~99 is GPX/GoPro's typical
"no real fix yet" sentinel) and no <fix> tag or fix != "3d".
Blindly using the first trackpoint can give a completely wrong
location - this filters for a genuinely locked, low-uncertainty
fix and picks the middle one, rather than the first. If NO
trackpoint in the whole file ever achieved a good lock, this
returns no location at all rather than falling back to a
stale/unreliable point - a confidently wrong location (observed
in practice: a leftover fix from a previous location, reverse-
geocoding to the wrong place entirely) is worse than none.

Only trusted camera models (see TRUSTED_CAMERA_MODELS) have
their GPX data used at all - other cameras have shown
unreliable GPS in practice.

Version 1.1.0 (2026-07-19, GUI-012) additionally stamps the
FULL sequence of good trackpoints onto media.gps_track (not just
the single middle representative point onto
gps_latitude/gps_longitude, which is unchanged) - used to draw a
real route line on the new Map panel. Only populated in the same
cases the single-point stamping already applies (trusted camera,
no pre-existing GPS, a good lock exists somewhere in the file).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

_GPX_NAMESPACE = "{http://www.topografix.com/GPX/1/1}"

# A trackpoint counts as "good" for location purposes only if
# its PDOP is at or below this. Real GPS fixes are typically
# well under 10; GoPro's "not locked yet" sentinel is ~99.
MAX_ACCEPTABLE_PDOP = 10.0


class GpxGpsLoader:
    """
    Stamps GPS coordinates from sibling .gpx files onto
    MediaFiles that don't already have them.
    """

    # Only trust GPX GPS data from these camera models. HERO13
    # footage has consistently shown a good GPS lock; other
    # cameras (HERO8, Insta360, DJI) have shown unreliable or
    # stale GPS data in practice (e.g. a leftover fix from a
    # previous location, reverse-geocoding to a wrong place
    # entirely). Adjust this list if that changes - matched as a
    # substring against camera_model, case-insensitive.
    TRUSTED_CAMERA_MODELS: tuple[str, ...] = ("HERO13",)

    def load(self, media_files: Iterable) -> None:

        for media in media_files:

            if getattr(media, "gps_latitude", None) is not None:
                # Already has GPS (e.g. from embedded EXIF) -
                # don't override it with a GPX-derived guess.
                continue

            if not self._is_trusted_camera(media):
                continue

            gpx_path = self._sibling_gpx_path(media)

            if gpx_path is None or not gpx_path.exists():
                continue

            good_points = self._good_trackpoints(gpx_path)

            if not good_points:
                continue

            # The middle point, not the first - avoids a GPS
            # warm-up period at the very start of the recording.
            media.gps_latitude, media.gps_longitude = good_points[
                len(good_points) // 2
            ]

            # GUI-012: the full sequence, for the Map panel's
            # route line - separate from the single representative
            # point above, which stays exactly as before.
            media.gps_track = good_points

    @classmethod
    def _is_trusted_camera(cls, media) -> bool:

        model = str(getattr(media, "camera_model", "") or "").upper()

        return any(
            trusted.upper() in model
            for trusted in cls.TRUSTED_CAMERA_MODELS
        )

    @staticmethod
    def _sibling_gpx_path(media) -> Path | None:

        full_path = getattr(media, "full_path", None)

        if full_path is None:
            return None

        return Path(full_path).with_suffix(".gpx")

    @classmethod
    def _good_trackpoints(
        cls,
        gpx_path: Path,
    ) -> list[tuple[float, float]]:
        """
        Returns every trackpoint in the file that achieved a
        genuine GPS lock (fix == "3d" or no fix tag at all, and
        PDOP at or below MAX_ACCEPTABLE_PDOP), in file order.
        Empty list if the file couldn't be parsed, has no
        trackpoints at all, or never achieved a good lock - a
        confidently wrong location/route is worse than none.
        """

        try:
            tree = ET.parse(gpx_path)
        except (ET.ParseError, OSError):
            return []

        root = tree.getroot()

        trackpoints = root.findall(f".//{_GPX_NAMESPACE}trkpt")

        if not trackpoints:
            # Fall back to a plain (non-namespaced) search, in
            # case this GPX file doesn't declare the standard
            # namespace.
            trackpoints = root.findall(".//trkpt")

        if not trackpoints:
            return []

        points = [
            point
            for point in (
                cls._parse_point(trkpt) for trkpt in trackpoints
            )
            if point is not None
        ]

        return [
            (lat, lon)
            for lat, lon, fix, pdop in points
            if (fix is None or fix == "3d")
            and (pdop is None or pdop <= MAX_ACCEPTABLE_PDOP)
        ]

    @classmethod
    def _parse_point(cls, trkpt) -> tuple | None:

        lat = trkpt.get("lat")
        lon = trkpt.get("lon")

        if lat is None or lon is None:
            return None

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return None

        fix_element = trkpt.find(f"{_GPX_NAMESPACE}fix")

        if fix_element is None:
            fix_element = trkpt.find("fix")

        fix = fix_element.text if fix_element is not None else None

        pdop_element = trkpt.find(f"{_GPX_NAMESPACE}pdop")

        if pdop_element is None:
            pdop_element = trkpt.find("pdop")

        pdop = None

        if pdop_element is not None and pdop_element.text:
            try:
                pdop = float(pdop_element.text)
            except (TypeError, ValueError):
                pdop = None

        return lat, lon, fix, pdop