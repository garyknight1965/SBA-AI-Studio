"""
============================================================
SBA AI Studio
Regression Base Test
Version : 1.1.0
Sprint : R2
============================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter

from regression.result import RegressionResult


class BaseRegressionTest(ABC):
    """
    Base class for every regression test.
    """

    name = "Unnamed Test"
    category = "General"
    description = ""

    def execute(self) -> RegressionResult:

        start = perf_counter()

        try:

            self.run()

            return RegressionResult(
                name=self.name,
                category=self.category,
                success=True,
                duration=perf_counter() - start,
                message="",
            )

        except Exception as ex:

            return RegressionResult(
                name=self.name,
                category=self.category,
                success=False,
                duration=perf_counter() - start,
                message=str(ex),
            )

    @abstractmethod
    def run(self) -> None:
        """
        Execute the regression test.
        """
        raise NotImplementedError