"""
============================================================
SBA AI Studio
Planning Pipeline
ML-011D
Version : 1.0.0 Alpha
============================================================

Executes PlanningStep components in sequence.
"""

from __future__ import annotations

from typing import Any

from sba_resolve.core.services.planning_step import PlanningStep


class PlanningPipeline:
    """
    Executes a sequence of PlanningStep objects.
    """

    def __init__(self) -> None:

        self._steps: list[PlanningStep] = []

    def add_step(
        self,
        step: PlanningStep,
    ) -> None:

        self._steps.append(step)

    def execute(
        self,
        data: Any,
    ) -> Any:

        result = data

        for step in self._steps:

            result = step.execute(result)

        return result

    @property
    def step_count(self) -> int:

        return len(self._steps)

    def clear(self) -> None:

        self._steps.clear()

    def __len__(self) -> int:

        return len(self._steps)

    def __iter__(self):

        return iter(self._steps)