"""
SBA AI Studio
Developer Toolkit Bootstrap

Creates the tools folder and developer test scripts.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"
TOOLS.mkdir(exist_ok=True)

FILES = {
    "resolve_diagnostics.py": 
DEV-001 Resolve Diagnostics
