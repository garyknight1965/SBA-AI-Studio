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
from ui.widgets.locations_widget import LocationsWidget
from ui.widgets.metadata_widget import MetadataWidget
from ui.widgets.statistics_widget import StatisticsWidget
from ui.widgets.transcript_widget import TranscriptWidget
from ui.widgets.youtube_metadata_widget import YouTubeMetadataWidget


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
        self.youtube_panel = YouTubeMetadataWidget()
        self.transcript_panel = TranscriptWidget()
        self.locations_panel = LocationsWidget()

        self._add("Workspace", self.workspace_tree, Qt.LeftDockWidgetArea)
        self._add("Media Browser", self.media_browser, Qt.LeftDockWidgetArea)
        self._add("Metadata", self.metadata_panel, Qt.RightDockWidgetArea)
        self._add("Statistics", self.statistics_panel, Qt.RightDockWidgetArea)
        self._add(
            "YouTube Metadata", self.youtube_panel, Qt.BottomDockWidgetArea
        )
        self._add(
            "Transcript", self.transcript_panel, Qt.BottomDockWidgetArea
        )
        self._add(
            "Locations", self.locations_panel, Qt.RightDockWidgetArea
        )

        self.main_window.workspace_tree = self.workspace_tree
        self.main_window.media_browser = self.media_browser
        self.main_window.metadata_panel = self.metadata_panel
        self.main_window.statistics_panel = self.statistics_panel
        self.main_window.youtube_panel = self.youtube_panel
        self.main_window.transcript_panel = self.transcript_panel
        self.main_window.locations_panel = self.locations_panel

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
        self.youtube_panel.clear()
        self.transcript_panel.clear()
        self.locations_panel.clear()

    def _add(self, title, widget, area):
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(title.replace(" ", "_"))
        dock.setWidget(widget)
        self.main_window.addDockWidget(area, dock)
