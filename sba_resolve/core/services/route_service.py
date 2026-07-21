"""
============================================================
SBA AI Studio
Route Service (OpenRouteService)
Backlog: Real road-following map routing
Version : 1.0.0
============================================================

Fetches a real, road-following route between GPS waypoints via
OpenRouteService's Directions API (driving-car profile - ORS has
no dedicated motorcycle profile, and driving-car follows the same
public road network a motorcycle would use).

Uses only the standard library (urllib), matching the project's
established no-new-dependency style for external API clients (see
ollama_client.py, groq_provider.py).

Confirmed request/response format (verified via ORS's own
documentation/community examples before writing this):
    POST https://api.openrouteservice.org/v2/directions/driving-car/geojson
    Header: Authorization: <raw api key, no "Bearer" prefix>
    Body:   {"coordinates": [[lon, lat], [lon, lat], ...]}
    Response: GeoJSON FeatureCollection - the route's actual
        coordinate sequence is at
        response["features"][0]["geometry"]["coordinates"]
        (each a [lon, lat] pair - the "geojson" endpoint variant
        was deliberately chosen over the plain endpoint specifically
        to get real coordinates back instead of an encoded polyline
        string, avoiding the need for a polyline-decoding
        implementation entirely).

This module never silently swallows a failure - every failure path
raises RouteServiceError with a specific, actionable reason. The
CALLER (RouteWorker / main_window.py) decides what to do with that
failure - in this app's case, falling back to the already-working
straight-line pin-to-pin display (MapWidget's original behaviour),
with the specific reason shown in the status bar rather than a
silent, unexplained fallback.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
)


class RouteServiceError(RuntimeError):
    """
    Raised when a route can't be fetched - missing/rejected API
    key, network failure, too many/invalid waypoints, or an
    unparseable response. Always a clear, specific message rather
    than a bare urllib traceback.
    """


class RouteService:
    """
    Thin client for ORS's Directions API. One public method:
    get_route(waypoints) -> list of (lat, lon) tuples tracing the
    real road route through every waypoint, in order.
    """

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise RouteServiceError(
                "No OpenRouteService API key was provided. Add one "
                "in Settings -> Map, or get a free key at "
                "openrouteservice.org."
            )
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def get_route(
        self, waypoints: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """
        waypoints: ordered list of (lat, lon) tuples - at least 2
        required (a route needs a start and an end).

        Returns the full road-following coordinate sequence as
        (lat, lon) tuples, in travel order.

        Raises RouteServiceError (never a bare urllib/json
        exception) if there are fewer than 2 waypoints, the key is
        rejected, ORS returns an error (e.g. too many waypoints for
        the free tier, a waypoint ORS can't snap to a road), the
        service is unreachable, or the response can't be parsed.
        """

        if len(waypoints) < 2:
            raise RouteServiceError(
                f"A route needs at least 2 waypoints, got "
                f"{len(waypoints)}."
            )

        # ORS wants [longitude, latitude] order - the reverse of
        # this app's (lat, lon) convention (MediaFile.gps_latitude/
        # gps_longitude, MapWidget's pin dicts).
        coordinates = [[lon, lat] for lat, lon in waypoints]

        payload = json.dumps({"coordinates": coordinates}).encode(
            "utf-8"
        )

        request = urllib.request.Request(
            DIRECTIONS_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": self.api_key,
                "Accept": "application/geo+json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                pass
            if exc.code == 403:
                raise RouteServiceError(
                    "OpenRouteService rejected the API key (HTTP "
                    "403). Check the key in Settings -> Map, or "
                    "generate a new one at openrouteservice.org."
                ) from exc
            if exc.code == 429:
                raise RouteServiceError(
                    "OpenRouteService's free-tier rate limit was "
                    "hit (HTTP 429). Wait a moment and try again."
                ) from exc
            raise RouteServiceError(
                f"OpenRouteService returned an error (HTTP "
                f"{exc.code}). Details: {body[:300]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RouteServiceError(
                f"Could not reach OpenRouteService. Check your "
                f"internet connection. Details: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise RouteServiceError(
                f"OpenRouteService did not respond within "
                f"{self.timeout_seconds:.0f}s."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RouteServiceError(
                f"OpenRouteService's response wasn't valid JSON: "
                f"{raw[:200]!r}"
            ) from exc

        features = data.get("features")
        if not isinstance(features, list) or not features:
            raise RouteServiceError(
                f"OpenRouteService's response had no route features: "
                f"{data!r}"
            )

        geometry = features[0].get("geometry", {})
        route_coordinates = geometry.get("coordinates")

        if not isinstance(route_coordinates, list) or not route_coordinates:
            raise RouteServiceError(
                f"OpenRouteService's response had no route "
                f"coordinates: {data!r}"
            )

        # Flip back from ORS's [lon, lat] to this app's (lat, lon).
        return [
            (point[1], point[0])
            for point in route_coordinates
            if isinstance(point, list) and len(point) >= 2
        ]