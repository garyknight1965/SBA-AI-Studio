"""
SBA AI Studio
Filename Parser Base Classes

Defines the interface used by all filename parsers.

Author: SBA AI Studio
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class BaseFilenameParser(ABC):
    """
    Base class for filename parsers.
    """

    @abstractmethod
    def can_parse(self, filename: str) -> bool:
        """
        Returns True if this parser supports the filename.
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, filename: str) -> datetime | None:
        """
        Extracts a timestamp from the filename.

        Returns
        -------
        datetime | None
        """
        raise NotImplementedError