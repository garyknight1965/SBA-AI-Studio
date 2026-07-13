"""
============================================================
SBA AI Studio
Import Project Command
Version : 1.0.0
Sprint : RV-004
============================================================

Complete end-to-end import workflow.

Folder
    ↓
Media Library
    ↓
Timeline Plan
    ↓
Resolve Project
    ↓
Media Pool
"""

from __future__ import annotations

from pathlib import Path

from sba_resolve.commands.create_bins_command import CreateBinsCommand
from sba_resolve.commands.create_project_command import CreateProjectCommand
from sba_resolve.commands.import_timeline_command import ImportTimelineCommand
from sba_resolve.context import ResolveContext
from sba_resolve.core.services.media_library_service import (
    MediaLibraryService,
)
from sba_resolve.core.services.timeline_builder_service import (
    TimelineBuilderService,
)


class ImportProjectCommand:
    """
    Complete SBA AI Studio import workflow.
    """

    def __init__(self, context: ResolveContext):

        self.context = context

        self.library_service = MediaLibraryService()

        self.timeline_builder = TimelineBuilderService()

    def execute(
        self,
        project_name: str,
        media_folder: str | Path,
    ):

        #
        # Create/Open Resolve project
        #

        CreateProjectCommand(
            self.context
        ).execute(project_name)

        #
        # Import media into SBA library
        #

        library = self.library_service.import_folder(
            media_folder
        )

        #
        # Build timeline plan
        #

        plan = self.timeline_builder.build(
            library
        )

        #
        # Create Resolve bins
        #

        CreateBinsCommand(
            self.context
        ).execute(plan)

        #
        # Import media
        #

        ImportTimelineCommand(
            self.context
        ).execute(plan)

        return self.context.report