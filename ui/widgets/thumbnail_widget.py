"""
============================================================
SBA AI Studio
Thumbnail Panel
ML-061 / ML-062 (scrollable layout)
Version : 1.1.0
============================================================

Lets the channel owner generate a real YouTube thumbnail from this
project's own footage:

1. "Suggest Frames" pulls a handful of candidate still frames from
   across the project's clips (see ThumbnailFrameExtractor -
   deterministic, evenly-spaced selection, NOT an AI guess at which
   frame "looks best" - that's a judgement call left to Gary).
2. Clicking a candidate composites it live with the overlay text and
   (if configured in Settings) the channel logo, and shows the
   result.
3. "Save Thumbnail..." writes the composited image to a chosen PNG
   file.

The overlay text field is pre-filled externally (see MainWindow) from
YouTubeMetadataGenerator's own thumbnail_text suggestion (ML-059)
when available, but stays fully editable here - editing it live
updates the preview.

ML-062 (2026-07-23): 5 candidate previews plus a 480-wide composited
preview image made this panel taller than its dock/window area,
running off the bottom of the screen instead of scrolling - the same
problem the Settings dialog and YouTube Metadata panel already hit
and were fixed for. Fixed the same way here: everything except the
Suggest Frames button/status label now lives inside a QScrollArea.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sba_resolve.core.services.thumbnail_generator import ThumbnailComposer

CANDIDATE_PREVIEW_SIZE = 160
PREVIEW_DISPLAY_WIDTH = 480


class ThumbnailWidget(QWidget):

    # Emitted when the user clicks "Suggest Frames" - the owner
    # (MainWindow) is responsible for running the worker and calling
    # set_candidates()/set_error() back on this widget.
    suggest_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._composer = ThumbnailComposer()
        self._candidates = []
        self._selected_index = None
        self._composed_image = None
        self._logo_path = ""

        self.suggest_button = QPushButton("Suggest Thumbnail Frames")
        self.suggest_button.clicked.connect(self.suggest_requested.emit)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.candidates_row = QHBoxLayout()

        self.text_field = QLineEdit()
        self.text_field.setPlaceholderText(
            "Thumbnail overlay text (pre-filled from generated "
            "YouTube metadata when available)"
        )
        self.text_field.textChanged.connect(self._update_preview)

        self.preview_label = QLabel("Pick a suggested frame to preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(270)

        self.save_button = QPushButton("Save Thumbnail...")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._on_save_clicked)

        group = QGroupBox("Thumbnail")
        group_layout = QVBoxLayout()
        group_layout.addLayout(self.candidates_row)
        group_layout.addWidget(self.text_field)
        group_layout.addWidget(self.preview_label)
        group_layout.addWidget(self.save_button)
        group.setLayout(group_layout)

        # ML-062: the candidate row + preview image can grow taller
        # than the dock/window area - put it in a scroll area so it
        # scrolls internally instead of running off the bottom of the
        # screen. Suggest Frames / status label stay outside the
        # scroll area, always visible at the top.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setWidget(group)

        layout = QVBoxLayout(self)
        layout.addWidget(self.suggest_button)
        layout.addWidget(self.status_label)
        layout.addWidget(scroll_area)

    def set_logo_path(self, logo_path: str) -> None:
        """
        Called externally (MainWindow, from Settings) whenever the
        configured logo path might have changed - e.g. right before
        generation, so the preview always reflects the current
        setting.
        """
        self._logo_path = logo_path or ""
        self._update_preview()

    def set_suggested_text(self, text: str) -> None:
        """
        Pre-fills the overlay text field from an external source
        (YouTubeMetadataGenerator's thumbnail_text) - only if the
        field is currently empty, so this never clobbers something
        Gary already typed himself.
        """
        if not self.text_field.text().strip() and text:
            self.text_field.setText(text)

    def set_generating(self, is_generating: bool) -> None:
        self.suggest_button.setEnabled(not is_generating)
        if is_generating:
            self.status_label.setText(
                "Extracting candidate frames from the footage..."
            )

    def set_candidates(self, candidates: list) -> None:
        """
        candidates: list[ThumbnailCandidate] (see
        thumbnail_generator.py) - each with a real BGR frame in
        .image.
        """

        if candidates:
            self.status_label.setText(
                f"{len(candidates)} candidate frame(s) - click one "
                f"to preview."
            )

        self._candidates = candidates
        self._selected_index = None
        self._composed_image = None
        self.save_button.setEnabled(False)
        self.preview_label.setText("Pick a suggested frame to preview")
        self.preview_label.setPixmap(QPixmap())

        while self.candidates_row.count():
            item = self.candidates_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, candidate in enumerate(candidates):

            button = QPushButton()
            button.setFixedSize(
                CANDIDATE_PREVIEW_SIZE, CANDIDATE_PREVIEW_SIZE
            )
            button.setIconSize(button.size() * 0.9)

            pixmap = self._frame_to_qpixmap(candidate.image)

            if pixmap is not None:
                button.setIcon(QIcon(pixmap))

            button.clicked.connect(
                lambda checked=False, i=index: self._select_candidate(i)
            )

            self.candidates_row.addWidget(button)

    def set_error(self, message: str) -> None:
        self.status_label.setText(f"Could not suggest frames: {message}")

    def clear(self) -> None:
        self.text_field.clear()
        self.set_candidates([])
        self.status_label.setText("")

    def _select_candidate(self, index: int) -> None:
        self._selected_index = index
        self._update_preview()

    def _update_preview(self) -> None:

        if self._selected_index is None or not self._candidates:
            return

        candidate = self._candidates[self._selected_index]

        composed = self._composer.compose(
            candidate.image,
            text=self.text_field.text(),
            logo_path=self._logo_path or None,
        )

        self._composed_image = composed

        pixmap = self._pil_to_qpixmap(composed)

        self.preview_label.setPixmap(
            pixmap.scaledToWidth(
                PREVIEW_DISPLAY_WIDTH, Qt.SmoothTransformation
            )
        )

        self.save_button.setEnabled(True)

    def _on_save_clicked(self) -> None:

        if self._composed_image is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Thumbnail", "thumbnail.png", "PNG Image (*.png)"
        )

        if not path:
            return

        self._composer.save(self._composed_image, path)

        self.status_label.setText(f"Thumbnail saved to {path}")

    def _frame_to_qpixmap(self, frame_image):
        """
        Converts a candidate's raw BGR numpy frame directly to a
        small QPixmap for the candidate button's icon, without
        going through the full compositing pipeline (no text/logo -
        this is just a plain preview of the unedited frame).
        """

        try:
            composed = self._composer.compose(frame_image, text="")
        except Exception:
            return None

        pixmap = self._pil_to_qpixmap(composed)

        return pixmap.scaled(
            CANDIDATE_PREVIEW_SIZE,
            CANDIDATE_PREVIEW_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    @staticmethod
    def _pil_to_qpixmap(pil_image) -> QPixmap:

        rgb_image = pil_image.convert("RGB")

        data = rgb_image.tobytes("raw", "RGB")

        qimage = QImage(
            data,
            rgb_image.width,
            rgb_image.height,
            rgb_image.width * 3,
            QImage.Format_RGB888,
        )

        # QImage doesn't copy the buffer by default - it's about to
        # go out of scope, so make an explicit copy before wrapping
        # it in a QPixmap.
        return QPixmap.fromImage(qimage.copy())