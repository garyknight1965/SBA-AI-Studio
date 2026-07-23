"""
============================================================
SBA AI Studio
Regression Runner
Version : 1.1.0
Sprint : R2
============================================================

Runs discovered regression tests, optionally filtered by mode:

    python run_regression.py --core
        Tests that need neither a real headless GUI nor a real
        Resolve connection - safe to run in any plain Python
        environment.

    python run_regression.py --ui
        Only tests that construct real (offscreen) PySide6
        widgets. Skipped automatically - and reported as BLOCKED,
        not FAILED - if the environment is missing a native GUI
        dependency such as libGL.so.1.

    python run_regression.py --resolve
        Only tests that exercise Resolve-integration behaviour.
        (All Resolve API access in this suite is mocked - nothing
        here requires a running copy of Resolve.)

    python run_regression.py --all
        Everything. This is the default if run_regression.py is
        invoked with no arguments at all, matching prior behaviour.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from regression.gui_preflight import check_gui_available
from regression.registry import RegressionRegistry
from regression.result import RegressionResult


MODE_ALL = "all"
MODE_CORE = "core"
MODE_UI = "ui"
MODE_RESOLVE = "resolve"


class RegressionRunner:

    def __init__(self, mode: str = MODE_ALL):

        self.mode = mode

        self.registry = RegressionRegistry()

    def _tests_for_mode(self):

        for test in self.registry.tests:

            if self.mode == MODE_ALL:
                yield test

            elif self.mode == MODE_UI:
                if test.requires_gui:
                    yield test

            elif self.mode == MODE_RESOLVE:
                if test.requires_resolve:
                    yield test

            elif self.mode == MODE_CORE:
                if not test.requires_gui and not test.requires_resolve:
                    yield test

    def run(self) -> int:

        print("=" * 60)
        print(" SBA AI Studio Regression Suite")
        print(f" Mode: {self.mode}")
        print("=" * 60)
        print()

        tests = list(self._tests_for_mode())

        needs_gui_check = any(test.requires_gui for test in tests)

        gui_available, gui_reason = (
            check_gui_available() if needs_gui_check else (True, "")
        )

        if needs_gui_check and not gui_available:
            print(f"GUI preflight: {gui_reason}")
            print(
                "GUI-dependent tests below will be reported as "
                "BLOCKED (environment limitation), not FAILED."
            )
            print()

        results = []

        for test in tests:

            if test.requires_gui and not gui_available:

                results.append(
                    RegressionResult(
                        name=test.name,
                        category=test.category,
                        success=False,
                        duration=0.0,
                        message=gui_reason,
                        blocked=True,
                    )
                )

                continue

            results.append(test.execute())

        grouped = defaultdict(list)

        for result in results:

            grouped[result.category].append(result)

        passed = 0
        failed = 0
        blocked = 0

        for category in sorted(grouped):

            print(category)

            print("-" * len(category))

            for result in grouped[category]:

                print(result)

                if result.blocked:
                    if result.message:
                        print(f"    {result.message}")
                    blocked += 1
                elif not result.success:
                    if result.message:
                        print(f"    {result.message}")
                    failed += 1
                else:
                    passed += 1

            print()

        print("=" * 60)

        print(f"Passed  : {passed}")
        print(f"Failed  : {failed}")
        print(f"Blocked : {blocked}")

        if not tests:
            print()
            print(f"(no tests matched mode '{self.mode}')")

        print("=" * 60)

        return 0 if failed == 0 else 1


def _parse_args(argv):

    parser = argparse.ArgumentParser(
        description="SBA AI Studio regression suite",
    )

    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        "--core",
        action="store_const",
        dest="mode",
        const=MODE_CORE,
        help=(
            "Run only tests that need neither a real headless GUI "
            "nor a real Resolve connection."
        ),
    )

    mode_group.add_argument(
        "--ui",
        action="store_const",
        dest="mode",
        const=MODE_UI,
        help="Run only tests that construct real headless GUI widgets.",
    )

    mode_group.add_argument(
        "--resolve",
        action="store_const",
        dest="mode",
        const=MODE_RESOLVE,
        help="Run only tests that exercise Resolve-integration behaviour.",
    )

    mode_group.add_argument(
        "--all",
        action="store_const",
        dest="mode",
        const=MODE_ALL,
        help="Run every discovered test (default).",
    )

    parser.set_defaults(mode=MODE_ALL)

    return parser.parse_args(argv)


def main(argv=None):

    args = _parse_args(sys.argv[1:] if argv is None else argv)

    runner = RegressionRunner(mode=args.mode)

    return runner.run()


if __name__ == "__main__":

    raise SystemExit(main())