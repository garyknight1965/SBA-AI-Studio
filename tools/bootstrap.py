"""
============================================================
SBA AI Studio Bootstrapper
Version : 2.0
Author  : Gary Knight
============================================================
"""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------
# Folder Structure
# ------------------------------------------------------------

FOLDERS = [
    "assets",
    "bridge",
    "core",
    "docs",
    "logs",
    "projects",
    "tests",
    "tools",
    "ui",

    "archive",
    "archive/diagnostics",
    "archive/experiments",
    "archive/old_tests",

    "resolve",
    "resolve/commands",
]

# ------------------------------------------------------------
# Python Packages
# ------------------------------------------------------------

PACKAGES = [
    "bridge",
    "core",
    "resolve",
    "resolve/commands",
    "tests",
    "tools",
    "ui",
]

# ------------------------------------------------------------
# Project Files
# ------------------------------------------------------------

FILES = {
    "README.md": "# SBA AI Studio\n",
    "requirements.txt": "",
    ".gitignore": """__pycache__/
*.pyc
.venv/
logs/
""",
    "pyproject.toml": """
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sba-ai-studio"
version = "0.2.0"
requires-python = ">=3.10"
"""
}

# ------------------------------------------------------------
# Files to archive
# ------------------------------------------------------------

ARCHIVE = {

    "tools": [
        "dll_test.py",
        "import_test.py",
        "resolve_test.py",
        "resolve310_test.py",
        "resolve_direct.py",
        "resolve_diagnostic.py",
    ],

    "resolve": [
        "common.py"
    ]
}

print("=" * 60)
print(" SBA AI Studio Bootstrapper")
print("=" * 60)
print()

print("Project Root")
print(ROOT)
print()

# ------------------------------------------------------------
# Create folders
# ------------------------------------------------------------

print("Verifying folders...")

for folder in FOLDERS:

    path = ROOT / folder

    path.mkdir(parents=True, exist_ok=True)

    print(f"[ OK ] {folder}")

print()

# ------------------------------------------------------------
# Create packages
# ------------------------------------------------------------

print("Verifying packages...")

for package in PACKAGES:

    init = ROOT / package / "__init__.py"

    if not init.exists():
        init.write_text("", encoding="utf-8")

    print(f"[ OK ] {package}")

print()

# ------------------------------------------------------------
# Project files
# ------------------------------------------------------------

print("Verifying project files...")

for filename, content in FILES.items():

    file = ROOT / filename

    if not file.exists():

        file.write_text(
            content.strip() + "\n",
            encoding="utf-8"
        )

    print(f"[ OK ] {filename}")

print()

# ------------------------------------------------------------
# Archive obsolete files
# ------------------------------------------------------------

print("Archiving obsolete files...")

archive_root = ROOT / "archive"

for folder, files in ARCHIVE.items():

    source_folder = ROOT / folder

    destination = archive_root / folder

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    for filename in files:

        source = source_folder / filename

        if source.exists():

            target = destination / filename

            if not target.exists():

                shutil.move(
                    str(source),
                    str(target)
                )

                print(f"[MOVE] {folder}/{filename}")

            else:

                print(f"[SKIP] {folder}/{filename}")

print()

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print("=" * 60)
print(" Bootstrap Complete")
print("=" * 60)

print()

print("Next step:")
print("    python -m tools.bootstrap")