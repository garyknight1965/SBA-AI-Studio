"""
SBA AI Studio
Capture Time Parser Registry

Automatically discovers and instantiates all parser implementations.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class ParserRegistry:
    """
    Discovers all parser classes that inherit from BaseCaptureTimeParser.
    """

    def __init__(self):
        self._parsers = []
        self.discover()

    def discover(self) -> None:
        """
        Discover parser classes in this package.
        """

        package = importlib.import_module(
            "sba_resolve.capture_time.parsers"
        )

        self._parsers.clear()

        for _, module_name, _ in pkgutil.iter_modules(package.__path__):

            if module_name in ("base_parser", "registry"):
                continue

            module = importlib.import_module(
                f"sba_resolve.capture_time.parsers.{module_name}"
            )

            for _, obj in inspect.getmembers(module, inspect.isclass):

                if (
                    issubclass(obj, BaseCaptureTimeParser)
                    and obj is not BaseCaptureTimeParser
                ):
                    self._parsers.append(obj())

        self._parsers.sort(key=lambda p: p.priority)

    @property
    def parsers(self):
        return list(self._parsers)