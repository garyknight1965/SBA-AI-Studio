"""
SBA AI Studio
GUI-001-003
Timeline Panel
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget


class TimelineWidget(QWidget):
    """
    Timeline placeholder for GUI-001.
    Future versions will support drag & drop,
    AI story building and Resolve timeline sync.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title = QLabel("Timeline")
        self.title.setAlignment(Qt.AlignCenter)

        self.timeline = QListWidget()
        self.timeline.addItem("Timeline is empty")
        self.timeline.setAlternatingRowColors(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.timeline)

    def clear(self):
        self.timeline.clear()
        self.timeline.addItem("Timeline is empty")

    def add_clip(self, clip_name: str):
        if self.timeline.count() == 1 and self.timeline.item(0).text() == "Timeline is empty":
            self.timeline.clear()
        self.timeline.addItem(clip_name)

    def load_clips(self, clip_names):
        self.timeline.clear()
        for clip in clip_names:
            self.timeline.addItem(str(clip))
        if self.timeline.count() == 0:
            self.timeline.addItem("Timeline is empty")
