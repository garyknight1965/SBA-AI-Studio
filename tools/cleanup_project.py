from pathlib import Path
import shutil

ROOT = Path(r"D:\Projects\SBA-AI-Studio")

print("=" * 70)
print(" SBA AI Studio Project Cleanup")
print("=" * 70)
print()

# ----------------------------------------------------
# Folders
# ----------------------------------------------------

folders = [
    "assets",
    "archive",
    "archive/tests",
    "archive/experiments",
    "bridge",
    "core",
    "logs",
    "projects",
    "resolve",
    "tests",
    "tools",
    "ui",
]

for folder in folders:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

print("✓ Folder structure verified")

# ----------------------------------------------------
# __init__.py
# ----------------------------------------------------

packages = [
    "bridge",
    "core",
    "resolve",
    "tests",
    "tools",
    "ui",
]

for package in packages:

    init = ROOT / package / "__init__.py"

    if not init.exists():
        init.write_text("", encoding="utf-8")

print("✓ Python packages verified")

# ----------------------------------------------------
# Archive old test scripts
# ----------------------------------------------------

archive = ROOT / "archive" / "tests"

test_files = [
    "test_metadata.py",
    "test_resolve_import.py",
    "test_fusionscript.py",
    "resolve_direct.py",
    "resolve_diagnostic.py",
    "resolve310_test.py",
]

for filename in test_files:

    source = ROOT / "tools" / filename

    if source.exists():

        destination = archive / filename

        shutil.move(source, destination)

        print(f"Archived: {filename}")

print("✓ Temporary test files archived")

# ----------------------------------------------------
# README
# ----------------------------------------------------

readme = ROOT / "README.md"

if not readme.exists():

    readme.write_text(
"""# SBA AI Studio

AI Assisted DaVinci Resolve Workflow

Author: Gary Knight
Channel: Scottish Biker Abroad

""",
encoding="utf-8"
)

print("✓ README verified")

# ----------------------------------------------------
# requirements.txt
# ----------------------------------------------------

requirements = ROOT / "requirements.txt"

if not requirements.exists():

    requirements.write_text(
"""PySide6
opencv-python
exiftool
""",
encoding="utf-8"
)

print("✓ requirements.txt verified")

# ----------------------------------------------------
# .gitignore
# ----------------------------------------------------

gitignore = ROOT / ".gitignore"

if not gitignore.exists():

    gitignore.write_text(
"""
# Python
__pycache__/
*.pyc

# Virtual Environments
.venv/
.venv310/
.venv312/

# Logs
logs/

# IDE
.vscode/
.idea/

# OS
Thumbs.db
.DS_Store

# Build
dist/
build/

# Temp
*.tmp

# Resolve Cache
CacheClip/
""",
encoding="utf-8"
)

print("✓ .gitignore verified")

# ----------------------------------------------------
# Resolve Bridge
# ----------------------------------------------------

bridge_files = [
    "bridge/__init__.py",
    "bridge/bridge.py",
    "bridge/exporter.py",
    "bridge/models.py",
    "bridge/commands.py",

    "resolve/common.py",
    "resolve/run_bridge.py",
    "resolve/create_project.py",
    "resolve/create_bins.py",
    "resolve/import_media.py",
]

for file in bridge_files:

    path = ROOT / file

    if not path.exists():

        path.write_text("", encoding="utf-8")

print("✓ Resolve Bridge scaffold verified")

# ----------------------------------------------------
# Demo Project
# ----------------------------------------------------

demo = ROOT / "projects" / "demo_project.json"

if not demo.exists():

    demo.write_text(
"""{
    "project_name": "ABR Festival",

    "bins": [
        "GoPro",
        "DJI Flip",
        "Insta360",
        "Drone",
        "Audio",
        "Exports"
    ]
}
""",
encoding="utf-8"
)

print("✓ Demo project created")

print()
print("=" * 70)
print(" Project cleanup complete")
print("=" * 70)