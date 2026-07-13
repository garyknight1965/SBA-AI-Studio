\
"""
SBA AI Studio
Safe Migration Engine
Architecture Sprint AS-005

This tool NEVER deletes files.
It only archives files that have been explicitly approved.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ARCHIVE_LIST = [
    "controllers/workspace_controller1.py",
    "ui/main_window.py",
]

DELETE_REVIEW = [
    "sba_resolve/manager/media_pool_manager;.py",
    "sba_resolve/manager/media_pool_managertmp.py",
]


def main() -> None:
    root = Path.cwd()

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_root = root / "archive" / stamp
    archive_root.mkdir(parents=True, exist_ok=True)

    moved = []

    print("=" * 72)
    print("SBA AI Studio - Safe Migration Engine")
    print("=" * 72)
    print(f"Archive folder : {archive_root}")
    print()

    for rel in ARCHIVE_LIST:
        src = root / rel
        if not src.exists():
            print(f"SKIP : {rel} (not found)")
            continue

        dst = archive_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src), str(dst))
        moved.append(rel)
        print(f"MOVED: {rel}")

    print("\nReview-only candidates (NOT deleted)")
    print("-" * 72)
    for rel in DELETE_REVIEW:
        p = root / rel
        state = "FOUND" if p.exists() else "NOT FOUND"
        print(f"{state:10} {rel}")

    report = archive_root / "migration_report.txt"
    with report.open("w", encoding="utf-8") as f:
        f.write("SBA AI Studio Migration Report\n")
        f.write("=" * 40 + "\n\n")
        f.write("Archived files:\n")
        for item in moved:
            f.write(f" - {item}\n")
        f.write("\nReview-only:\n")
        for item in DELETE_REVIEW:
            f.write(f" - {item}\n")

    print("\nMigration complete.")
    print(f"Archived : {len(moved)}")
    print("Deleted  : 0")
    print(f"Report   : {report}")


if __name__ == "__main__":
    main()
