"""
============================================================
SBA AI Studio
Create Bins Command
Version : 1.0.0
Sprint : RV-003
============================================================

Creates Media Pool bins from a TimelinePlan.

Business logic belongs in commands.
"""

from __future__ import annotations

from sba_resolve.context import ResolveContext
from sba_resolve.core.models.timeline_plan import TimelinePlan


class CreateBinsCommand:
    """
    Creates the Media Pool folder structure for a TimelinePlan.
    """

    def __init__(self, context: ResolveContext):

        self.context = context

    def execute(
        self,
        plan: TimelinePlan,
    ) -> None:

        media_pool = self.context.media_pool
        root = self.context.root_folder

        if media_pool is None:
            raise RuntimeError("Media Pool unavailable.")

        for day in plan.days:

            #
            # Create (or reuse) the day folder
            #

            day_folder = self._ensure_folder(
                root,
                str(day.day),
            )

            for track in day.tracks:

                self._ensure_folder(
                    day_folder,
                    track.name,
                )

    # -----------------------------------------------------

    def _ensure_folder(
        self,
        parent,
        name: str,
    ):

        #
        # Reuse existing folder
        #

        for folder in parent.GetSubFolderList():

            if folder.GetName() == name:

                self.context.report.bins_existing += 1

                return folder

        #
        # Create new folder
        #

        folder = self.context.media_pool.AddSubFolder(
            parent,
            name,
        )

        if folder is None:

            raise RuntimeError(
                f"Unable to create folder '{name}'."
            )

        self.context.report.bins_created += 1

        return folder