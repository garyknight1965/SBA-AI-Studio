"""
============================================================
SBA AI Studio
Bootstrap
============================================================
"""

import sys
from pathlib import Path


def bootstrap() -> Path:
    """
    Locate the SBA AI Studio project root automatically.
    """

    # bootstrap.py lives in:
    # <project>/resolve/bootstrap.py
    project_root = Path(__file__).resolve().parent.parent

    if not project_root.exists():
        raise FileNotFoundError(
            f"Project root not found: {project_root}"
        )

    root = str(project_root)

    if root not in sys.path:
        sys.path.insert(0, root)

    return project_root