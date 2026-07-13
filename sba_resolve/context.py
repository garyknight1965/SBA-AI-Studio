"""
============================================================
SBA AI Studio
Resolve Context
Version : 3.1.0 RC1
============================================================
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolveReport:
    """
    Runtime statistics collected during connector execution.
    """

    # Project
    project_created: bool = False

    # Bins
    bins_created: int = 0
    bins_existing: int = 0

    # Media
    media_imported: int = 0
    media_skipped: int = 0
    media_missing: int = 0
    media_failed: int = 0

    # Diagnostics
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ResolveContext:
    """
    Shared runtime state passed to every Resolve command.
    """

    # Resolve
    resolve: Any = None
    project: Any = None
    media_pool: Any = None
    root_folder: Any = None
    timeline: Any = None

    # Bridge project
    project_data: dict = field(default_factory=dict)

    # Execution report
    report: ResolveReport = field(default_factory=ResolveReport)
