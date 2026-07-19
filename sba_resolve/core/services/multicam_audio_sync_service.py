"""
============================================================
SBA AI Studio
Multicam Audio Sync Service
ML-054 Step 2a
Version: 1.3.0
============================================================

Productionizes the FFT band-cross-correlation approach proven
out in tools/audio_sync_experiment.py and tools/audio_sync_batch.py
into a real Planning Engine service.

Given a MulticamDetector candidate (a group of clips from
different cameras overlapping in real time) and the placements
already computed for those clips, attempts to verify - via
shared engine/road/ambient audio - whether the clips are
genuinely synchronized, and if so, computes a corrected
record_frame for every non-reference clip in the group.

Design principle (per Gary, ML-054): never guess. A clip is
only ever corrected/placed based on audio sync if the
correlation strength clears STRONG_THRESHOLD.

Version 1.1.0 fixed a real bug: paired Insta360 dual-lens views
(same physical camera, front/back lens - guaranteed the same
moment by construction, already resolved and distinguished by
Insta360ViewAssigner via a non-empty camera_profile.view label)
were incorrectly being sent through audio-sync verification. A
candidate group where every clip already carries a resolved view
label is skipped entirely - trusted and left unchanged.

Version 1.2.0 added mark_all_unsynced(), used when audio sync
was disabled via config - candidate-scoped, every non-reference
clip in a detected multicam candidate marked as needing manual
sync, no audio work attempted.

Version 1.3.0 (2026-07-19) adds is_paired_view_group() - a
public wrapper around the existing paired-view check, so
TimelinePlanningService's stricter "only GoPro HERO13 Black
auto-places" default mode (which now applies project-wide, not
just to multicam-candidate clips - see Gary's 2026-07-19 scope
change) can reuse this check without reaching into a private
method. mark_all_unsynced() remains in the codebase as a
documented, still-available alternative, but is no longer called
by TimelinePlanningService's default path.

Reference clip selection always prefers GoPro HERO13 Black
(lav mic - Gary's most trustworthy/anchor camera) when
evaluate() or mark_all_unsynced() run (i.e. when
enable_multicam_audio_sync is True).

No Resolve API code lives here - only local file/audio analysis
via ffmpeg and media_file.full_path, consistent with the rest of
the Planning Engine.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 4000

STRONG_THRESHOLD = 0.5

DEFAULT_SECONDS = 45.0

BANDS = {
    "Broadband (no filter)": (0.0, SAMPLE_RATE / 2 - 1),
    "Low (engine rumble, 20-200Hz)": (20.0, 200.0),
    "Mid (200-800Hz)": (200.0, 800.0),
    "High (800-2000Hz)": (800.0, 2000.0),
}

DEFAULT_CAMERA_ORDER = [
    "GoPro HERO13 Black",
    "GoPro HERO8 Black",
    "Insta360 X3",
    "DJI Flip",
    "Unknown Camera",
]


@dataclass
class ClipSyncResult:
    """
    The audio-sync verdict for one clip within one multicam
    candidate group.
    """

    media_file: object
    is_reference: bool
    synced: bool
    corrected_record_frame: int | None
    offset_seconds: float | None
    strength: float
    band: str | None
    reason: str


class MulticamAudioSyncService:
    """
    Attempts audio-based sync verification for multicam
    candidate groups, returning a per-clip verdict.
    """

    def __init__(
        self,
        camera_order: list[str] | None = None,
        seconds: float = DEFAULT_SECONDS,
        strong_threshold: float = STRONG_THRESHOLD,
    ) -> None:

        self.camera_order = camera_order or list(DEFAULT_CAMERA_ORDER)
        self.seconds = seconds
        self.strong_threshold = strong_threshold

    def evaluate(
        self,
        candidates,
        placements,
        fps: float,
    ) -> dict[int, ClipSyncResult]:
        """
        Evaluates every multicam candidate group and returns a
        mapping of id(media_file) -> ClipSyncResult, covering
        every clip that appears in at least one candidate.
        """

        placement_by_media_id = {
            id(placement.media_file): placement
            for placement in placements
        }

        results: dict[int, ClipSyncResult] = {}

        for candidate in candidates:

            clips = list(candidate.clips)

            if len(clips) < 2:
                continue

            if self._is_already_paired_view_group(clips):
                results.update(
                    self._trust_all_clips(clips, placement_by_media_id)
                )
                continue

            candidate_results = self._evaluate_candidate(
                clips, placement_by_media_id, fps
            )

            results.update(candidate_results)

        return results

    def mark_all_unsynced(
        self,
        candidates,
        placements,
    ) -> dict[int, ClipSyncResult]:
        """
        Candidate-scoped placeholder marking (no audio work
        attempted). Kept available but NOT called by
        TimelinePlanningService's default path as of 2026-07-19 -
        superseded there by the stricter, project-wide
        "only GoPro HERO13 Black auto-places" rule. Still usable
        directly if that candidate-scoped behaviour is ever
        wanted again.
        """

        placement_by_media_id = {
            id(placement.media_file): placement
            for placement in placements
        }

        results: dict[int, ClipSyncResult] = {}

        for candidate in candidates:

            clips = list(candidate.clips)

            if len(clips) < 2:
                continue

            if self._is_already_paired_view_group(clips):
                results.update(
                    self._trust_all_clips(clips, placement_by_media_id)
                )
                continue

            reference = self._choose_reference(clips)

            reference_placement = placement_by_media_id.get(id(reference))

            results[id(reference)] = ClipSyncResult(
                media_file=reference,
                is_reference=True,
                synced=True,
                corrected_record_frame=(
                    reference_placement.record_frame
                    if reference_placement
                    else None
                ),
                offset_seconds=0.0,
                strength=0.0,
                band=None,
                reason="Reference clip - position trusted as-is.",
            )

            for clip in clips:

                if clip is reference:
                    continue

                results[id(clip)] = ClipSyncResult(
                    media_file=clip,
                    is_reference=False,
                    synced=False,
                    corrected_record_frame=None,
                    offset_seconds=None,
                    strength=0.0,
                    band=None,
                    reason=(
                        "Audio sync is disabled "
                        "(enable_multicam_audio_sync is false in "
                        "config/settings.json) - clip needs manual "
                        "sync in Resolve."
                    ),
                )

        return results

    def is_paired_view_group(self, clips) -> bool:
        """
        Public wrapper around _is_already_paired_view_group(), so
        other services (e.g. TimelinePlanningService's
        HERO13-only default mode) can reuse this check without
        reaching into a private method.
        """

        return self._is_already_paired_view_group(clips)

    @staticmethod
    def _is_already_paired_view_group(clips) -> bool:

        if len(clips) < 2:
            return False

        for clip in clips:
            profile = getattr(clip, "camera_profile", None)
            view = getattr(profile, "view", None) if profile else None
            if not view:
                return False

        return True

    @staticmethod
    def _trust_all_clips(
        clips, placement_by_media_id: dict
    ) -> dict[int, "ClipSyncResult"]:

        results: dict[int, ClipSyncResult] = {}

        for clip in clips:

            placement = placement_by_media_id.get(id(clip))

            results[id(clip)] = ClipSyncResult(
                media_file=clip,
                is_reference=True,
                synced=True,
                corrected_record_frame=(
                    placement.record_frame if placement else None
                ),
                offset_seconds=0.0,
                strength=1.0,
                band=None,
                reason=(
                    "Already-paired Insta360 dual-lens view - same "
                    "physical camera, trusted by construction, never "
                    "audio-evaluated."
                ),
            )

        return results

    def _evaluate_candidate(
        self,
        clips,
        placement_by_media_id: dict,
        fps: float,
    ) -> dict[int, ClipSyncResult]:

        reference = self._choose_reference(clips)

        reference_placement = placement_by_media_id.get(id(reference))

        results: dict[int, ClipSyncResult] = {}

        results[id(reference)] = ClipSyncResult(
            media_file=reference,
            is_reference=True,
            synced=True,
            corrected_record_frame=(
                reference_placement.record_frame
                if reference_placement
                else None
            ),
            offset_seconds=0.0,
            strength=1.0,
            band=None,
            reason="Reference clip - position trusted as-is.",
        )

        for clip in clips:

            if clip is reference:
                continue

            results[id(clip)] = self._evaluate_pair(
                reference, clip, placement_by_media_id, fps
            )

        return results

    def _choose_reference(self, clips):

        for camera_name in self.camera_order:
            for clip in clips:
                display_name = (
                    getattr(clip, "camera_display_name", None)
                    or getattr(clip, "camera_model", None)
                )
                if display_name == camera_name:
                    return clip

        return clips[0]

    def _evaluate_pair(
        self,
        reference,
        clip,
        placement_by_media_id: dict,
        fps: float,
    ) -> ClipSyncResult:

        reference_placement = placement_by_media_id.get(id(reference))
        clip_placement = placement_by_media_id.get(id(clip))

        if reference_placement is None or clip_placement is None:
            return ClipSyncResult(
                media_file=clip,
                is_reference=False,
                synced=False,
                corrected_record_frame=None,
                offset_seconds=None,
                strength=0.0,
                band=None,
                reason="No placement found for this clip or its reference.",
            )

        overlap_start_frame = max(
            reference_placement.record_frame,
            clip_placement.record_frame,
        )

        reference_offset_seconds = max(
            0.0,
            (overlap_start_frame - reference_placement.record_frame) / fps,
        )
        clip_offset_seconds = max(
            0.0,
            (overlap_start_frame - clip_placement.record_frame) / fps,
        )

        try:
            reference_audio = self._extract_audio(
                reference.full_path, self.seconds, reference_offset_seconds
            )
            clip_audio = self._extract_audio(
                clip.full_path, self.seconds, clip_offset_seconds
            )
        except Exception as exc:
            return ClipSyncResult(
                media_file=clip,
                is_reference=False,
                synced=False,
                corrected_record_frame=None,
                offset_seconds=None,
                strength=0.0,
                band=None,
                reason=f"Audio extraction failed: {exc}",
            )

        if len(reference_audio) == 0 or len(clip_audio) == 0:
            return ClipSyncResult(
                media_file=clip,
                is_reference=False,
                synced=False,
                corrected_record_frame=None,
                offset_seconds=None,
                strength=0.0,
                band=None,
                reason="One or both clips produced no audio.",
            )

        best_band_label = None
        best_strength = 0.0
        best_band_offset = 0.0

        for label, (low, high) in BANDS.items():

            filtered_reference = (
                self._bandpass(reference_audio, low, high)
                if low > 0
                else reference_audio
            )
            filtered_clip = (
                self._bandpass(clip_audio, low, high)
                if low > 0
                else clip_audio
            )

            offset, strength = self._best_offset(
                filtered_reference, filtered_clip
            )

            if abs(strength) > abs(best_strength):
                best_strength = strength
                best_band_label = label
                best_band_offset = offset

        if abs(best_strength) < self.strong_threshold:
            return ClipSyncResult(
                media_file=clip,
                is_reference=False,
                synced=False,
                corrected_record_frame=None,
                offset_seconds=best_band_offset,
                strength=best_strength,
                band=best_band_label,
                reason=(
                    f"Correlation strength {best_strength:.3f} "
                    f"(band: {best_band_label}) below the "
                    f"{self.strong_threshold:.2f} threshold required "
                    f"for automatic placement."
                ),
            )

        total_offset_seconds = (
            reference_offset_seconds
            - clip_offset_seconds
            + best_band_offset
        )

        corrected_record_frame = round(
            reference_placement.record_frame
            + (total_offset_seconds * fps)
        )

        return ClipSyncResult(
            media_file=clip,
            is_reference=False,
            synced=True,
            corrected_record_frame=corrected_record_frame,
            offset_seconds=best_band_offset,
            strength=best_strength,
            band=best_band_label,
            reason=(
                f"Synced via audio correlation (band: "
                f"{best_band_label}, strength {best_strength:.3f})."
            ),
        )

    @staticmethod
    def _extract_audio(
        path: Path, seconds: float, offset: float = 0.0
    ) -> np.ndarray:

        command = [
            "ffmpeg", "-y",
            "-ss", str(offset),
            "-i", str(path),
            "-t", str(seconds),
            "-ac", "1",
            "-ar", str(SAMPLE_RATE),
            "-f", "f32le",
            "-",
        ]

        result = subprocess.run(
            command, capture_output=True, check=True
        )

        return np.frombuffer(result.stdout, dtype=np.float32)

    @staticmethod
    def _bandpass(
        signal: np.ndarray, low_hz: float, high_hz: float
    ) -> np.ndarray:

        spectrum = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(len(signal), d=1.0 / SAMPLE_RATE)

        mask = (freqs >= low_hz) & (freqs <= high_hz)

        spectrum = spectrum * mask

        return np.fft.irfft(spectrum, n=len(signal))

    @staticmethod
    def _best_offset(
        signal_a: np.ndarray,
        signal_b: np.ndarray,
    ) -> tuple[float, float]:

        fft_size = 1

        while fft_size < len(signal_a) + len(signal_b) - 1:
            fft_size *= 2

        fa = np.fft.rfft(signal_a, fft_size)
        fb = np.fft.rfft(signal_b, fft_size)

        correlation = np.fft.irfft(fa * np.conj(fb), fft_size)

        correlation = np.concatenate(
            (
                correlation[-(len(signal_b) - 1):],
                correlation[: len(signal_a)],
            )
        )

        peak_index = int(np.argmax(np.abs(correlation)))

        lag_samples = peak_index - (len(signal_b) - 1)

        offset_seconds = lag_samples / SAMPLE_RATE

        norm = np.sqrt(np.sum(signal_a ** 2) * np.sum(signal_b ** 2))

        strength = float(correlation[peak_index] / norm) if norm > 0 else 0.0

        return offset_seconds, strength