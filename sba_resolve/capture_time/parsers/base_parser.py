"""
SBA AI Studio
Capture Time Parser Interface

All capture time parsers must inherit from BaseCaptureTimeParser.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCaptureTimeParser(ABC):
    """
    Base class for all capture time parsers.
    """

    #: Human-readable parser name.
    name: str = "Base Parser"

    #: Priority used when two parsers return equal confidence.
    priority: int = 100

    @abstractmethod
    def supports(self, metadata: dict[str, Any]) -> bool:
        """
        Return True if this parser can interpret the supplied metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, metadata: dict[str, Any]):
        """
        Parse metadata and return a TimestampCandidate.

        Returns:
            TimestampCandidate | None
        """
        raise NotImplementedError