"""
============================================================
SBA AI Studio
Location Grouper
Version : 1.0.0
Sprint  : ML-038
============================================================

Groups scanned media by place name (Core Module 2 - Media
Organisation - "group by location" from the product handover),
using ReverseGeocoder to turn each clip's GPS coordinates into a
place name.

IMPORTANT - this makes real network calls (via ReverseGeocoder,
rate-limited to ~1 request/second per distinct ~1km location
cluster). Following the same pattern already used for YouTube
metadata generation, this must be invoked from a background
thread (e.g. a QThread worker), NEVER from
WorkspaceController.scan_project() or anywhere else that runs
synchronously on the GUI thread - that would freeze the UI for
however long geocoding takes. This class itself has no threading
of its own; the caller is responsible for running it off the main
thread.

Clips with no GPS data, or whose coordinates can't be resolved to
a place (offline, rate-limited, bad response), are grouped under
LocationGroup(place_name=UNKNOWN_LOCATION) rather than dropped.
"""

from __future__ import annotations

from typing import Iterable

from sba_resolve.core.models.location_group import (
    UNKNOWN_LOCATION,
    LocationGroup,
)
from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.services.reverse_geocoder import ReverseGeocoder


class LocationGrouper:
    """
    Groups media files by reverse-geocoded place name.
    """

    def __init__(self, geocoder: ReverseGeocoder | None = None) -> None:
        self.geocoder = geocoder or ReverseGeocoder()

    def group(
        self, media_files: Iterable[MediaFile]
    ) -> list[LocationGroup]:
        """
        Returns LocationGroups sorted alphabetically by place
        name, with UNKNOWN_LOCATION (if present) always last -
        so a UI listing these reads real places first, with the
        "couldn't identify this" bucket at the end rather than
        interleaved alphabetically among real names.
        """

        clips_by_place: dict[str, list[MediaFile]] = {}

        for media in media_files:

            place = self.geocoder.place_name(
                getattr(media, "gps_latitude", None),
                getattr(media, "gps_longitude", None),
            )

            place = place or UNKNOWN_LOCATION

            clips_by_place.setdefault(place, []).append(media)

        known_places = sorted(
            place for place in clips_by_place if place != UNKNOWN_LOCATION
        )

        ordered_places = known_places + (
            [UNKNOWN_LOCATION] if UNKNOWN_LOCATION in clips_by_place else []
        )

        return [
            LocationGroup(place_name=place, clips=clips_by_place[place])
            for place in ordered_places
        ]
