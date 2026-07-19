"""
============================================================
SBA AI Studio
Multicam Audio Sync Service Regression Test
ML-054 Step 2a
Version: 1.0.0
============================================================

Verifies:
- The pure correlation math (_best_offset) correctly recovers a
  known, self-correlated signal (offset ~0, strength ~1.0) and
  correctly recovers the approximate magnitude of a known
  shifted-copy offset - a basic sanity check on the math ported
  from audio_sync_experiment.py, not a full re-verification of
  that already-proven tool's sign convention.
- Reference clip selection always prefers GoPro HERO13 Black
  when present, falls back to HERO8, then to the first clip
  when no camera matches the known order at all.
- A clip whose audio extraction fails (or returns no audio) is
  reported as sync-failed with a clear reason, never raises.
- The reference clip in an evaluated candidate always keeps its
  original record_frame - the "anchor" position is never
  audio-corrected, per Gary's design decision (2026-07-19).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

from regression.base_test import BaseRegressionTest


class MulticamAudioSyncServiceRegressionTest(BaseRegressionTest):

    name = "Multicam Audio Sync Service (ML-054 Step 2a)"

    category = "Planning"

    description = (
        "Verify the productionized audio correlation math, "
        "reference-clip selection order, and safe failure "
        "handling for the new MulticamAudioSyncService."
    )

    def _make_media(self, filename, camera_model, created, duration=60):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            camera_model=camera_model,
            created=created,
            duration=str(duration),
        )

    def _make_placement(self, media, record_frame):

        from sba_resolve.core.models.timeline_placement import (
            TimelinePlacement,
        )

        placement = TimelinePlacement(media_file=media)
        placement.record_frame = record_frame

        return placement

    def run(self) -> None:

        from sba_resolve.core.services.multicam_audio_sync_service import (
            MulticamAudioSyncService,
            SAMPLE_RATE,
        )

        service = MulticamAudioSyncService(seconds=2.0)

        # --------------------------------------------------
        # 1. Self-correlation sanity check: a signal correlated
        #    with an identical copy of itself must recover an
        #    offset of ~0 with strength ~1.0. This is the most
        #    basic possible check on the ported correlation math
        #    and is unambiguous regardless of sign convention.
        # --------------------------------------------------

        rng = np.random.default_rng(1)

        signal = rng.standard_normal(2000).astype(np.float32)

        offset, strength = service._best_offset(signal, signal)

        if abs(offset) > (5 / SAMPLE_RATE):
            raise RuntimeError(
                "Self-correlation must recover ~0 offset, got "
                f"{offset!r}"
            )

        if strength < 0.95:
            raise RuntimeError(
                "Self-correlation must recover strength close to "
                f"1.0, got {strength!r}"
            )

        # --------------------------------------------------
        # 2. Shifted-copy check: correlating a signal against a
        #    window of itself shifted by a known number of
        #    samples must recover approximately that magnitude of
        #    offset, with a clearly high strength (large shared
        #    overlap). Only the MAGNITUDE is asserted here - sign
        #    convention is inherited unchanged from
        #    audio_sync_experiment.py, which already documents
        #    itself as verified against synthetic ground truth.
        # --------------------------------------------------

        base = rng.standard_normal(2400).astype(np.float32)

        known_lag_samples = 120

        window_a = base[known_lag_samples:known_lag_samples + 2000]
        window_b = base[0:2000]

        offset_b, strength_b = service._best_offset(window_a, window_b)

        expected_offset_seconds = known_lag_samples / SAMPLE_RATE

        if abs(abs(offset_b) - expected_offset_seconds) > 0.01:
            raise RuntimeError(
                "Shifted-copy correlation should recover an offset "
                f"magnitude near {expected_offset_seconds:.4f}s, got "
                f"{offset_b!r}"
            )

        if abs(strength_b) < 0.7:
            raise RuntimeError(
                "Shifted-copy correlation with large shared overlap "
                f"should show high strength, got {strength_b!r}"
            )

        # --------------------------------------------------
        # 3. Reference clip selection order.
        # --------------------------------------------------

        moment = datetime(2026, 1, 1, 10, 0, 0)

        hero13 = self._make_media(
            "hero13.mp4", "GoPro HERO13 Black", moment
        )
        hero8 = self._make_media(
            "hero8.mp4", "GoPro HERO8 Black", moment
        )
        x3 = self._make_media("x3.mp4", "Insta360 X3", moment)

        chosen = service._choose_reference([hero8, x3, hero13])

        if chosen is not hero13:
            raise RuntimeError(
                "HERO13 must be chosen as reference when present, "
                f"got {getattr(chosen, 'filename', chosen)!r}"
            )

        chosen_no_hero13 = service._choose_reference([x3, hero8])

        if chosen_no_hero13 is not hero8:
            raise RuntimeError(
                "HERO8 must be chosen as reference when HERO13 is "
                f"absent, got "
                f"{getattr(chosen_no_hero13, 'filename', chosen_no_hero13)!r}"
            )

        unknown_a = self._make_media("unknown_a.mp4", "Weird Cam", moment)
        unknown_b = self._make_media("unknown_b.mp4", "Weird Cam", moment)

        chosen_fallback = service._choose_reference([unknown_a, unknown_b])

        if chosen_fallback is not unknown_a:
            raise RuntimeError(
                "With no recognised camera in the group, the first "
                "clip in the list must be chosen as a fallback "
                f"reference, got "
                f"{getattr(chosen_fallback, 'filename', chosen_fallback)!r}"
            )

        # --------------------------------------------------
        # 4. Full evaluate() path: reference keeps its original
        #    record_frame untouched, and a clip whose audio
        #    extraction fails is reported as sync-failed with a
        #    clear reason, never raises.
        # --------------------------------------------------

        from sba_resolve.core.models.multicam_candidate import (
            MulticamCandidate,
        )

        placement_hero13 = self._make_placement(hero13, record_frame=0)
        placement_hero8 = self._make_placement(hero8, record_frame=50)

        candidate = MulticamCandidate(
            start_frame=0,
            end_frame=1000,
            confidence=1.0,
            reason="Test candidate",
        )
        candidate.add_clip(hero13)
        candidate.add_clip(hero8)

        # hero8/hero13 point at nonexistent fake paths, so real
        # ffmpeg extraction will fail - exercising the safe
        # failure path without needing real media files.
        results = service.evaluate(
            [candidate],
            [placement_hero13, placement_hero8],
            fps=25.0,
        )

        reference_result = results[id(hero13)]

        if not reference_result.is_reference:
            raise RuntimeError(
                "Reference clip's result must be marked is_reference."
            )

        if reference_result.corrected_record_frame != 0:
            raise RuntimeError(
                "Reference clip's record_frame must be left "
                "untouched (0), got "
                f"{reference_result.corrected_record_frame!r}"
            )

        other_result = results[id(hero8)]

        if other_result.synced:
            raise RuntimeError(
                "A clip with an unreadable/nonexistent audio file "
                "must be reported as sync-failed, not synced."
            )

        if not other_result.reason:
            raise RuntimeError(
                "A sync-failed clip must always have a non-empty "
                "reason explaining why."
            )