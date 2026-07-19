"""
SBA AI Studio
GUI-001-001
Metadata Panel

GUI-011 (2026-07-19): sets a minimum height so this panel's
11-row form can't be squeezed below a usable size when stacked
with Statistics and Locations in the same dock area - previously
fields like "Camera:"/"Date:" were getting visually clipped with
no obvious indication content was cut off. 240px wasn't enough
(confirmed via screenshot - "Date:" still half-clipped); bumped
to 300px.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sba_resolve.core.models.media_file import MediaFile


class MetadataWidget(QScrollArea):
    FIELDS = [
        ("Filename", "filename"),
        ("Camera", "camera_model"),
        ("Lens", "lens"),
        ("Resolution", "_resolution"),
        ("FPS", "fps"),
        ("Duration", "duration"),
        ("Codec", "codec"),
        ("Bitrate", "bitrate"),
        ("Date", "created"),
        ("GPS", "_gps"),
        ("File Size", "file_size"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        # GUI-011: floor height so the 11-row form always has
        # room to breathe, regardless of how the dock area splits
        # space between Metadata/Statistics/Locations.
        self.setMinimumHeight(300)

        container = QWidget()
        self._form = QFormLayout()

        self._labels = {}
        for title, key in self.FIELDS:
            value = QLabel("-")
            value.setWordWrap(True)
            self._labels[key] = value
            self._form.addRow(f"{title}:", value)

        group = QGroupBox("Metadata")
        group.setLayout(self._form)

        layout = QVBoxLayout(container)
        layout.addWidget(group)
        layout.addStretch()

        self.setWidget(container)

    def clear(self):
        for label in self._labels.values():
            label.setText("-")

    def set_media(self, media: MediaFile | None):
        if media is None:
            self.clear()
            return

        self._labels["filename"].setText(str(getattr(media, "filename", "-")))
        self._labels["camera_model"].setText(str(getattr(media, "camera_model", "-")))
        self._labels["lens"].setText(str(getattr(media, "lens", "-")))
        w = getattr(media, "width", None)
        h = getattr(media, "height", None)
        self._labels["_resolution"].setText(f"{w} x {h}" if w and h else "-")
        self._labels["fps"].setText(str(getattr(media, "fps", "-")))
        self._labels["duration"].setText(str(getattr(media, "duration", "-")))
        self._labels["codec"].setText(str(getattr(media, "codec", "-")))
        self._labels["bitrate"].setText(str(getattr(media, "bitrate", "-")))
        self._labels["created"].setText(str(getattr(media, "created", "-")))
        lat = getattr(media, "gps_latitude", None)
        lon = getattr(media, "gps_longitude", None)
        self._labels["_gps"].setText(f"{lat}, {lon}" if lat is not None and lon is not None else "-")
        self._labels["file_size"].setText(str(getattr(media, "file_size", "-")))