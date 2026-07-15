"""
============================================================
SBA AI Studio
GPX GPS Loader Regression Test
ML-029
Version : 1.0.0
============================================================

Verifies GpxGpsLoader:
- Filters out unreliable trackpoints (no "3d" fix, or PDOP above
  the acceptable threshold - GoPro's typical "not locked yet"
  sentinel is ~99) and picks a genuinely good point instead of
  blindly using the first one.
- Never overrides a MediaFile that already has GPS coordinates
  (e.g. from embedded EXIF metadata).
- Degrades gracefully (does nothing) when there's no sibling
  .gpx file, or it's malformed.
- Falls back to a non-namespaced search if the GPX file doesn't
  declare the standard namespace.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from regression.base_test import BaseRegressionTest


NAMESPACED_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="55.37843020" lon="6.99358740"><pdop>99.989998</pdop></trkpt>
      <trkpt lat="55.37843020" lon="6.99358740"><pdop>99.989998</pdop></trkpt>
      <trkpt lat="51.93250000" lon="5.85100000"><fix>3d</fix><pdop>2.44</pdop></trkpt>
      <trkpt lat="51.93260000" lon="5.85200000"><fix>3d</fix><pdop>2.40</pdop></trkpt>
      <trkpt lat="51.93270000" lon="5.85300000"><fix>3d</fix><pdop>2.38</pdop></trkpt>
    </trkseg>
  </trk>
</gpx>
"""

NO_NAMESPACE_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="10.0" lon="20.0"><fix>3d</fix><pdop>1.5</pdop></trkpt>
    </trkseg>
  </trk>
