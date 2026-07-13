\
"""
SBA AI Studio
Project Doctor
Architecture Sprint AS-006

Read-only project health checker.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

IGNORE = {
    ".git",
    "__pycache__",
    ".venv",
    ".venv310",
    ".venv312",
    "archive",
    "logs",
}

CHECK_PATHS = [
    "start.py",
    "controllers",
    "ui",
    "sba_resolve",
]


def skip(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)


def count_python(root: Path) -> int:
    return len([p for p in root.rglob("*.py") if not skip(p)])


def has_legacy_core(root: Path) -> bool:
    return (root / "core").exists()


def temp_files(root: Path):
    bad = []
    for p in root.rglob("*.py"):
        if skip(p):
            continue
        if ";" in p.name or p.name.endswith("tmp.py"):
            bad.append(p.relative_to(root))
    return bad


def package_inits(root: Path):
    missing = []
    for folder in root.rglob("*"):
        if skip(folder) or not folder.is_dir():
            continue
        if any(x.suffix == ".py" for x in folder.iterdir()):
            init = folder / "__init__.py"
            if not init.exists():
                missing.append(init.relative_to(root))
    return missing


def can_import_start(root: Path):
    return (root / "start.py").exists()


def health_score(legacy: bool, temps: int, missing: int):
    score = 100
    if legacy:
        score -= 3
    score -= temps * 2
    score -= missing
    return max(score, 0)


def main():
    root = Path.cwd()

    legacy = has_legacy_core(root)
    temps = temp_files(root)
    missing = package_inits(root)
    score = health_score(legacy, len(temps), len(missing))

    print("=" * 72)
    print("SBA AI Studio Doctor")
    print("=" * 72)
    print(f"Python files : {count_python(root)}")
    print(f"Entry point  : {'PASS' if can_import_start(root) else 'FAIL'}")
    print(f"Legacy core  : {'FOUND' if legacy else 'PASS'}")
    print(f"Temp files   : {len(temps)}")
    print(f"Missing __init__.py : {len(missing)}")
    print()

    if temps:
        print("Temporary / suspicious files")
        print("-" * 72)
        for t in temps:
            print(t)
        print()

    if missing:
        print("Missing __init__.py")
        print("-" * 72)
        for m in missing:
            print(m)
        print()

    print("=" * 72)
    print(f"PROJECT HEALTH : {score}%")
    print("=" * 72)
    print("Read-only check. No files were modified.")


if __name__ == "__main__":
    main()
