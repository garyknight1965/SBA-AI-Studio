"""
============================================================
SBA AI Studio
GPX GPS Loader
ML-029-001
Version : 1.0.0 Alpha
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
fix and picks the middle one, rather than the first.
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

    def load(self, media_files: Iterable) -> None:

        for media in media_files:

            if getattr(media, "gps_latitude", None) is not None:
                # Already has GPS (e.g. from embedded EXIF) -
                # don't override it with a GPX-derived guess.
                continue

            gpx_path = self._sibling_gpx_path(media)

            if gpx_path is None or not gpx_path.exists():
                continue

            coords = self._representative_trackpoint(gpx_path)

            if coords is None:
                continue

            media.gps_latitude, media.gps_longitude = coords

    @staticmethod
    def _sibling_gpx_path(media) -> Path | None:

        full_path = getattr(media, "full_path", None)

        if full_path is None:
            return None

        return Path(full_path).with_suffix(".gpx")

    @classmethod
    def _representative_trackpoint(
        cls,
        gpx_path: Path,
    ) -> tuple[float, float] | None:

        try:
            tree = ET.parse(gpx_path)
        except (ET.ParseError, OSError):
            return None

        root = tree.getroot()

        trackpoints = root.findall(f".//{_GPX_NAMESPACE}trkpt")

        if not trackpoints:
            # Fall back to a plain (non-namespaced) search, in
            # case this GPX file doesn't declare the standard
            # namespace.
            trackpoints = root.findall(".//trkpt")

        if not trackpoints:
            return None

        points = [
            point
            for point in (
                cls._parse_point(trkpt) for trkpt in trackpoints
            )
            if point is not None
        ]

        if not points:
            return None

        good_points = [
            (lat, lon)
            for lat, lon, fix, pdop in points
            if (fix is None or fix == "3d")
            and (pdop is None or pdop <= MAX_ACCEPTABLE_PDOP)
        ]

        candidates = good_points or [(lat, lon) for lat, lon, _, _ in points]

        # The middle point, not the first - avoids a GPS
        # warm-up period at the very start of the recording.
        return candidates[len(candidates) // 2]

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
