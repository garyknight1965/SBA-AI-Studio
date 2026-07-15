"""
============================================================
SBA AI Studio
Nested Bin Path Regression Test
ML-024
Version : 1.0.0
============================================================

Verifies:
- ResolveMediaPoolService.ensure_bin_path() creates every
  missing folder along a "/"-separated path (e.g. the "Day 1"
  folder AND the "GoPro HERO13 Black" folder inside it), not
  just the final level.
- Calling it again for a path that already partially or fully
  exists reuses those folders instead of creating duplicates.
- sync_bins() reports [NEW] vs [OK] correctly per full
  requested bin path and updates context.report accordingly.
- find_bin_by_path() (used later by import_media) can locate a
  clip's bin after sync_bins() has created it.
"""

from __future__ import annotations

from regression.base_test import BaseRegressionTest


class FakeFolder:

    def __init__(self, name):
        self._name = name
        self._subfolders = []

    def GetName(self):
        return self._name

    def GetSubFolderList(self):
        return list(self._subfolders)

    def GetClipList(self):
        return []


class FakeMediaPool:

    def __init__(self):
        self.add_subfolder_calls = []

    def AddSubFolder(self, parent, name):
        self.add_subfolder_calls.append((parent.GetName(), name))
        folder = FakeFolder(name)
        parent._subfolders.append(folder)
        return folder


class FakeReport:

    def __init__(self):
        self.bins_created = 0
        self.bins_existing = 0


class FakeContext:

    def __init__(self, media_pool, root_folder, project_data):
        self.media_pool = media_pool
        self.root_folder = root_folder
        self.project_data = project_data
        self.report = FakeReport()


class NestedBinPathRegressionTest(BaseRegressionTest):

    name = "Nested Bin Paths (ML-024)"

    category = "Resolve"

    description = (
        "Verify Day/Camera nested bin creation, reuse of "
        "already-existing folders, and correct sync_bins "
        "reporting."
    )

    def run(self) -> None:

        from sba_resolve.commands.sync_bins import sync_bins
        from sba_resolve.media_pool.services.resolve_media_pool_service import (
            ResolveMediaPoolService,
        )

        root = FakeFolder("Root")
        media_pool = FakeMediaPool()

        context = FakeContext(
            media_pool=media_pool,
            root_folder=root,
            project_data={
                "bins": [
                    "Day 1/GoPro HERO13 Black",
                    "Day 1/GoPro HERO8 Black",
                    "Day 2/GoPro HERO13 Black",
                ]
            },
        )

        sync_bins(context)

        # 2 day folders + 3 camera sub-folders = 5 real folders
        # created, even though only 3 bin PATHS were requested.
        if len(media_pool.add_subfolder_calls) != 5:
            raise RuntimeError(
                f"Expected 5 AddSubFolder calls (2 day folders + "
                f"3 camera folders), got "
                f"{len(media_pool.add_subfolder_calls)}: "
                f"{media_pool.add_subfolder_calls}"
            )

        if context.report.bins_created != 3:
            raise RuntimeError(
                f"Expected 3 bin paths reported as created, got "
                f"{context.report.bins_created}."
            )

        # "Day 1" must only be created ONCE, even though two
        # camera bins reference it.
        day1_creations = [
            call for call in media_pool.add_subfolder_calls
            if call == ("Root", "Day 1")
        ]

        if len(day1_creations) != 1:
            raise RuntimeError(
                f"Expected 'Day 1' folder to be created exactly "
                f"once, got {len(day1_creations)} creation(s)."
            )

        # --------------------------------------------------
        # Running sync_bins again for a path that already fully
        # exists must report it as existing, not create anything
        # new.
        # --------------------------------------------------

        context.project_data["bins"] = [
            "Day 1/GoPro HERO13 Black",
        ]

        calls_before = len(media_pool.add_subfolder_calls)

        sync_bins(context)

        if len(media_pool.add_subfolder_calls) != calls_before:
            raise RuntimeError(
                "Re-syncing an already-existing bin path should "
                "not create anything new."
            )

        if context.report.bins_existing != 1:
            raise RuntimeError(
                f"Expected 1 existing bin path reported, got "
                f"{context.report.bins_existing}."
            )

        # --------------------------------------------------
        # find_bin_by_path must locate what sync_bins created -
        # this is exactly what import_media() relies on later.
        # --------------------------------------------------

        service = ResolveMediaPoolService.__new__(
            ResolveMediaPoolService
        )
        service.media_pool = media_pool
        service.root_folder = root

        found = service.find_bin_by_path("Day 2/GoPro HERO13 Black")

        if found is None or found.GetName() != "GoPro HERO13 Black":
            raise RuntimeError(
                "find_bin_by_path() could not locate a bin path "
                "that sync_bins() should have created."
            )

        # A path that was never requested must not exist.
        missing = service.find_bin_by_path("Day 3/GoPro HERO13 Black")

        if missing is not None:
            raise RuntimeError(
                "find_bin_by_path() found a bin path that was "
                "never created."
            )
