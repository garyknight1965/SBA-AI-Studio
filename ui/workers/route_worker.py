"""
============================================================
SBA AI Studio
Route Worker
Backlog: Real road-following map routing
Version : 1.0.0
============================================================

Runs RouteService.get_route() on a background thread - it makes a
real network call to OpenRouteService, same reasoning as
LocationGroupingWorker/ReverseGeocoder.

run() is deliberately plain, synchronous Python calling the
already-regression-tested RouteService - it can be called directly
(bypassing QThread.start()) for testing without spinning up a real
thread or making real network calls (with a fake service injected).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sba_resolve.core.services.route_service import (
    RouteService,
    RouteServiceError,
)


class RouteWorker(QThread):

    succeeded = Signal(list)

    failed = Signal(str)

    def __init__(
        self,
        waypoints: list[tuple[float, float]],
        api_key: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.waypoints = list(waypoints)
        self.api_key = api_key

    def run(self) -> None:

        try:
            route = RouteService(api_key=self.api_key).get_route(
                self.waypoints
            )

        except RouteServiceError as exc:
            self.failed.emit(str(exc))
            return

        except Exception as exc:
            self.failed.emit(f"Unexpected error: {exc}")
            return

        self.succeeded.emit(route)