"""
SBA AI Studio
GUI-001 Integration
Dock Manager v2
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ui.widgets.workspace_tree_widget import WorkspaceTreeWidget
from ui.widgets.media_browser_widget import MediaBrowserWidget
from ui.widgets.metadata_widget import MetadataWidget
from ui.widgets.statistics_widget import StatisticsWidget
from ui.widgets.timeline_widget import TimelineWidget
from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)


class DockManager:

    def __init__(self, main_window):
        self.main_window = main_window
        self._created = False

    def build(self, workspace):
        if self._created:
            self.refresh(workspace)
            return

        self.workspace_tree = WorkspaceTreeWidget(workspace)
        self.media_browser = MediaBrowserWidget()
        self.metadata_panel = MetadataWidget()
        self.statistics_panel = StatisticsWidget()
        self.timeline_panel = TimelineWidget()

        self._add("Workspace", self.workspace_tree, Qt.LeftDockWidgetArea)
        self._add("Media Browser", self.media_browser, Qt.LeftDockWidgetArea)
        self._add("Metadata", self.metadata_panel, Qt.RightDockWidgetArea)
        self._add("Statistics", self.statistics_panel, Qt.RightDockWidgetArea)
        self._add("Timeline", self.timeline_panel, Qt.BottomDockWidgetArea)

        self.main_window.workspace_tree = self.workspace_tree
        self.main_window.media_browser = self.media_browser
        self.main_window.metadata_panel = self.metadata_panel
        self.main_window.statistics_panel = self.statistics_panel
        self.main_window.timeline_panel = self.timeline_panel

        # Selecting a clip in EITHER the workspace tree or the
        # media browser table populates the Metadata panel -
        # WorkspaceTreeWidget already emitted media_selected, it
        # just had nothing listening on the other end.
        self.workspace_tree.media_selected.connect(
            self.metadata_panel.set_media
        )
        self.media_browser.clip_selected.connect(
            self.metadata_panel.set_media
        )

        self._created = True
        self.refresh(workspace)

    def refresh(self, workspace):
        self.workspace_tree.workspace = workspace
        if hasattr(self.workspace_tree, "refresh"):
            self.workspace_tree.refresh()

        self.media_browser.set_library(workspace.media)
        self.statistics_panel.update_statistics(workspace.media)
        self.metadata_panel.clear()
        self._refresh_timeline_preview(workspace)

    def _refresh_timeline_preview(self, workspace):
        """
        Populates the Timeline panel with a Day/Scene grouped
        preview from the Planning Engine - this runs entirely
        locally (no Resolve connection needed), so it works even
        with Resolve timeline creation disabled or Resolve not
        connected at all. Falls back to "Timeline is empty" if
        there's no media yet, or the Planning Engine can't
        produce anything from it.
        """

        media = list(getattr(workspace, "media", []) or [])

        if not media:
            self.timeline_panel.clear()
            return

        try:
            result = TimelinePlanningService().plan(media)
        except Exception:
            # A local preview should never crash the app - if
            # planning fails for any reason, just show nothing
            # rather than an error dialog over a side panel.
            self.timeline_panel.clear()
            return

        if not result.placements:
            self.timeline_panel.clear()
            return

        lines = []

        for placement in sorted(
            result.placements,
            key=lambda p: (p.ride_day, p.scene, p.record_frame),
        ):
            lines.append(
                f"Day {placement.ride_day} / Scene {placement.scene} "
                f"| {placement.camera_name or 'Unknown'} "
                f"| {placement.clip_name}"
            )

        self.timeline_panel.load_clips(lines)

    def _add(self, title, widget, area):
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(title.replace(" ", "_"))
        dock.setWidget(widget)
        self.main_window.addDockWidget(area, dock)
