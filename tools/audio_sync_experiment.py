"""
============================================================
SBA AI Studio
Audio Sync Experiment (diagnostic tool - NOT yet part of the
main pipeline)
============================================================

Tests whether cross-correlating two clips' audio - in different
frequency bands - can find a reliable time offset between them,
BEFORE committing engineering effort to building this into the
real Planning Engine.

Hypothesis being tested: even when a helmet cam (narration + lav
mic) and a second camera (ambient/wind noise only) have no
shared narration to sync against, both microphones still pick up
the bike's engine/road noise at essentially the same instant.
That shared signal might be recoverable by isolating the right
frequency band - but it's genuinely uncertain which band that is
until tested against real footage, since wind noise on
unprotected mics is ALSO often strongest at low frequencies and
could mask engine noise rather than the reverse. This tool tests
several bands and reports which one (if any) shows a real,
strong correlation peak - rather than assuming one upfront.

Usage:
    python tools/audio_sync_experiment.py clip_a.mp4 clip_b.mp4 [--seconds 60]

Requires ffmpeg (for audio extraction - already installed) and
numpy (for the correlation math - not currently a dependency of
the main application; install with:
    pip install numpy --break-system-packages
if it's missing).
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np

# Hz. Plenty of headroom for engine/wind/road-noise-range
# analysis (all well under 2kHz), keeps extracted data small and
# correlation fast.
SAMPLE_RATE = 4000


def extract_audio(path: Path, seconds: float, offset: float = 0.0) -> np.ndarray:
    """
    Extracts up to `seconds` of mono audio from `path` via
    ffmpeg, starting at `offset` seconds into the file, resampled
    to SAMPLE_RATE, as a float32 numpy array in [-1, 1].
    """

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


def bandpass(signal: np.ndarray, low_hz: float, high_hz: float) -> np.ndarray:
    """
    Simple FFT-based band-pass filter (zeroes frequencies outside
    [low_hz, high_hz]). Good enough for this experiment - not a
    production-grade filter design.
    """

    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / SAMPLE_RATE)

    mask = (freqs >= low_hz) & (freqs <= high_hz)

    spectrum = spectrum * mask

    return np.fft.irfft(spectrum, n=len(signal))


def best_offset(
    signal_a: np.ndarray,
    signal_b: np.ndarray,
) -> tuple[float, float]:
    """
    Cross-correlates two signals via FFT and returns
    (offset_seconds, normalized_peak_strength).

    Positive offset means signal_a's content occurs LATER than
    signal_b's - i.e. signal_a is the delayed one (shift signal_a
    earlier, or signal_b later, by this many seconds to align
    them). Negative means the reverse. Verified against synthetic
    audio with a known ground-truth offset before this tool was
    used on any real footage.
    """

    fft_size = 1

    while fft_size < len(signal_a) + len(signal_b) - 1:
        fft_size *= 2

    fa = np.fft.rfft(signal_a, fft_size)
    fb = np.fft.rfft(signal_b, fft_size)

    correlation = np.fft.irfft(fa * np.conj(fb), fft_size)

    # Reorder so index 0 is zero lag and negative lags (signal_b
    # earlier than signal_a) come first, not wrapped at the end.
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


BANDS = {
    "Broadband (no filter)": (0.0, SAMPLE_RATE / 2 - 1),
    "Low (engine rumble, 20-200Hz)": (20.0, 200.0),
    "Mid (200-800Hz)": (200.0, 800.0),
    "High (800-2000Hz)": (800.0, 2000.0),
}


def run_experiment(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
) -> None:

    print()
    print(f"{'Band':<32} {'Offset (s)':>12} {'Strength':>10}")
    print("-" * 56)

    for label, (low, high) in BANDS.items():

        filtered_a = (
            bandpass(audio_a, low, high) if low > 0 else audio_a
        )
        filtered_b = (
            bandpass(audio_b, low, high) if low > 0 else audio_b
        )

        offset, strength = best_offset(filtered_a, filtered_b)

        print(f"{label:<32} {offset:>12.3f} {strength:>10.3f}")

    print()
    print(
        "Higher |strength| = a stronger, more trustworthy "
        "correlation peak."
    )
    print(
        "As a rough guide: above ~0.3-0.5 usually means a real "
        "alignment; near 0 means no clear match in that band."
    )
    print(
        "If every band scores low, engine-noise correlation "
        "likely isn't reliable enough for this footage - that's "
        "a real, useful answer too."
    )
    print()
    print(
        "Offset sign: POSITIVE means clip_a's shared content "
        "happens LATER than clip_b's (clip_a is the delayed one). "
        "NEGATIVE means clip_a's content happens EARLIER."
    )


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Test audio cross-correlation sync between two clips, "
            "across several frequency bands."
        )
    )
    parser.add_argument("clip_a")
    parser.add_argument("clip_b")
    parser.add_argument(
        "--seconds",
        type=float,
        default=60.0,
        help="How many seconds of audio to analyse (default 60).",
    )
    parser.add_argument(
        "--offset-a",
        type=float,
        default=0.0,
        help="Seconds into clip_a to start extraction (default 0).",
    )
    parser.add_argument(
        "--offset-b",
        type=float,
        default=0.0,
        help="Seconds into clip_b to start extraction (default 0).",
    )

    args = parser.parse_args()

    print("=" * 56)
    print("Audio Sync Experiment (diagnostic tool)")
    print("=" * 56)
    print(f"Extracting {args.seconds:.0f}s of audio from both clips...")

    try:
        audio_a = extract_audio(
            Path(args.clip_a), args.seconds, args.offset_a
        )
        audio_b = extract_audio(
            Path(args.clip_b), args.seconds, args.offset_b
        )
    except subprocess.CalledProcessError as exc:
        print(f"ffmpeg failed: {exc}")
        return 1
    except FileNotFoundError:
        print(
            "ffmpeg not found on PATH - open a NEW terminal "
            "window if you just installed it."
        )
        return 1

    if len(audio_a) == 0 or len(audio_b) == 0:
        print(
            "One or both clips produced no audio - check the "
            "file paths and that these clips actually have an "
            "audio track."
        )
        return 1

    print(f"  {args.clip_a}: {len(audio_a) / SAMPLE_RATE:.1f}s extracted")
    print(f"  {args.clip_b}: {len(audio_b) / SAMPLE_RATE:.1f}s extracted")

    run_experiment(audio_a, audio_b)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
