"""
SBA AI Studio
Project Cleanup & Structure Migration
Version 4.0.0

Run from the project root:

    python tools/restructure_project.py

This script:
- Creates the new core folders
- Creates missing __init__.py files
- Moves Project Scanner into the new location (if required)
- Reports duplicate manager files
- Does NOT delete anything automatically.
"""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

NEW_FOLDERS = [
    "sba_resolve/core/models",
    "sba_resolve/core/scanner",
    "sba_resolve/core/metadata",
    "sba_resolve/core/database",
    "sba_resolve/core/logging",
    "sba_resolve/core/services",
]

MOVE_FILES = [
    (
        "project_scanner_ml001.py",
        "sba_resolve/core/scanner/project_scanner.py",
    ),
]

CHECK_DUPLICATES = [
    "media_pool_manager.py",
    "connector.py",
    "context.py",
]


def ensure_structure():
    print("\nCreating folder structure...")
    for folder in NEW_FOLDERS:
        p = ROOT / folder
        p.mkdir(parents=True, exist_ok=True)
        init = p / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")
        print(f"[OK ] {folder}")


def move_known_files():
    print("\nMoving known files...")
    for src, dst in MOVE_FILES:
        s = ROOT / src
        d = ROOT / dst
        if s.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
            print(f"[MOVE] {src} -> {dst}")


def find_duplicates():
    print("\nDuplicate report...")
    for filename in CHECK_DUPLICATES:
        matches = list(ROOT.rglob(filename))
        if len(matches) > 1:
            print(f"\n[DUPLICATE] {filename}")
            for m in matches:
                print("   ", m.relative_to(ROOT))


def find_debug_files():
    print("\nTemporary files...")
    patterns = (
        "*_debug.py",
        "*_mv*.py",
        "*_rc*.py",
        "*_ml*.py",
    )
    found = False
    for pattern in patterns:
        for f in ROOT.rglob(pattern):
            found = True
            print("   ", f.relative_to(ROOT))
    if not found:
        print("None found.")


def main():
    print("=" * 60)
    print("SBA AI Studio Project Cleanup")
    print("=" * 60)

    ensure_structure()
    move_known_files()
    find_duplicates()
    find_debug_files()

    print("\nNo files were deleted.")
    print("Review the duplicate and temporary file reports")
    print("before removing obsolete files.")

if __name__ == "__main__":
    main()
