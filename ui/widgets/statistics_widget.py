"""
SBA AI Studio
GUI-001-002
Statistics Panel
"""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from sba_resolve.core.models.media_library import MediaLibrary


class StatisticsWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._labels = {}

        form = QFormLayout()
        for title in (
            "Total Files",
            "Total Duration",
            "Video Files",
            "Image Files",
            "GoPro",
            "DJI",
            "Insta360",
            "Other",
        ):
            lbl = QLabel("0")
            self._labels[title] = lbl
            form.addRow(f"{title}:", lbl)

        group = QGroupBox("Project Statistics")
        group.setLayout(form)

        layout = QVBoxLayout(self)
        layout.addWidget(group)
        layout.addStretch()

    def update_statistics(self, library: MediaLibrary | None):
        if library is None:
            for lbl in self._labels.values():
                lbl.setText("0")
            return

        total = len(library)
        video = 0
        image = 0
        gopro = dji = insta = other = 0
        duration = 0.0

        for media in library:
            ext = getattr(media, "extension", "").lower()
            if ext in {".mp4", ".mov", ".mxf"}:
                video += 1
            else:
                image += 1

            duration += float(getattr(media, "duration_seconds", 0) or 0)

            cam = str(getattr(media, "camera_model", "")).lower()
            if "gopro" in cam:
                gopro += 1
            elif "dji" in cam:
                dji += 1
            elif "insta" in cam:
                insta += 1
            else:
                other += 1

        self._labels["Total Files"].setText(str(total))
        self._labels["Video Files"].setText(str(video))
        self._labels["Image Files"].setText(str(image))
        self._labels["GoPro"].setText(str(gopro))
        self._labels["DJI"].setText(str(dji))
        self._labels["Insta360"].setText(str(insta))
        self._labels["Other"].setText(str(other))

        hrs = int(duration // 3600)
        mins = int((duration % 3600) // 60)
        secs = int(duration % 60)
        self._labels["Total Duration"].setText(f"{hrs:02}:{mins:02}:{secs:02}")
