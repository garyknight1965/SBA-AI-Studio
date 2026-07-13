"""
============================================================
SBA AI Studio
Regression Result
Version : 1.0.0
Sprint : R2
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RegressionResult:
    """
    Result returned by every regression test.
    """

    name: str

    category: str

    success: bool

    duration: float

    message: str = ""

    details: str = ""

    @property
    def status(self) -> str:

        return "PASS" if self.success else "FAIL"

    @property
    def colour(self) -> str:

        return "#28a745" if self.success else "#dc3545"

    def __str__(self) -> str:

        return (
            f"{self.name:<35}"
            f"{self.status}"
            f" ({self.duration:.3f}s)"
        )