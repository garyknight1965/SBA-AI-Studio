"""
============================================================
SBA AI Studio
Audio Sync Experiment (Batch)
============================================================

Runs the audio correlation experiment (see audio_sync_experiment.py)
against EVERY multicam candidate the Planning Engine already
found - so you don't have to know or guess which clips overlap.

Reuses the real pipeline (scan -> validate -> GoPro chapter
correction -> GPS -> Planning Engine -> MulticamDetector) to find
candidate pairs, then extracts the actual overlapping portion of
each clip's audio (not just the start of the file) and runs the
same band-by-band correlation test as the single-pair tool.

Usage:
    python tools/audio_sync_batch.py "D:\\Movies\\12-05-2026 castle" [--seconds 45]

Requires ffmpeg and numpy (see audio_sync_experiment.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audio_sync_experiment import BANDS, bandpass, best_offset, extract_audio

from sba_resolve.core.media_import_pipeline import MediaImportPipeline
from sba_resolve.core.services.multicam_confidence_scorer import (
    MulticamConfidenceScorer,
)
from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)


def main() -> int:

    if len(sys.argv) < 2:
        print(
            'Usage: python tools/audio_sync_batch.py "<footage_folder>" '
            "[--seconds 45]"
        )
        return 1

    folder = Path(sys.argv[1])

    seconds = 45.0

    if "--seconds" in sys.argv:
        idx = sys.argv.index("--seconds")
        seconds = float(sys.argv[idx + 1])

    if not folder.exists():
        print(f"Folder not found: {folder}")
        return 1

    print("=" * 60)
    print("Scanning footage")
    print("=" * 60)

    pipeline = MediaImportPipeline()

    media = pipeline.import_folder(folder)

    if pipeline.last_validation_report:
        pipeline.last_validation_report.print_report()

    if not media:
        print("No usable media found.")
        return 1

    print()
    print("=" * 60)
    print("Running Planning Engine")
    print("=" * 60)

    result = TimelinePlanningService(fps=25.0).plan(media)

    if not result.multicam_candidates:
        print(
            "No multicam candidates detected - nothing to test. "
            "This means the Planning Engine didn't find any "
            "overlapping-camera windows in this footage at all."
        )
        return 0

    print(f"Found {len(result.multicam_candidates)} multicam candidate(s).")

    # Map each MediaFile to its placement, so we know each clip's
    # position on the shared frame timeline (needed to work out
    # WHERE within each individual clip file the overlap actually
    # starts, rather than always testing from each file's own
    # beginning).
    placement_by_media_id = {
        id(p.media_file): p for p in result.placements
    }

    fps = 25.0

    scorer = MulticamConfidenceScorer()

    print()
    print("=" * 60)
    print(f"Testing audio correlation ({seconds:.0f}s per candidate)")
    print("=" * 60)

    for index, candidate in enumerate(result.multicam_candidates, start=1):

        clips = list(candidate.clips)

        if len(clips) < 2:
            continue

        # Test the first two distinct-camera clips in this
        # candidate - covers the common 2-camera case directly;
        # a 3+ camera overlap would need pairwise testing, out of
        # scope for this quick batch experiment.
        clip_a, clip_b = clips[0], clips[1]

        placement_a = placement_by_media_id.get(id(clip_a))
        placement_b = placement_by_media_id.get(id(clip_b))

        if placement_a is None or placement_b is None:
            continue

        offset_a = max(
            0.0,
            (candidate.start_frame - placement_a.record_frame) / fps,
        )
        offset_b = max(
            0.0,
            (candidate.start_frame - placement_b.record_frame) / fps,
        )

        print()
        print(f"--- Candidate {index}: {clip_a.filename} <-> {clip_b.filename} ---")
        print(
            f"  Timestamp-based confidence: {candidate.confidence:.0%} "
            f"({scorer.status_for(candidate.confidence)})"
        )

        try:
            audio_a = extract_audio(clip_a.full_path, seconds, offset_a)
            audio_b = extract_audio(clip_b.full_path, seconds, offset_b)
        except Exception as exc:
            print(f"  Could not extract audio: {exc}")
            continue

        if len(audio_a) == 0 or len(audio_b) == 0:
            print("  One or both clips produced no audio - skipping.")
            continue

        best_band_label = None
        best_strength = 0.0
        best_band_offset = 0.0

        for label, (low, high) in BANDS.items():

            filtered_a = bandpass(audio_a, low, high) if low > 0 else audio_a
            filtered_b = bandpass(audio_b, low, high) if low > 0 else audio_b

            band_offset, strength = best_offset(filtered_a, filtered_b)

            if abs(strength) > abs(best_strength):
                best_strength = strength
                best_band_label = label
                best_band_offset = band_offset

        print(
            f"  Best audio match: {best_band_label} | "
            f"offset {best_band_offset:+.3f}s | "
            f"strength {best_strength:.3f}"
        )

        if abs(best_strength) >= 0.5:
            print("  -> Strong match - likely a reliable audio sync point.")
        elif abs(best_strength) >= 0.3:
            print("  -> Moderate match - worth a manual check before trusting.")
        else:
            print("  -> Weak/no match - audio correlation unreliable here.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
