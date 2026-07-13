"""
============================================================
SBA AI Studio
Import Timeline Command
Version : 1.0.0
Sprint : RV-001
============================================================

Imports a TimelinePlan into DaVinci Resolve.

Business logic belongs here.

Resolve services remain thin wrappers around the API.
"""

from __future__ import annotations

from sba_resolve.core.models.timeline_plan import TimelinePlan
from sba_resolve.core.services.resolve_media_pool_service import (
    ResolveMediaPoolService,
)


class ImportTimelineCommand:
    """
    Import a TimelinePlan into DaVinci Resolve.

    This class orchestrates the import process while keeping
    Resolve services free from business logic.
    """

    def __init__(self, context):

        self.context = context

        self.media_pool = ResolveMediaPoolService(context)

    def execute(
        self,
        plan: TimelinePlan,
    ) -> None:

        if plan.total_clips == 0:
            raise RuntimeError(
                "TimelinePlan contains no clips."
            )

        print()
        print("=" * 60)
        print("Import Timeline")
        print("=" * 60)

        imported = 0

        for day in plan.days:

            print(f"\nDay: {day.day}")

            for track in day.tracks:

                print(f"  Track: {track.name}")

                #
                # Current implementation imports into the
                # Resolve root folder.
                #
                # Later versions will automatically create
                # matching Media Pool bins.
                #

                folder = self.media_pool.root_folder

                for clip in track.clips:

                    if self.media_pool.clip_exists(
                        folder,
                        clip.media.full_path,
                    ):
                        continue

                    result = self.media_pool.import_file(
                        folder,
                        clip.media.full_path,
                    )

                    if result is not None:
                        imported += 1

        print()
        print("=" * 60)
        print(f"Imported : {imported}")
        print("=" * 60)