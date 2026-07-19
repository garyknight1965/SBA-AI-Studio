"""
============================================================
SBA AI Studio
YouTube Metadata Panel
ML-028-001
Version : 1.0.0 Alpha
============================================================

Displays generated YouTube title/description/tags, editable so
the channel owner can tweak before publishing. Generation itself
happens elsewhere (see YouTubeMetadataWorker) - this widget is
purely display + a "Generate" trigger signal.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class YouTubeMetadataWidget(QWidget):

    # Emitted when the user clicks Generate - the owner
    # (MainWindow) is responsible for actually running
    # generation and calling set_metadata()/set_generating()
    # back on this widget.
    generate_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.notes_field = QLineEdit()
        self.notes_field.setPlaceholderText(
            "Optional: a landmark, event, or detail to mention "
            "(e.g. 'stopped at Stirling Castle') - treated as a "
            "real fact, not invented by the model"
        )

        self.generate_button = QPushButton("Generate YouTube Metadata")
        self.generate_button.clicked.connect(
            self.generate_requested.emit
        )

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.title_field = QLineEdit()
        self.title_field.setPlaceholderText(
            "Generated title will appear here"
        )

        self.description_field = QTextEdit()
        self.description_field.setPlaceholderText(
            "Generated description will appear here"
        )
        self.description_field.setMinimumHeight(120)

        self.tags_field = QLineEdit()
        self.tags_field.setPlaceholderText(
            "Generated tags will appear here (comma-separated)"
        )

        form = QFormLayout()
        form.addRow("Title:", self.title_field)
        form.addRow("Description:", self.description_field)
        form.addRow("Tags:", self.tags_field)

        group = QGroupBox("YouTube Metadata (draft - edit before publishing)")
        group.setLayout(form)

        layout = QVBoxLayout(self)
        layout.addWidget(self.notes_field)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.status_label)
        layout.addWidget(group)

    def additional_notes(self) -> str:
        return self.notes_field.text()

    def set_generating(self, is_generating: bool) -> None:
        """
        Disables the Generate button and shows a status message
        while a generation request is in flight.
        """

        self.generate_button.setEnabled(not is_generating)

        if is_generating:
            self.status_label.setText(
                "Generating... this can take a while on first "
                "use while the model loads."
            )

    def set_metadata(self, metadata: dict) -> None:
        """
        Populates the fields from a YouTubeMetadataGenerator
        result dict. If the model's response couldn't be parsed
        (metadata["parse_error"] is True), the raw response is
        shown in the description field instead, so nothing is
        silently lost even on a bad response.
        """

        if metadata.get("parse_error"):
            self.status_label.setText(
                "The model's response wasn't valid structured "
                "JSON - showing its raw output below instead."
            )
            self.title_field.setText("")
            self.description_field.setPlainText(
                metadata.get("raw_response", "")
            )
            self.tags_field.setText("")
            return

        self.status_label.setText(
            "Draft generated - review and edit before publishing. "
            "This is a starting point, not a final copy: it only "
            "knows what the ride reconstruction data told it."
        )

        self.title_field.setText(metadata.get("title") or "")
        self.description_field.setPlainText(
            metadata.get("description") or ""
        )
        self.tags_field.setText(
            ", ".join(metadata.get("tags") or [])
        )

    def set_error(self, message: str) -> None:
        self.status_label.setText(f"Generation failed: {message}")

    def clear(self) -> None:
        self.notes_field.clear()
        self.status_label.setText("")
        self.title_field.clear()
        self.description_field.clear()
        self.tags_field.clear()
