"""
SBA AI Studio
Capture Time Service

Public API for resolving capture timestamps.

This service hides the parser registry and resolver implementation from
the rest of the application.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from sba_resolve.capture_time.resolver import CaptureTimeResolver


class CaptureTimeService:
    """
    High-level service used throughout SBA AI Studio.

    Components such as MediaFile, MediaLibrary, Timeline Builder and
    Project Scanner should use this service instead of interacting with
    parsers directly.
    """

    def __init__(self) -> None:
        self._resolver = CaptureTimeResolver()

    def resolve(self, metadata: dict[str, Any]):
        """
        Resolve the best capture timestamp from metadata.
        """
        return self._resolver.resolve(metadata)

    @lru_cache(maxsize=4096)
    def resolve_from_hash(self, metadata_hash: str, metadata_json: str):
        """
        Cached resolution for repeated metadata.

        The caller is responsible for supplying a stable hash together
        with a serialized metadata representation.
        """
        import json

        metadata = json.loads(metadata_json)
        return self.resolve(metadata)

    def parser_count(self) -> int:
        """
        Return the number of registered parsers.
        """
        return len(self._resolver._parsers)

    def reload(self) -> None:
        """
        Reload all available parsers.
        """
        self._resolver = CaptureTimeResolver()