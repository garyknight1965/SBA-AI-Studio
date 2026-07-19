"""
============================================================
SBA AI Studio
Map Panel
GUI-012
Version : 1.3.0
============================================================

Shows scanned media on a real interactive map (Leaflet.js +
OpenStreetMap tiles, via QWebEngineView) - a pin for every clip
with a known GPS location, plus a single line connecting those
pins in chronological order.

Requires an internet connection to fetch map tiles - consistent
with the app's existing use of real network calls elsewhere
(ReverseGeocoder). No API key needed; OpenStreetMap's standard
tile server is free for reasonable use.

Only clips with GPS data actually appear - clips from untrusted
cameras (see GpxGpsLoader.TRUSTED_CAMERA_MODELS) or with no GPS
lock at all are silently excluded, not guessed at.

Versions 1.1.0/1.2.0 tried drawing the route from the FULL GPX
trackpoint sequence (per ride day, then per clip) to trace the
actual road - both were more complex than needed. Version 1.3.0
(2026-07-19, per Gary) simplifies to what was actually wanted:
just connect each clip's single representative pin to the next
in chronological order - straight lines, not road-following, but
simple and predictable. MediaFile.gps_track (the full trackpoint
list added for the earlier approach) is left in the model
unused, in case a road-following route is wanted again later.
"""

from __future__ import annotations

import json
from datetime import datetime

from PySide6.QtWebEngineWidgets import QWebEngineView

_MAP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<link rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
    html, body, #map { height: 100%; margin: 0; padding: 0; }
    .leaflet-popup-content { font-family: sans-serif; font-size: 13px; }
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    var map = L.map('map').setView([0, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    var currentLayers = [];

    function updateMapData(pins) {

        currentLayers.forEach(function(layer) {
            map.removeLayer(layer);
        });
        currentLayers = [];

        var bounds = [];
        var routePoints = [];

        pins.forEach(function(pin) {
            var marker = L.marker([pin.lat, pin.lon])
                .bindPopup(pin.label)
                .addTo(map);
            currentLayers.push(marker);
            bounds.push([pin.lat, pin.lon]);
            routePoints.push([pin.lat, pin.lon]);
        });

        if (routePoints.length > 1) {
            var routeLine = L.polyline(routePoints, {
                color: '#4f8cff',
                weight: 4,
                opacity: 0.8
            }).addTo(map);
            currentLayers.push(routeLine);
        }

        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [30, 30] });
        }
    }
</script>
</body>
</html>
"""


class MapWidget(QWebEngineView):
    """
    Central-widget map panel. set_media() is the only method
    callers need - it extracts each clip's pin (skipping clips
    with no GPS) and redraws the map with a line connecting them
    in chronological order. Safe to call with an empty list
    (clears the map).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loaded = False
        self._pending_media = None

        self.loadFinished.connect(self._on_load_finished)
        self.setHtml(_MAP_HTML)

    def _on_load_finished(self, ok: bool) -> None:
        self._loaded = ok
        if ok and self._pending_media is not None:
            self._push_update(self._pending_media)
            self._pending_media = None

    def set_media(self, media_list) -> None:
        """
        Redraws the map from a list of MediaFile objects. Clips
        with no gps_latitude/gps_longitude are skipped entirely.
        Remaining clips are sorted by `created` timestamp and
        connected pin-to-pin, in chronological order.
        """

        if not self._loaded:
            # The page hasn't finished its first load yet - queue
            # this update for _on_load_finished() to apply once
            # it has, rather than silently dropping it.
            self._pending_media = list(media_list)
            return

        self._push_update(media_list)

    def _push_update(self, media_list) -> None:

        media_list = sorted(
            media_list,
            key=lambda m: getattr(m, "created", None) or datetime.min,
        )

        pins = []

        for media in media_list:

            lat = getattr(media, "gps_latitude", None)
            lon = getattr(media, "gps_longitude", None)

            if lat is not None and lon is not None:
                pins.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "label": str(
                            getattr(media, "filename", "")
                        ),
                    }
                )

        pins_json = json.dumps(pins)

        self.page().runJavaScript(f"updateMapData({pins_json});")

    def clear(self) -> None:
        self.set_media([])