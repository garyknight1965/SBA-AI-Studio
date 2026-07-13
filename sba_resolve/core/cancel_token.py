"""
SBA AI Studio

Cancellation Token
ML-006A
"""

from __future__ import annotations


class CancellationToken:
    """
    Simple cancellation token used by long-running operations.
    """

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled