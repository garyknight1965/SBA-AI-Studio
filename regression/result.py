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

    # True when this test was not run because a required environment
    # dependency (e.g. a native GUI library) was not available - this is
    # distinct from a real application failure and should not be counted
    # as one.
    blocked: bool = False

    @property
    def status(self) -> str:

        if self.blocked:
            return "BLOCKED"

        return "PASS" if self.success else "FAIL"

    @property
    def colour(self) -> str:

        if self.blocked:
            return "#f0ad4e"

        return "#28a745" if self.success else "#dc3545"

    def __str__(self) -> str:

        return (
            f"{self.name:<35}"
            f"{self.status}"
            f" ({self.duration:.3f}s)"
        )