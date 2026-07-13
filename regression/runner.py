"""
============================================================
SBA AI Studio
Regression Runner
Version : 1.0.0
Sprint : R2
============================================================

Runs every discovered regression test.
"""

from __future__ import annotations

import sys
from collections import defaultdict

from regression.registry import RegressionRegistry


class RegressionRunner:

    def __init__(self):

        self.registry = RegressionRegistry()

    def run(self) -> int:

        print("=" * 60)
        print(" SBA AI Studio Regression Suite")
        print("=" * 60)
        print()

        results = []

        for test in self.registry.tests:

            result = test.execute()

            results.append(result)

        grouped = defaultdict(list)

        for result in results:

            grouped[result.category].append(result)

        passed = 0
        failed = 0

        for category in sorted(grouped):

            print(category)

            print("-" * len(category))

            for result in grouped[category]:

                print(result)

                if result.success:
                    passed += 1
                else:
                    failed += 1

            print()

        print("=" * 60)

        print(f"Passed : {passed}")

        print(f"Failed : {failed}")

        print("=" * 60)

        return 0 if failed == 0 else 1


def main():

    runner = RegressionRunner()

    return runner.run()


if __name__ == "__main__":

    raise SystemExit(main())