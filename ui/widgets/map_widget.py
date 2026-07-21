"""
============================================================
SBA AI Studio
Map Panel
GUI-012
Version : 1.4.0
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

Version 1.4.0 (2026-07-21): that road-following route is now
available, via OpenRouteService (see
sba_resolve/core/services/route_service.py and
ui/workers/route_worker.py) - main_window.py fetches it on a
background thread (real network call) after set_media() and calls
set_route() with the result. This is entirely optional and
additive: set_media()'s straight pin-to-pin line is drawn
immediately as before and stays as the fallback if no
OpenRouteService API key is configured, or if the fetch fails for
any reason (main_window.py reports the specific reason via the
status bar; this widget itself doesn't need to know why a route
never arrived).
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
    var currentRouteLayer = null;

    function updateMapData(pins) {

        currentLayers.forEach(function(layer) {
            map.removeLayer(layer);
        });
        currentLayers = [];

        if (currentRouteLayer !== null) {
            map.removeLayer(currentRouteLayer);
            currentRouteLayer = null;
        }

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
            currentRouteLayer = L.polyline(routePoints, {
                color: '#4f8cff',
                weight: 4,
                opacity: 0.8
            }).addTo(map);
        }

        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [30, 30] });
        }
    }

    function updateRoute(routePoints) {
        // Replaces ONLY the straight-line route drawn by
        // updateMapData() with a real, road-following route (see
        // MapWidget.set_route()) - pins/bounds are untouched, since
        // this is called later, after an async route fetch
        // completes, once updateMapData() has already drawn
        // whatever pins currently exist.

        if (currentRouteLayer !== null) {
            map.removeLayer(currentRouteLayer);
            currentRouteLayer = null;
        }

        if (routePoints.length > 1) {
            currentRouteLayer = L.polyline(routePoints, {
                color: '#4f8cff',
                weight: 4,
                opacity: 0.8
            }).addTo(map);
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
        self._pending_route = None

        self.loadFinished.connect(self._on_load_finished)
        self.setHtml(_MAP_HTML)

    def _on_load_finished(self, ok: bool) -> None:
        self._loaded = ok
        if ok and self._pending_media is not None:
            self._push_update(self._pending_media)
            self._pending_media = None
        if ok and self._pending_route is not None:
            self._push_route(self._pending_route)
            self._pending_route = None

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

    def set_route(self, route_points: list[tuple[float, float]]) -> None:
        """
        Replaces the straight pin-to-pin line (drawn by set_media())
        with a real, road-following route - called by main_window.py
        once an async OpenRouteService fetch succeeds (see
        route_service.py / route_worker.py). Safe to call before the
        page has finished loading (queues like set_media() does) or
        with an empty/short list (clears back to no route line;
        JS-side updateRoute() already no-ops for <2 points).

        Does NOT touch pins or map bounds - only the route line
        layer.
        """

        if not self._loaded:
            self._pending_route = list(route_points)
            return

        self._push_route(route_points)

    def _push_route(self, route_points: list[tuple[float, float]]) -> None:
        points_json = json.dumps(
            [[lat, lon] for lat, lon in route_points]
        )
        self.page().runJavaScript(f"updateRoute({points_json});")