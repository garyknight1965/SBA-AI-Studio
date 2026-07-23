"""
============================================================
SBA AI Studio
Regression GUI Preflight
Version : 1.0.0
============================================================

Some regression tests instantiate real (headless, offscreen)
PySide6 widgets. That requires native libraries - most commonly
libGL.so.1 - that are not installed in many CI/container images.

When those libraries are missing, the tests fail with an opaque
Qt/OpenGL import error that looks identical to a real application
regression. This module runs the same underlying check once,
up front, so the runner can label the affected tests as
"environment-blocked" instead of "failed".

The check is deliberately conservative: it does not just look for
libGL.so.1 on disk (library layouts vary across distros), it tries
to actually construct a QApplication under the offscreen platform,
which is the real thing every GUI regression test needs to succeed.
"""

from __future__ import annotations

import os


_cached_result: tuple[bool, str] | None = None


def check_gui_available() -> tuple[bool, str]:
    """
    Returns (available, reason).

    available is True if a headless PySide6 QApplication could be
    constructed. reason is empty on success, or a short explanation
    of what went wrong (e.g. mentioning libGL.so.1) on failure.

    The result is cached for the lifetime of the process - the
    check is only meaningful once per environment, and constructing
    extra QApplication instances is unnecessary overhead.
    """

    global _cached_result

    if _cached_result is not None:
        return _cached_result

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        _cached_result = (True, "")

    except Exception as ex:

        reason = str(ex).strip() or ex.__class__.__name__

        _cached_result = (
            False,
            f"GUI dependency unavailable ({reason})",
        )

    return _cached_result