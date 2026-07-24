"""
============================================================
SBA AI Studio
Settings Dialog
GUI-010
Version : 1.5.0
============================================================

A real in-app Settings dialog, so config/settings.json's
important toggles - timeline creation, multicam audio sync,
Gap Compression, AI provider/model, IntelliScript prompt
guidance, Map routing key, ExifTool path, Resolve module path,
theme - can be edited through the app instead of by hand.

Reads current values via app_settings.py's load_*() functions
when opened, and writes every field back via save_settings() as
one atomic update on OK/Apply - never partially, so a cancelled
dialog never touches the file at all.

Version 1.1.0 (2026-07-19, GUI-011) adds a dark theme checkbox
and applies the change immediately via ui.theme.apply_theme() on
OK, so a theme change is visible right away without restarting
the app.

Version 1.2.0 (Groq provider backlog item) adds an "AI Provider"
section - a choice between Ollama (local, original default) and
Groq (cloud, free tier, chosen over Gemini per Gary's 2026-07-20
decision - Groq directly targets the slowness/timeout problems
Ollama was causing). The Groq API key field never has its value
logged or printed anywhere in this file or in app_settings.py.
Switching providers here takes effect on the very next AI call -
no restart needed, since every AI-calling service reads the
current provider fresh via get_ai_provider() each time it runs.

Version 1.3.0 (2026-07-20/21) adds "IntelliScript Prompt" (a
multi-line editable guidance box) and "Map" (an OpenRouteService
API key field for real road-following routing) sections.

Version 1.4.0 (2026-07-21) fixes a real problem: the dialog had
grown tall enough (Appearance/Resolve/Gap Compression/AI Provider/
IntelliScript Prompt/Map/Tools) that OK/Cancel ended up pushed
below the visible screen on Gary's setup. Fixed properly:
everything except OK/Cancel now lives inside a QScrollArea, so the
dialog is capped to a sane height (520x720) and any overflow
scrolls - OK/Cancel stay on an outer layout, always visible,
regardless of how many sections exist or how small the screen is.

Version 1.5.0 (2026-07-24, ML-072) adds a "Camera LUTs" section -
one field per camera manufacturer (GoPro/DJI/Insta360), applied
automatically to Media Pool clips during timeline creation (see
create_timeline.py's _apply_camera_luts() and
app_settings.load_camera_luts()). Each field's "Browse..." button
opens Resolve's own LUT folder by default and computes the value
relative to it (see _lut_row()) - the stored value must match
exactly what Resolve's own LUT browser shows, not an arbitrary
filesystem path, so browsing from within that folder is the
easiest way to get a value that will actually work. A blank field
leaves that camera's clips untouched, same as before this setting
existed.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sba_resolve.core.services.app_settings import (
    load_ai_provider,
    load_camera_luts,
    load_exiftool_path,
    load_gap_compression_settings,
    load_groq_api_key,
    load_groq_model,
    load_intelliscript_guidance,
    load_multicam_audio_sync_enabled,
    load_ollama_model,
    load_openrouteservice_api_key,
    load_resolve_module_path,
    load_theme,
    load_thumbnail_logo_path,
    load_timeline_creation_enabled,
    load_youtube_metadata_guidance,
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
        # Scrollable-dialog fix (2026-07-21): the dialog kept growing
        # taller with each new section added over time (AI Provider,
        # IntelliScript Prompt, Map) until it exceeded screen height
        # and the OK/Cancel buttons ended up pushed below the visible
        # desktop - reachable in theory (dragging the window up, or
        # pressing Enter for the default button) but not obviously
        # so. Fixed properly: everything except OK/Cancel now lives
        # inside a QScrollArea, so the dialog itself is capped to a
        # sane height and any overflow scrolls - OK/Cancel stay fixed
        # at the bottom, always visible, regardless of how many
        # sections exist or how small the screen is.
        self.resize(520, 720)

        outer_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

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
        # Camera LUTs section (ML-072, 2026-07-24)
        # -----------------------------------------------------
        # Applied automatically to Media Pool clips during timeline
        # creation, per camera manufacturer - see
        # create_timeline.py's _apply_camera_luts() and
        # app_settings.load_camera_luts(). GoPro/DJI/Insta360
        # footage is imported but never auto-placed onto any
        # timeline (Gary drags it in manually later), so this has
        # to be a Media Pool clip property, not a timeline LUT -
        # already handled on the create_timeline.py side; this
        # section is just where the three values get typed in.

        camera_lut_group = QGroupBox("Camera LUTs")
        camera_lut_form = QFormLayout()

        camera_lut_form.addRow(QLabel(
            "Applied automatically to each camera's clips when a "
            "timeline is created. Leave blank to skip a camera.\n"
            "Value must match exactly what Resolve's own LUT "
            "browser shows - use \"Browse...\" to pick a .cube file "
            "from Resolve's LUT folder and the matching value will "
            "be filled in automatically."
        ))

        self.camera_lut_gopro_edit = QLineEdit()
        camera_lut_form.addRow(
            "GoPro:", self._lut_row(self.camera_lut_gopro_edit)
        )

        self.camera_lut_dji_edit = QLineEdit()
        camera_lut_form.addRow(
            "DJI:", self._lut_row(self.camera_lut_dji_edit)
        )

        self.camera_lut_insta360_edit = QLineEdit()
        camera_lut_form.addRow(
            "Insta360:", self._lut_row(self.camera_lut_insta360_edit)
        )

        camera_lut_group.setLayout(camera_lut_form)
        layout.addWidget(camera_lut_group)

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
        # AI Provider section (Groq provider backlog item)
        # -----------------------------------------------------

        ai_group = QGroupBox("AI Provider")
        ai_form = QFormLayout()

        self.ollama_radio = QRadioButton("Ollama (local)")
        self.groq_radio = QRadioButton("Groq (cloud, free tier)")
        self.ai_provider_buttons = QButtonGroup(self)
        self.ai_provider_buttons.addButton(self.ollama_radio)
        self.ai_provider_buttons.addButton(self.groq_radio)
        ai_form.addRow(self.ollama_radio)
        ai_form.addRow(self.groq_radio)

        self.ollama_model_edit = QLineEdit()
        ai_form.addRow("Ollama model:", self.ollama_model_edit)

        self.groq_api_key_edit = QLineEdit()
        self.groq_api_key_edit.setEchoMode(QLineEdit.Password)
        ai_form.addRow("Groq API key:", self.groq_api_key_edit)

        self.groq_model_edit = QLineEdit()
        ai_form.addRow("Groq model:", self.groq_model_edit)

        ai_group.setLayout(ai_form)
        layout.addWidget(ai_group)

        self.ollama_radio.toggled.connect(self._update_ai_field_visibility)
        self.groq_radio.toggled.connect(self._update_ai_field_visibility)

        # -----------------------------------------------------
        # IntelliScript Prompt section
        # -----------------------------------------------------
        # Only the editorial guidance portion of the prompt is
        # editable here (what counts as filler/rambling/meta-
        # commentary, how to group paragraphs) - the mechanical
        # parts (the segment list, the JSON response-format
        # instructions) stay fixed in intelliscript_editor.py, since
        # breaking that part would break parsing regardless of what
        # Gary intended to change.

        prompt_group = QGroupBox("IntelliScript Prompt")
        prompt_layout = QVBoxLayout()

        prompt_layout.addWidget(QLabel(
            "Editorial guidance sent to the AI - what to cut/keep, "
            "how to group paragraphs:"
        ))

        self.intelliscript_guidance_edit = QTextEdit()
        self.intelliscript_guidance_edit.setMinimumHeight(160)
        prompt_layout.addWidget(self.intelliscript_guidance_edit)

        reset_button = QPushButton("Reset to Default")
        reset_button.clicked.connect(self._reset_intelliscript_guidance)
        prompt_layout.addWidget(reset_button)

        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # -----------------------------------------------------
        # YouTube Metadata Prompt section (ML-058, 2026-07-23)
        # -----------------------------------------------------
        # Only the brand-voice/style guidance is editable here
        # (channel tone, title/description style, the editing
        # credit mention) - the mechanical parts of the prompt
        # (day-by-day facts, anti-hallucination rules, JSON
        # response-format instructions) stay fixed in
        # youtube_metadata_generator.py, since loosening those
        # could let the model invent facts or break parsing
        # regardless of what Gary intended to change.

        youtube_prompt_group = QGroupBox("YouTube Metadata Prompt")
        youtube_prompt_layout = QVBoxLayout()

        youtube_prompt_layout.addWidget(QLabel(
            "Brand voice / style guidance sent to the AI - channel "
            "tone, title/description style, editing credit mention:"
        ))

        self.youtube_metadata_guidance_edit = QTextEdit()
        self.youtube_metadata_guidance_edit.setMinimumHeight(160)
        youtube_prompt_layout.addWidget(
            self.youtube_metadata_guidance_edit
        )

        youtube_reset_button = QPushButton("Reset to Default")
        youtube_reset_button.clicked.connect(
            self._reset_youtube_metadata_guidance
        )
        youtube_prompt_layout.addWidget(youtube_reset_button)

        youtube_prompt_group.setLayout(youtube_prompt_layout)
        layout.addWidget(youtube_prompt_group)

        # -----------------------------------------------------
        # Map section
        # -----------------------------------------------------
        # Real road-following routing (2026-07-21). With no key set,
        # the Map panel falls back to its original straight
        # pin-to-pin lines - this field is entirely optional.

        map_group = QGroupBox("Map")
        map_form = QFormLayout()

        self.openrouteservice_api_key_edit = QLineEdit()
        self.openrouteservice_api_key_edit.setEchoMode(QLineEdit.Password)
        map_form.addRow(
            "OpenRouteService API key:",
            self.openrouteservice_api_key_edit,
        )

        map_group.setLayout(map_form)
        layout.addWidget(map_group)

        # -----------------------------------------------------
        # Tools section
        # -----------------------------------------------------

        tools_group = QGroupBox("Tools")
        tools_form = QFormLayout()

        self.exiftool_path_edit = QLineEdit()
        tools_form.addRow(
            "ExifTool path:",
            self._path_row(self.exiftool_path_edit, is_folder=False),
        )

        tools_group.setLayout(tools_form)
        layout.addWidget(tools_group)

        # -----------------------------------------------------
        # Thumbnail section (ML-061, 2026-07-23)
        # -----------------------------------------------------

        thumbnail_group = QGroupBox("Thumbnail")
        thumbnail_form = QFormLayout()

        self.thumbnail_logo_path_edit = QLineEdit()
        thumbnail_form.addRow(
            "Logo image (composited bottom-right):",
            self._path_row(
                self.thumbnail_logo_path_edit,
                is_folder=False,
                file_filter="Images (*.png *.jpg *.jpeg *.bmp)",
            ),
        )

        thumbnail_group.setLayout(thumbnail_form)
        layout.addWidget(thumbnail_group)

        # Push all sections to the top rather than spreading out to
        # fill the scroll area's height.
        layout.addStretch()

        scroll_area.setWidget(content_widget)
        outer_layout.addWidget(scroll_area)

        # -----------------------------------------------------
        # OK / Cancel - deliberately on outer_layout, NOT inside the
        # scroll area, so they're always visible regardless of how
        # tall the content above grows or how small the screen is.
        # -----------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer_layout.addWidget(buttons)

        self._load_current_values()

    def _path_row(
        self,
        line_edit: QLineEdit,
        is_folder: bool,
        file_filter: str | None = None,
    ) -> QHBoxLayout:
        """
        Wraps a QLineEdit with a "Browse..." button that opens a
        file or folder picker and fills the field - returned as a
        layout so it can be dropped straight into a QFormLayout
        row. file_filter (e.g. "Images (*.png *.jpg *.jpeg)") is
        only used for file pickers, not folder pickers.
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
                    self,
                    "Select File",
                    line_edit.text(),
                    file_filter or "",
                )
            if chosen:
                line_edit.setText(chosen)

        browse_button.clicked.connect(_browse)
        row.addWidget(browse_button)

        return row

    def _lut_row(self, line_edit: QLineEdit) -> QHBoxLayout:
        """
        Wraps a QLineEdit with a "Browse..." button for picking a
        camera LUT file (ML-072). Unlike _path_row(), the value
        this stores is NOT a filesystem path - Resolve's
        MediaPoolItem.SetClipProperty("Input LUT", ...) expects the
        value exactly as it appears in Resolve's own LUT
        browser/dropdown, which is the LUT's path RELATIVE to
        Resolve's LUT folder (e.g. "GoPro/HERO13_Look.cube"), not
        an absolute filesystem path.

        The browse dialog opens directly inside Resolve's LUT
        folder by default, and the chosen file's path is converted
        to be relative to that folder before being written into
        the field - so browsing from inside that folder (or a
        subfolder of it) produces a value that will actually work.

        If the person picks a file OUTSIDE Resolve's LUT folder
        (e.g. it hasn't been installed into Resolve yet), this
        falls back to just the filename - which only works if that
        exact file also happens to sit directly in Resolve's LUT
        folder root. In that case the field is filled in but the
        underlying LUT still needs to actually be moved/copied into
        Resolve's LUT folder for the value to mean anything to
        Resolve.
        """

        row = QHBoxLayout()
        row.addWidget(line_edit)

        browse_button = QPushButton("Browse...")

        def _browse():

            lut_root = (
                Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
                / "Blackmagic Design"
                / "DaVinci Resolve"
                / "Support"
                / "LUT"
            )

            start_dir = str(lut_root) if lut_root.exists() else (
                line_edit.text()
            )

            chosen, _ = QFileDialog.getOpenFileName(
                self,
                "Select LUT File",
                start_dir,
                "LUT files (*.cube *.3dl)",
            )

            if not chosen:
                return

            chosen_path = Path(chosen)

            try:
                relative = chosen_path.relative_to(lut_root)
                value = str(relative).replace("\\", "/")
            except ValueError:
                # Not under Resolve's LUT folder - see docstring
                # above for what this fallback means in practice.
                value = chosen_path.name

            line_edit.setText(value)

        browse_button.clicked.connect(_browse)
        row.addWidget(browse_button)

        return row

    def _update_ai_field_visibility(self):
        """
        Shows only the fields relevant to whichever provider is
        currently selected - the Groq API key/model fields have no
        effect at all while Ollama is selected (and vice versa), so
        hiding the irrelevant ones avoids confusion about which
        fields are actually "live".
        """

        is_groq = self.groq_radio.isChecked()
        self.ollama_model_edit.setVisible(not is_groq)
        self.groq_api_key_edit.setVisible(is_groq)
        self.groq_model_edit.setVisible(is_groq)

    def _reset_intelliscript_guidance(self):
        """
        Restores DEFAULT_INTELLISCRIPT_GUIDANCE into the text box -
        does NOT save anything to disk by itself, same as any other
        field here; only OK actually writes it.
        """
        from sba_resolve.core.services.app_settings import (
            DEFAULT_INTELLISCRIPT_GUIDANCE,
        )

        self.intelliscript_guidance_edit.setPlainText(
            DEFAULT_INTELLISCRIPT_GUIDANCE
        )

    def _reset_youtube_metadata_guidance(self):
        """
        Restores DEFAULT_YOUTUBE_METADATA_GUIDANCE into the text box -
        does NOT save anything to disk by itself, same as any other
        field here; only OK actually writes it.
        """
        from sba_resolve.core.services.app_settings import (
            DEFAULT_YOUTUBE_METADATA_GUIDANCE,
        )

        self.youtube_metadata_guidance_edit.setPlainText(
            DEFAULT_YOUTUBE_METADATA_GUIDANCE
        )

    def _load_current_values(self):

        self.dark_theme_check.setChecked(load_theme() == "dark")

        self.timeline_creation_check.setChecked(
            load_timeline_creation_enabled()
        )
        self.multicam_audio_sync_check.setChecked(
            load_multicam_audio_sync_enabled()
        )
        self.resolve_module_path_edit.setText(load_resolve_module_path())

        camera_luts = load_camera_luts()
        self.camera_lut_gopro_edit.setText(camera_luts.get("GoPro", ""))
        self.camera_lut_dji_edit.setText(camera_luts.get("DJI", ""))
        self.camera_lut_insta360_edit.setText(
            camera_luts.get("Insta360", "")
        )

        gap_settings = load_gap_compression_settings()
        self.gap_enabled_check.setChecked(gap_settings.enabled)
        self.gap_threshold_spin.setValue(
            gap_settings.gap_threshold_seconds
        )
        self.gap_compressed_spin.setValue(
            gap_settings.compressed_gap_seconds
        )

        if load_ai_provider() == "groq":
            self.groq_radio.setChecked(True)
        else:
            self.ollama_radio.setChecked(True)
        self.ollama_model_edit.setText(load_ollama_model())
        self.groq_api_key_edit.setText(load_groq_api_key())
        self.groq_model_edit.setText(load_groq_model())
        self._update_ai_field_visibility()

        self.intelliscript_guidance_edit.setPlainText(
            load_intelliscript_guidance()
        )

        self.youtube_metadata_guidance_edit.setPlainText(
            load_youtube_metadata_guidance()
        )

        self.openrouteservice_api_key_edit.setText(
            load_openrouteservice_api_key()
        )

        self.exiftool_path_edit.setText(load_exiftool_path())

        self.thumbnail_logo_path_edit.setText(load_thumbnail_logo_path())

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
            "camera_luts": {
                manufacturer: value
                for manufacturer, value in (
                    ("GoPro", self.camera_lut_gopro_edit.text().strip()),
                    ("DJI", self.camera_lut_dji_edit.text().strip()),
                    (
                        "Insta360",
                        self.camera_lut_insta360_edit.text().strip(),
                    ),
                )
                if value
            },
            "gap_compression": {
                "enabled": self.gap_enabled_check.isChecked(),
                "gap_threshold_seconds": self.gap_threshold_spin.value(),
                "compressed_gap_seconds": (
                    self.gap_compressed_spin.value()
                ),
            },
            "ai_provider": "groq" if self.groq_radio.isChecked() else (
                "ollama"
            ),
            "ollama_model": self.ollama_model_edit.text().strip() or (
                "llama3.2"
            ),
            "groq_api_key": self.groq_api_key_edit.text(),
            "groq_model": self.groq_model_edit.text().strip() or (
                "llama-3.3-70b-versatile"
            ),
            "intelliscript_prompt_guidance": (
                self.intelliscript_guidance_edit.toPlainText().strip()
            ),
            "youtube_metadata_prompt_guidance": (
                self.youtube_metadata_guidance_edit.toPlainText().strip()
            ),
            "openrouteservice_api_key": (
                self.openrouteservice_api_key_edit.text()
            ),
            "exiftool": self.exiftool_path_edit.text(),
            "thumbnail_logo_path": self.thumbnail_logo_path_edit.text(),
        }

        save_settings(updates)

        # GUI-011: apply immediately, so switching theme is visible
        # right away rather than only on next launch.
        apply_theme(theme_value)

        self.accept()