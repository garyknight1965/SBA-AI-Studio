"""
============================================================
SBA AI Studio
Planning Step
ML-011C
Version : 1.0.0 Alpha
============================================================

Base class for every Planning Engine step.

Each planning component receives input data,
transforms it, and returns the result for the
next step in the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PlanningStep(ABC):
    """
    Base class for every Planning Engine component.
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """
        Execute one planning step.

        Parameters
        ----------
        data
            Input from the previous planning step.

        Returns
        -------
        Any
            Output for the next planning step.
        """
        raise NotImplementedError

    def __call__(self, data: Any) -> Any:
        return self.execute(data)

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__