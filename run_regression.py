"""
============================================================
SBA AI Studio
Regression Launcher
============================================================

Compatibility entry point.

All regression logic is implemented in the regression package.

This launcher exists so existing documentation, CI scripts,
and developer workflows can continue using:

    python run_regression.py
"""

from regression.runner import main


if __name__ == "__main__":
    raise SystemExit(main())