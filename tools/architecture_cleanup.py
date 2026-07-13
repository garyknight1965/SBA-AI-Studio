\
"""
SBA AI Studio - Architecture Cleanup Tool
Phase 1 (Safe Audit)

This version NEVER modifies your project.
It scans the project and produces a report.
"""

from __future__ import annotations

from pathlib import Path
from collections import defaultdict

REQUIRED_PACKAGES = [
    "ui",
    "ui/widgets",
    "ui/windows",
    "controllers",
    "sba_resolve/core",
    "sba_resolve/core/models",
    "sba_resolve/core/library",
    "sba_resolve/core/metadata",
    "sba_resolve/core/scanner",
]

IGNORE = {
    ".git",
    "__pycache__",
    ".venv",
    ".venv310",
    ".venv312",
    "archive",
    "logs",
}


def should_skip(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)


def scan_python(root: Path):
    return [
        p for p in root.rglob("*.py")
        if not should_skip(p)
    ]


def duplicate_names(files):
    d = defaultdict(list)
    for f in files:
        d[f.name].append(f)
    return {k: v for k, v in d.items() if len(v) > 1}


def missing_init(root: Path):
    missing = []
    for rel in REQUIRED_PACKAGES:
        folder = root / rel
        if folder.exists():
            init = folder / "__init__.py"
            if not init.exists():
                missing.append(init)
    return missing


def legacy_core(root: Path):
    folder = root / "core"
    return folder.exists()


def main():
    root = Path.cwd()

    files = scan_python(root)

    print("=" * 70)
    print("SBA AI Studio - Architecture Audit")
    print("=" * 70)
    print(f"Root          : {root}")
    print(f"Python files  : {len(files)}")
    print()

    print("Duplicate filenames")
    print("-" * 70)
    dups = duplicate_names(files)
    if not dups:
        print("None")
    else:
        for name, paths in sorted(dups.items()):
            print(name)
            for p in paths:
                print(f"   {p.relative_to(root)}")
    print()

    print("Missing __init__.py")
    print("-" * 70)
    miss = missing_init(root)
    if not miss:
        print("None")
    else:
        for p in miss:
            print(p.relative_to(root))
    print()

    print("Legacy architecture")
    print("-" * 70)
    if legacy_core(root):
        print("WARNING: legacy 'core/' folder found.")
    else:
        print("OK")

    print()
    print("Audit complete.")
    print("No files were modified.")

if __name__ == "__main__":
    main()
