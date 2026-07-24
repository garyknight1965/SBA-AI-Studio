"""
============================================================
SBA AI Studio
YouTube Metadata Panel
ML-028-001 / ML-059 (rich SEO output) / ML-060 (scrollable layout) / ML-065 (type safety)
Version : 1.2.1
============================================================

Displays generated YouTube title/description/tags, editable so
the channel owner can tweak before publishing. Generation itself
happens elsewhere (see YouTubeMetadataWorker) - this widget is
purely display + a "Generate" trigger signal.

ML-059 (2026-07-23, per Gary's SEO-expert prompt template) adds
display fields for the richer generated output: 4 additional
title options (the primary pick still populates Title: above),
15 SEO tags (unchanged field, just a longer list now), a
suggested export filename, a pinned comment, and thumbnail
overlay text.

ML-060 (2026-07-23): those extra fields made the panel taller
than its dock area, overflowing into whatever panel sits below it
instead of scrolling - the same problem the Settings dialog had
(GUI-010 backlog item 5) before it got a QScrollArea. Fixed the
same way here: everything except the notes field / Generate
button / status label now lives inside a QScrollArea, so the
metadata form scrolls internally instead of overflowing into
neighbouring docks.

ML-065 (2026-07-23): set_metadata() crashed with a TypeError when
the model returned "description" as a list instead of a string
(QTextEdit.setPlainText only accepts str). Added a small
_as_text() helper used on every single-string field pulled from
the metadata dict, so a schema drift from the model degrades
gracefully (joined into readable text) instead of crashing the
whole generation flow. This is a defensive fix at the display
boundary - it does not address whether the generator/prompt side
should also be coercing types before storing the metadata dict.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def _as_text(value) -> str:
    """
    Coerces a metadata value that is expected to be a single
    string for display, but which the model occasionally returns
    as a list of strings (e.g. a description split into
    paragraphs) instead. Anything else falsy becomes "".

    This is intentionally permissive rather than raising - a
    malformed field should degrade to readable text, not crash
    the whole metadata panel.
    """

    if not value:
        return ""
    if isinstance(value, list):
        return "\n\n".join(str(part) for part in value)
    return str(value)


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
            "Generated title (best pick) will appear here"
        )

        self.title_options_field = QTextEdit()
        self.title_options_field.setPlaceholderText(
            "Alternate title options will appear here, one per line"
        )
        self.title_options_field.setMinimumHeight(70)
        self.title_options_field.setMaximumHeight(90)

        self.description_field = QTextEdit()
        self.description_field.setPlaceholderText(
            "Generated description will appear here"
        )
        self.description_field.setMinimumHeight(120)

        self.tags_field = QLineEdit()
        self.tags_field.setPlaceholderText(
            "Generated tags will appear here (comma-separated)"
        )

        self.filename_field = QLineEdit()
        self.filename_field.setPlaceholderText(
            "Suggested export filename will appear here"
        )

        self.pinned_comment_field = QTextEdit()
        self.pinned_comment_field.setPlaceholderText(
            "Suggested pinned comment will appear here"
        )
        self.pinned_comment_field.setMinimumHeight(50)
        self.pinned_comment_field.setMaximumHeight(70)

        self.thumbnail_text_field = QLineEdit()
        self.thumbnail_text_field.setPlaceholderText(
            "Suggested thumbnail overlay text will appear here"
        )

        form = QFormLayout()
        form.addRow("Title:", self.title_field)
        form.addRow("Other title options:", self.title_options_field)
        form.addRow("Description:", self.description_field)
        form.addRow("Tags:", self.tags_field)
        form.addRow("Suggested filename:", self.filename_field)
        form.addRow("Pinned comment:", self.pinned_comment_field)
        form.addRow("Thumbnail text:", self.thumbnail_text_field)

        group = QGroupBox("YouTube Metadata (draft - edit before publishing)")
        group.setLayout(form)

        # ML-060: the form above can grow taller than the dock
        # area (especially with every ML-059 field populated at
        # once) - put it in a scroll area so it scrolls
        # internally instead of overflowing into whatever panel
        # sits below this one. The notes field / Generate button
        # / status label stay outside the scroll area, always
        # visible at the top.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setWidget(group)

        layout = QVBoxLayout(self)
        layout.addWidget(self.notes_field)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.status_label)
        layout.addWidget(scroll_area)

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
        silently lost even on a bad response - every other field
        is cleared rather than left showing stale data.

        Every single-string field is passed through _as_text()
        first, since the model has been observed returning a list
        (e.g. paragraphs) for fields that are supposed to be a
        single string - without this, PySide6 raises a TypeError
        and the whole "metadata generated" signal handler blows up.
        """

        if metadata.get("parse_error"):
            self.status_label.setText(
                "The model's response wasn't valid structured "
                "JSON - showing its raw output below instead."
            )
            self.title_field.setText("")
            self.title_options_field.setPlainText("")
            self.description_field.setPlainText(
                _as_text(metadata.get("raw_response", ""))
            )
            self.tags_field.setText("")
            self.filename_field.setText("")
            self.pinned_comment_field.setPlainText("")
            self.thumbnail_text_field.setText("")
            return

        self.status_label.setText(
            "Draft generated - review and edit before publishing. "
            "This is a starting point, not a final copy: it only "
            "knows what the ride reconstruction data told it."
        )

        titles = metadata.get("titles") or []
        # titles itself is expected to be a list already; guard
        # against a model returning a single string here too.
        if isinstance(titles, str):
            titles = [titles]

        self.title_field.setText(_as_text(metadata.get("title")))
        # The primary pick (titles[0], already in Title: above) is
        # left out of this list so the two fields don't repeat
        # each other.
        self.title_options_field.setPlainText(
            "\n".join(str(t) for t in titles[1:])
        )
        self.description_field.setPlainText(
            _as_text(metadata.get("description"))
        )

        tags = metadata.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        self.tags_field.setText(", ".join(str(t) for t in tags))

        self.filename_field.setText(
            _as_text(metadata.get("filename_suggestion"))
        )
        self.pinned_comment_field.setPlainText(
            _as_text(metadata.get("pinned_comment"))
        )
        self.thumbnail_text_field.setText(
            _as_text(metadata.get("thumbnail_text"))
        )

    def set_error(self, message: str) -> None:
        self.status_label.setText(f"Generation failed: {message}")

    def clear(self) -> None:
        self.notes_field.clear()
        self.status_label.setText("")
        self.title_field.clear()
        self.title_options_field.clear()
        self.description_field.clear()
        self.tags_field.clear()
        self.filename_field.clear()
        self.pinned_comment_field.clear()
        self.thumbnail_text_field.clear()
