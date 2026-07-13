"""
============================================================
SBA AI Studio
Resolve Timeline API Inspector
RES-006B
============================================================
"""

import DaVinciResolveScript as bmd


def main():
    resolve = bmd.scriptapp("Resolve")

    if resolve is None:
        print("Unable to connect to Resolve.")
        return

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()

    if project is None:
        print("No project open.")
        return

    timeline = project.GetCurrentTimeline()

    if timeline is None:
        print("No timeline open.")
        return

    print("=" * 60)
    print("Timeline API")
    print("=" * 60)

    methods = sorted(
        name
        for name in dir(timeline)
        if not name.startswith("_")
    )

    for method in methods:
        print(method)


if __name__ == "__main__":
    main()