"""
============================================================
SBA AI Studio
Settings Dialog
GUI-010
Version : 1.1.0
============================================================

A real in-app Settings dialog, so config/settings.json's
important toggles - timeline creation, multicam audio sync,
Gap Compression, Ollama model, ExifTool path, Resolve module
path, theme - can be edited through the app instead of by hand.

Reads current values via app_settings.py's load_*() functions
when opened, and writes every field back via save_settings() as
one atomic update on OK/Apply - never partially, so a cancelled
dialog never touches the file at all.

Version 1.1.0 (2026-07-19, GUI-011) adds a dark theme checkbox
and applies the change immediately via ui.theme.apply_theme() on
OK, so a theme change is visible right away without restarting
the app.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from sba_resolve.core.services.app_settings import (
    load_exiftool_path,
    load_gap_compression_settings,
    load_multicam_audio_sync_enabled,
    load_ollama_model,
    load_resolve_module_path,
    load_theme,
    load_timeline_creation_enabled,
    save_settings,
)
from ui.theme import apply_theme


class SettingsDialog(QDialog):
    """
    Modal Settings dialog. Call exec() to show it; returns
    QDialog.Accepted if the person clicked OK (settings have
    already been saved to disk, and the theme already applied,
    at that point), or QDialog.Rejected if they clicked Cancel
    (nothing was written or changed).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)

        # -----------------------------------------------------
        # Appearance section
        # -----------------------------------------------------

        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout()

        self.dark_theme_check = QCheckBox("Dark theme")
        appearance_form.addRow(self.dark_theme_check)

        appearance_group.setLayout(appearance_form)
        layout.addWidget(appearance_group)

        # -----------------------------------------------------
        # Resolve section
        # -----------------------------------------------------

        resolve_group = QGroupBox("DaVinci Resolve")
        resolve_form = QFormLayout()

        self.timeline_creation_check = QCheckBox(
            "Create timeline on import"
        )
        resolve_form.addRow(self.timeline_creation_check)

        self.multicam_audio_sync_check = QCheckBox(
            "Attempt audio sync for multicam cameras (experimental "
            "- off is recommended, see tooltip)"
        )
        self.multicam_audio_sync_check.setToolTip(
            "When off (recommended): only GoPro HERO13 Black "
            "auto-places on the timeline. Every other camera gets "
            "an empty, named placeholder track for manual sync in "
            "Resolve.\n\n"
            "When on: the app attempts audio-based sync "
            "verification for overlapping camera clips. Real-world "
            "testing (2026-07-19) found this unreliable on every "
            "footage pair tried, including a same-brand GoPro "
            "control - only enable this if you have a cleaner "
            "audio setup worth testing."
        )
        resolve_form.addRow(self.multicam_audio_sync_check)

        self.resolve_module_path_edit = QLineEdit()
        resolve_form.addRow(
            "Resolve module path (blank = auto-detect):",
            self._path_row(self.resolve_module_path_edit, is_folder=True),
        )

        resolve_group.setLayout(resolve_form)
        layout.addWidget(resolve_group)

        # -----------------------------------------------------
        # Gap Compression section
        # -----------------------------------------------------

        gap_group = QGroupBox("Gap Compression")
        gap_form = QFormLayout()

        self.gap_enabled_check = QCheckBox("Enable Gap Compression")
        gap_form.addRow(self.gap_enabled_check)

        self.gap_threshold_spin = QDoubleSpinBox()
        self.gap_threshold_spin.setRange(1.0, 3600.0)
        self.gap_threshold_spin.setSuffix(" s")
        self.gap_threshold_spin.setDecimals(0)
        gap_form.addRow(
            "Compress gaps longer than:", self.gap_threshold_spin
        )

        self.gap_compressed_spin = QDoubleSpinBox()
        self.gap_compressed_spin.setRange(0.0, 300.0)
        self.gap_compressed_spin.setSuffix(" s")
        self.gap_compressed_spin.setDecimals(0)
        gap_form.addRow(
            "Compress those gaps down to:", self.gap_compressed_spin
        )

        gap_group.setLayout(gap_form)
        layout.addWidget(gap_group)

        # -----------------------------------------------------
        # AI / Tools section
        # -----------------------------------------------------

        tools_group = QGroupBox("AI && Tools")
        tools_form = QFormLayout()

        self.ollama_model_edit = QLineEdit()
        tools_form.addRow("Ollama model:", self.ollama_model_edit)

        self.exiftool_path_edit = QLineEdit()
        tools_form.addRow(
            "ExifTool path:",
            self._path_row(self.exiftool_path_edit, is_folder=False),
        )

        tools_group.setLayout(tools_form)
        layout.addWidget(tools_group)

        # -----------------------------------------------------
        # OK / Cancel
        # -----------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_current_values()

    def _path_row(self, line_edit: QLineEdit, is_folder: bool) -> QHBoxLayout:
        """
        Wraps a QLineEdit with a "Browse..." button that opens a
        file or folder picker and fills the field - returned as a
        layout so it can be dropped straight into a QFormLayout
        row.
        """

        row = QHBoxLayout()
        row.addWidget(line_edit)

        browse_button = QPushButton("Browse...")

        def _browse():
            if is_folder:
                chosen = QFileDialog.getExistingDirectory(
                    self, "Select Folder", line_edit.text()
                )
            else:
                chosen, _ = QFileDialog.getOpenFileName(
                    self, "Select File", line_edit.text()
                )
            if chosen:
                line_edit.setText(chosen)

        browse_button.clicked.connect(_browse)
        row.addWidget(browse_button)

        return row

    def _load_current_values(self):

        self.dark_theme_check.setChecked(load_theme() == "dark")

        self.timeline_creation_check.setChecked(
            load_timeline_creation_enabled()
        )
        self.multicam_audio_sync_check.setChecked(
            load_multicam_audio_sync_enabled()
        )
        self.resolve_module_path_edit.setText(load_resolve_module_path())

        gap_settings = load_gap_compression_settings()
        self.gap_enabled_check.setChecked(gap_settings.enabled)
        self.gap_threshold_spin.setValue(
            gap_settings.gap_threshold_seconds
        )
        self.gap_compressed_spin.setValue(
            gap_settings.compressed_gap_seconds
        )

        self.ollama_model_edit.setText(load_ollama_model())
        self.exiftool_path_edit.setText(load_exiftool_path())

    def _on_accept(self):

        theme_value = "dark" if self.dark_theme_check.isChecked() else (
            "light"
        )

        updates = {
            "theme": theme_value,
            "enable_timeline_creation": (
                self.timeline_creation_check.isChecked()
            ),
            "enable_multicam_audio_sync": (
                self.multicam_audio_sync_check.isChecked()
            ),
            "resolve_module_path": self.resolve_module_path_edit.text(),
            "gap_compression": {
                "enabled": self.gap_enabled_check.isChecked(),
                "gap_threshold_seconds": self.gap_threshold_spin.value(),
                "compressed_gap_seconds": (
                    self.gap_compressed_spin.value()
                ),
            },
            "ollama_model": self.ollama_model_edit.text().strip() or (
                "llama3.2"
            ),
            "exiftool": self.exiftool_path_edit.text(),
        }

        save_settings(updates)

        # GUI-011: apply immediately, so switching theme is visible
        # right away rather than only on next launch.
        apply_theme(theme_value)

        self.accept()