</gpx>
"""

ALL_BAD_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.07544090" lon="-1.98648230"><pdop>99.989998</pdop></trkpt>
      <trkpt lat="52.07544090" lon="-1.98648230"><pdop>99.989998</pdop></trkpt>
      <trkpt lat="52.07544090" lon="-1.98648230"><pdop>99.989998</pdop></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


class GpxGpsLoaderRegressionTest(BaseRegressionTest):

    name = "GPX GPS Loader (ML-029)"

    category = "Planning"

    description = (
        "Verify GPX sidecar GPS loading filters out unreliable "
        "trackpoints, never overrides existing GPS, and degrades "
        "gracefully on missing/malformed files."
    )

    def _make_media(self, full_path, gps_latitude=None, camera_model="HERO13 Black"):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=Path(full_path).name,
            full_path=Path(full_path),
            relative_path=Path(Path(full_path).name),
            extension=".mp4",
            size=1024,
            camera_model=camera_model,
            gps_latitude=gps_latitude,
            gps_longitude=(-1.0 if gps_latitude is not None else None),
        )

    def run(self) -> None:

        from sba_resolve.core.services.gpx_gps_loader import GpxGpsLoader

        with tempfile.TemporaryDirectory() as tmp:

            tmp_path = Path(tmp)

            # --------------------------------------------------
            # 1. Good GPX file - bad-fix points must be filtered
            #    out, a good point selected (not the first,
            #    unreliable one).
            # --------------------------------------------------

            good_gpx = tmp_path / "GH010167.gpx"
            good_gpx.write_text(NAMESPACED_GPX, encoding="utf-8")

            clip_with_gpx = self._make_media(
                tmp_path / "GH010167.mp4"
            )

            loader = GpxGpsLoader()

            loader.load([clip_with_gpx])

            if clip_with_gpx.gps_latitude is None:
                raise RuntimeError(
                    "Expected GPS to be loaded from the sibling "
                    ".gpx file."
                )

            if clip_with_gpx.gps_latitude == 55.37843020:
                raise RuntimeError(
                    "Loader used the unreliable first trackpoint "
                    "(PDOP ~99.99, no real fix) instead of "
                    "filtering it out."
                )

            # 3 good points (indices 2,3,4 in the file) -> middle
            # of those 3 is the 2nd one: lat 51.9326.
            if clip_with_gpx.gps_latitude != 51.9326:
                raise RuntimeError(
                    f"Expected the middle GOOD trackpoint "
                    f"(51.9326), got {clip_with_gpx.gps_latitude!r}."
                )

            # --------------------------------------------------
            # 2. Existing GPS must never be overridden.
            # --------------------------------------------------

            clip_with_existing_gps = self._make_media(
                tmp_path / "GH010167.mp4", gps_latitude=99.0
            )

            loader.load([clip_with_existing_gps])

            if clip_with_existing_gps.gps_latitude != 99.0:
                raise RuntimeError(
                    "Loader must never override existing GPS "
                    "coordinates."
                )

            # --------------------------------------------------
            # 3. No sibling .gpx file - degrades gracefully.
            # --------------------------------------------------

            clip_without_gpx = self._make_media(
                tmp_path / "GX010001.mp4"
            )

            loader.load([clip_without_gpx])

            if clip_without_gpx.gps_latitude is not None:
                raise RuntimeError(
                    "Expected no GPS when there's no sibling .gpx "
                    "file."
                )

            # --------------------------------------------------
            # 4. Malformed GPX file - degrades gracefully, no
            #    exception.
            # --------------------------------------------------

            malformed_gpx = tmp_path / "GH020000.gpx"
            malformed_gpx.write_text("<gpx><trk", encoding="utf-8")

            clip_with_malformed_gpx = self._make_media(
                tmp_path / "GH020000.mp4"
            )

            loader.load([clip_with_malformed_gpx])

            if clip_with_malformed_gpx.gps_latitude is not None:
                raise RuntimeError(
                    "Expected no GPS from a malformed .gpx file, "
                    "not a crash or a garbage value."
                )

            # --------------------------------------------------
            # 5. No-namespace fallback.
            # --------------------------------------------------

            no_ns_gpx = tmp_path / "GH030000.gpx"
            no_ns_gpx.write_text(NO_NAMESPACE_GPX, encoding="utf-8")

            clip_no_ns = self._make_media(tmp_path / "GH030000.mp4")

            loader.load([clip_no_ns])

            if clip_no_ns.gps_latitude != 10.0:
                raise RuntimeError(
                    f"Expected GPS from the non-namespaced GPX "
                    f"file (10.0), got {clip_no_ns.gps_latitude!r}."
                )

            # --------------------------------------------------
            # 6. Untrusted camera model - GPX data must be
            #    ignored entirely, even with a perfectly good
            #    GPX file present.
            # --------------------------------------------------

            hero8_gpx = tmp_path / "GH010167.gpx"
            hero8_gpx.write_text(NAMESPACED_GPX, encoding="utf-8")

            hero8_clip = self._make_media(
                tmp_path / "GH010167.mp4",
                camera_model="HERO8 Black",
            )

            loader.load([hero8_clip])

            if hero8_clip.gps_latitude is not None:
                raise RuntimeError(
                    "GPS should not be loaded for an untrusted "
                    "camera model (HERO8), even with a good GPX "
                    "file present."
                )

            # --------------------------------------------------
            # 7. A GPX file where NO trackpoint ever achieved a
            #    real lock must yield no location at all - not a
            #    confidently-wrong stale fallback. This is the
            #    exact real-world failure mode that produced a
            #    wrong "Charlton, UK" location from a stale fix.
            # --------------------------------------------------

            all_bad_gpx = tmp_path / "GX010099.gpx"
            all_bad_gpx.write_text(ALL_BAD_GPX, encoding="utf-8")

            clip_all_bad = self._make_media(
                tmp_path / "GX010099.mp4"
            )

            loader.load([clip_all_bad])

            if clip_all_bad.gps_latitude is not None:
                raise RuntimeError(
                    "Expected no location when every trackpoint "
                    "in the file is low-quality (no real GPS "
                    f"lock), got {clip_all_bad.gps_latitude!r} - "
                    "this must not fall back to a stale/wrong "
                    "position."
                )
