"""
============================================================
SBA AI Studio
Regression Registry
Version : 1.0.0
Sprint : R2
============================================================

Automatically discovers every regression test.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from regression.base_test import BaseRegressionTest


class RegressionRegistry:
    """
    Discovers every regression test automatically.
    """

    def __init__(self):

        self.tests = []

        self.discover()

    def discover(self) -> None:

        self.tests.clear()

        import regression.tests

        for _, module_name, _ in pkgutil.iter_modules(
            regression.tests.__path__
        ):

            module = importlib.import_module(
                f"regression.tests.{module_name}"
            )

            for _, obj in inspect.getmembers(
                module,
                inspect.isclass,
            ):

                if (
                    issubclass(obj, BaseRegressionTest)
                    and obj is not BaseRegressionTest
                ):

                    self.tests.append(obj())

        self.tests.sort(
            key=lambda t: (
                t.category,
                t.name,
            )
        )