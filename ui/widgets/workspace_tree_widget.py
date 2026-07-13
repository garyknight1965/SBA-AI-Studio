"""
SBA AI Studio
GUI-002-001
Dynamic Workspace Tree Widget
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from sba_resolve.core.models.workspace import Workspace


class WorkspaceTreeWidget(QTreeWidget):
    """
    Dynamic workspace tree built from Workspace.media.
    """

    category_selected = Signal(str)
    media_selected = Signal(object)

    def __init__(self, workspace: Workspace):
        super().__init__()
        self.workspace = workspace

        self.setHeaderHidden(True)
        self.itemSelectionChanged.connect(self._selection_changed)

        self.refresh()

    def set_workspace(self, workspace: Workspace):
        self.workspace = workspace
        self.refresh()

    def refresh(self):
        self.clear()

        root = QTreeWidgetItem(["Workspace"])
        self.addTopLevelItem(root)

        media_root = QTreeWidgetItem(
            [f"Media ({self.workspace.total_files})"]
        )
        root.addChild(media_root)

        groups = defaultdict(list)

        for media in self.workspace.media:
            category = getattr(media, "category", "") or "Unknown"
            groups[category].append(media)

        for category in sorted(groups):
            clips = sorted(groups[category], key=lambda m: m.filename.lower())

            category_item = QTreeWidgetItem(
                [f"{category} ({len(clips)})"]
            )
            category_item.setData(0, Qt.UserRole, ("category", category))
            media_root.addChild(category_item)

            for clip in clips:
                clip_item = QTreeWidgetItem([clip.filename])
                clip_item.setData(0, Qt.UserRole, ("media", clip))
                category_item.addChild(clip_item)

        for name in ("Timeline", "Journey", "AI", "Export"):
            root.addChild(QTreeWidgetItem([name]))

        self.expandAll()

    def _selection_changed(self):
        item = self.currentItem()
        if item is None:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        kind, value = data

        if kind == "category":
            self.category_selected.emit(value)
        elif kind == "media":
            self.media_selected.emit(value)
