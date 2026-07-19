"""
============================================================
SBA AI Studio
Locations Panel
ML-040-001
Version : 1.2.0
============================================================

Displays scanned media grouped by reverse-geocoded location (see
LocationGrouper / LocationGroupingWorker). Generation is a manual
trigger, not automatic on scan, because ReverseGeocoder makes real
network calls (rate-limited to ~1/second per distinct location) -
same reasoning as YouTubeMetadataWidget/TranscriptWidget: this
widget is purely display + a trigger signal, the actual work runs
on a background thread owned by MainWindow.

Version 1.2.0 (2026-07-19, GUI-011) bumps the minimum height from
200 to 260 - 200 still let the wrapped status text get clipped
(confirmed via screenshot).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LocationsWidget(QWidget):

    # Emitted when the user clicks Generate - MainWindow runs
    # LocationGroupingWorker and calls set_groups()/set_error()
    # back on this widget.
    generate_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # GUI-011: floor height so the wrapped status text and
        # location list always have room, regardless of how the
        # dock area splits space between the three right-side
        # panels.
        self.setMinimumHeight(260)

        self.generate_button = QPushButton("Group by Location")
        self.generate_button.clicked.connect(
            self.generate_requested.emit
        )

        self.status_label = QLabel(
            "Not yet generated - this makes real network requests "
            "(one per distinct location, rate-limited), so it "
            "only runs when you click the button."
        )
        self.status_label.setWordWrap(True)

        self.location_list = QListWidget()
        self.location_list.addItem("No locations generated yet.")
        self.location_list.setAlternatingRowColors(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.location_list)

    def set_generating(self, is_generating: bool) -> None:

        self.generate_button.setEnabled(not is_generating)

        if is_generating:
            self.status_label.setText(
                "Looking up locations... this can take a few "
                "seconds per distinct place (rate-limited to "
                "protect the free geocoding service)."
            )

    def set_groups(self, groups: list) -> None:
        """
        Populates the list from a list of LocationGroup objects
        (see LocationGrouper.group()).
        """

        self.location_list.clear()

        if not groups:
            self.location_list.addItem("No locations found.")
            self.status_label.setText("No locations found.")
            return

        known_count = sum(1 for g in groups if not g.is_unknown)

        for group in groups:
            label = f"{group.place_name} ({group.clip_count} clip(s))"
            self.location_list.addItem(label)

        self.status_label.setText(
            f"Grouped into {known_count} known location(s)"
            + (
                " + an Unknown Location group."
                if any(g.is_unknown for g in groups)
                else "."
            )
        )

    def set_error(self, message: str) -> None:
        self.status_label.setText(f"Location grouping failed: {message}")

    def clear(self) -> None:
        self.location_list.clear()
        self.location_list.addItem("No locations generated yet.")
        self.status_label.setText(
            "Not yet generated - this makes real network requests "
            "(one per distinct location, rate-limited), so it "
            "only runs when you click the button."
        )