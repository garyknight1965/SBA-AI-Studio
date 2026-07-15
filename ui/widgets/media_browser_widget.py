from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)

from sba_resolve.core.models.media_library import MediaLibrary


class MediaBrowserWidget(QTableWidget):

    # Emits the selected MediaFile (or None on deselection), so
    # other panels (e.g. the Metadata panel) can react without
    # this widget needing to know anything about them.
    clip_selected = Signal(object)

    HEADERS = [
        "Filename",
        "Camera",
        "Resolution",
        "Duration",
        "Type",
    ]

    def __init__(self):
        super().__init__(0, len(self.HEADERS))

        self.library: MediaLibrary | None = None

        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)

        self.itemSelectionChanged.connect(self._selection_changed)

    def set_library(self, library: MediaLibrary) -> None:
        self.library = library
        self.refresh()

    def refresh(self) -> None:
        self.setRowCount(0)

        if self.library is None:
            return

        for media in self.library:
            row = self.rowCount()
            self.insertRow(row)

            self.setItem(row, 0, QTableWidgetItem(media.filename))
            self.setItem(row, 1, QTableWidgetItem(media.camera_model))
            self.setItem(
                row,
                2,
                QTableWidgetItem(f"{media.width} x {media.height}")
            )
            self.setItem(row, 3, QTableWidgetItem(str(media.duration)))
            self.setItem(row, 4, QTableWidgetItem(media.extension))

            # Stashed on the first column's item so selection
            # changes can look the real MediaFile back up.
            self.item(row, 0).setData(Qt.UserRole, media)

        self.resizeColumnsToContents()

    def _selection_changed(self) -> None:

        selected = self.selectedItems()

        if not selected:
            self.clip_selected.emit(None)
            return

        row = selected[0].row()

        media = self.item(row, 0).data(Qt.UserRole)

        self.clip_selected.emit(media)
