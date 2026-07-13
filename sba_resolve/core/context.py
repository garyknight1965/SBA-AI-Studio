"""
============================================================
SBA AI Studio
Resolve Context
Version : Sprint 2 RC1
============================================================
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolveReport:
    """
    Runtime statistics collected during connector execution.
    """

    project_created: bool = False

    bins_created: int = 0
    bins_existing: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ResolveContext:
    """
    Shared runtime state passed to every Resolve command.
    """

    # ---------------------------------------------------------
    # Resolve
    # ---------------------------------------------------------

    resolve: Any = None
    project: Any = None

    media_pool: Any = None
    root_folder: Any = None

    timeline: Any = None

    # ---------------------------------------------------------
    # SBA Project
    # ---------------------------------------------------------

    project_data: dict = field(default_factory=dict)

    # ---------------------------------------------------------
    # Execution Report
    # ---------------------------------------------------------

    report: ResolveReport = field(default_factory=ResolveReport)