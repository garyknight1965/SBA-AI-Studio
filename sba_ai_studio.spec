# -*- mode: python ; coding: utf-8 -*-
"""
============================================================
SBA AI Studio
PyInstaller Build Spec
PACKAGING
Version : 1.0.0
============================================================

Builds a single-file (onefile) Windows .exe.

Bundles, as whole folders (safer than naming individual files -
nothing gets silently missed on a future PySide6/ExifTool
version bump):
  - tools/exiftool/  -> bundled ExifTool (see
    exiftool_engine.py v4.3, which looks for this at
    sys._MEIPASS/tools/exiftool/exiftool.exe when frozen)
  - assets/fonts/    -> bundled Barlow Condensed ExtraBold font
    for thumbnail text (ML-064, see thumbnail_generator.py's
    _bundled_font_path(), which looks for this at
    sys._MEIPASS/assets/fonts/BarlowCondensed-ExtraBold.ttf when
    frozen)
  - PySide6/resources/            -> QtWebEngine .pak resource
    files (icudtl.dat, qtwebengine_resources*.pak)
  - PySide6/translations/         -> QtWebEngine locale .pak
    files (qtwebengine_locales/ subfolder)
  - PySide6/QtWebEngineProcess.exe -> the separate WebEngine
    helper process Qt spawns at runtime

config/settings.json is deliberately NOT bundled - it must stay
external/user-editable next to the real .exe (see
app_settings.py v1.4.0's _default_settings_path(), which
resolves next to sys.executable when frozen). If it doesn't
exist yet on first run, save_settings()/the various load_*()
functions create it automatically with safe defaults - no setup
step needed.

Build with:
    pyinstaller sba_ai_studio.spec

Output: dist/SBA AI Studio.exe
"""

import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH)
PYSIDE6_DIR = PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "PySide6"

datas = [
    (str(PROJECT_ROOT / "tools" / "exiftool"), "tools/exiftool"),
    (str(PROJECT_ROOT / "assets" / "fonts"), "assets/fonts"),
    (str(PYSIDE6_DIR / "resources"), "PySide6/resources"),
    (str(PYSIDE6_DIR / "translations"), "PySide6/translations"),
    (
        str(PYSIDE6_DIR / "QtWebEngineProcess.exe"),
        "PySide6",
    ),
]

hidden_imports = [
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
    "PySide6.QtNetwork",
    "PySide6.QtPrintSupport",
    "cv2",
    "yaml",
]

a = Analysis(
    ["start.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SBA AI Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)