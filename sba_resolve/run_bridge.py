"""
============================================================
SBA AI Studio
Resolve Bridge
Version : M2-002
============================================================

Bridge launcher.

This module is imported by start.py.
It is never executed directly.
"""

import json
from pathlib import Path

from sba_resolve.bootstrap import bootstrap
from sba_resolve.connector import ResolveConnector


def main():
    """
    Launch the Resolve connector.
    """

    # ---------------------------------------------------------
    # Bootstrap
    # ---------------------------------------------------------

    project_root = bootstrap()

    # ---------------------------------------------------------
    # Load bridge project
    # ---------------------------------------------------------

    bridge_file = (
        Path(project_root)
        / "projects"
        / "bridge_project.json"
    )

    print("=" * 60)
    print("SBA Resolve Bridge")
    print("=" * 60)
    print()

    print("Loading Bridge Project...")

    with open(bridge_file, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    print(f"Project : {project_data['project_name']}")
    print()

    # ---------------------------------------------------------
    # Launch connector
    # ---------------------------------------------------------

    connector = ResolveConnector(project_data)

    connector.run()

    print()
    print("=" * 60)
    print("Bridge Finished")
    print("=" * 60)


if __name__ == "__main__":
    main()