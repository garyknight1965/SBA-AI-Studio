\
"""
SBA AI Studio
Project Architect v2
Architecture Sprint AS-003

Read-only migration planner.
This tool NEVER changes your project.
"""

from __future__ import annotations

from pathlib import Path
from collections import defaultdict

IGNORE = {
    ".git", "__pycache__", ".venv", ".venv310", ".venv312",
    "logs", "archive"
}

KEEP_PREFIXES = (
    "sba_resolve/core",
    "ui/windows",
    "ui/widgets",
    "controllers",
)

def skip(path: Path) -> bool:
    return any(p in IGNORE for p in path.parts)

def py_files(root: Path):
    return [p for p in root.rglob("*.py") if not skip(p)]

def action(root: Path, file: Path):
    rel = file.relative_to(root).as_posix()
    name = file.name

    if name == "__init__.py":
        return "KEEP"

    if rel == "controllers/workspace_controller1.py":
        return "ARCHIVE"

    if rel == "ui/main_window.py":
        return "ARCHIVE"

    if name.endswith("tmp.py") or ";" in name:
        return "DELETE?"

    if rel.startswith("core/"):
        return "LEGACY"

    if rel.startswith(KEEP_PREFIXES):
        return "KEEP"

    return "VERIFY"

def main():
    root = Path.cwd()
    buckets = defaultdict(list)

    for f in sorted(py_files(root)):
        buckets[action(root, f)].append(f.relative_to(root).as_posix())

    print("=" * 72)
    print("SBA AI Studio - Migration Plan")
    print("=" * 72)

    order = ("KEEP", "LEGACY", "VERIFY", "ARCHIVE", "DELETE?")

    for section in order:
        print(f"\n{section}")
        print("-" * 72)
        if not buckets[section]:
            print("None")
        else:
            for item in buckets[section]:
                print(item)

    print("\nSummary")
    print("-" * 72)
    for section in order:
        print(f"{section:9}: {len(buckets[section])}")

    print("\nThis tool did not modify any files.")

if __name__ == "__main__":
    main()
