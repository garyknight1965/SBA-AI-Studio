"""
============================================================
SBA AI Studio
Transcript Panel
ML-037-001
Version : 1.0.0
============================================================

Lets the editor load a DaVinci Resolve transcript export, trigger
IntelliScript generation (see IntelliScriptEditor /
IntelliScriptWorker), review the result, and save it to disk.

This widget is purely display + trigger signals - loading files,
running the AI, and saving results all happen in MainWindow, the
same division used by YouTubeMetadataWidget.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TranscriptWidget(QWidget):

    # Emitted when the user clicks "Load Transcript..." - MainWindow
    # owns the file dialog and calls set_loaded_file() back on this
    # widget once a file is chosen.
    load_requested = Signal()

    # Emitted when the user clicks "Generate IntelliScript" - only
    # enabled once a transcript is loaded.
    generate_requested = Signal()

    # Emitted when the user clicks "Save Script..." - only enabled
    # once a usable script has been generated.
    save_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.load_button = QPushButton("Load Transcript...")
        self.load_button.clicked.connect(self.load_requested.emit)

        self.file_label = QLabel("No transcript loaded.")
        self.file_label.setWordWrap(True)

        self.generate_button = QPushButton("Generate IntelliScript")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(
            self.generate_requested.emit
        )

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.script_output = QTextEdit()
        self.script_output.setPlaceholderText(
            "The generated IntelliScript-ready script will appear "
            "here - editable before saving."
        )
        self.script_output.setMinimumHeight(200)

        self.save_button = QPushButton("Save Script...")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_requested.emit)

        group = QGroupBox(
            "IntelliScript (dead air/filler cut, verbatim wording - "
            "review before use)"
        )
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.script_output)
        group_layout.addWidget(self.save_button)
        group.setLayout(group_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(self.load_button)
        layout.addWidget(self.file_label)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.status_label)
        layout.addWidget(group)

    def set_loaded_file(self, filename: str) -> None:
        """
        Called once MainWindow has read a transcript file - shows
        the filename and enables generation.
        """

        self.file_label.setText(f"Loaded: {filename}")
        self.generate_button.setEnabled(True)
        self.status_label.setText("")

    def set_generating(self, is_generating: bool) -> None:
        """
        Disables Generate while a request is in flight, matching
        YouTubeMetadataWidget's set_generating().
        """

        self.generate_button.setEnabled(not is_generating)
        self.load_button.setEnabled(not is_generating)

        if is_generating:
            self.status_label.setText(
                "Generating... this can take a while, especially "
                "on a long transcript or first model load."
            )

    def set_result(self, result: dict) -> None:
        """
        Populates the script area from an IntelliScriptEditor
        result dict (see IntelliScriptEditor.build_script()).

        On parse_error, shows the model's raw response instead so
        nothing is silently lost, but does NOT enable Save - a raw,
        unparsed model response is not a usable script.
        """

        if result.get("parse_error"):
            self.status_label.setText(
                "The model's response wasn't valid structured "
                "JSON - showing its raw output below instead. Not "
                "safe to save as a script; try generating again."
            )
            self.script_output.setPlainText(
                result.get("raw_response", "")
            )
            self.save_button.setEnabled(False)
            return

        segment_count = result.get("segment_count", 0)
        kept_count = result.get("kept_count", 0)

        self.status_label.setText(
            f"Generated - kept {kept_count} of {segment_count} "
            f"speech segments. Review the wording is exactly as "
            f"spoken before using this with IntelliScript."
        )

        self.script_output.setPlainText(result.get("script", ""))
        self.save_button.setEnabled(bool(result.get("script")))

    def set_error(self, message: str) -> None:
        self.status_label.setText(f"Generation failed: {message}")
        self.save_button.setEnabled(False)

    def current_script(self) -> str:
        """
        The script text as it currently stands in the editor -
        used by MainWindow when saving, so any manual edits the
        user made after generation are preserved.
        """

        return self.script_output.toPlainText()

    def clear(self) -> None:
        self.file_label.setText("No transcript loaded.")
        self.status_label.setText("")
        self.script_output.clear()
        self.generate_button.setEnabled(False)
        self.save_button.setEnabled(False)
