"""
============================================================
SBA AI Studio
Multicam Confidence Scorer Regression Test
ML-031
Version : 1.0.0
============================================================

Verifies MulticamConfidenceScorer:
- Uses the MINIMUM (not average) contributing clip confidence -
  a candidate with one low-confidence clip must not look
  trustworthy just because its other clip is high-confidence.
- A candidate with no clips at all scores 0.0 rather than
  raising.
- status_for() maps confidence to the right band (Auto-sync /
  Review / Manual).
"""

from __future__ import annotations

from pathlib import Path

from regression.base_test import BaseRegressionTest


class MulticamConfidenceScorerRegressionTest(BaseRegressionTest):

    name = "Multicam Confidence Scorer (ML-031)"

    category = "Planning"

    description = (
        "Verify multicam confidence uses the weakest "
        "contributing clip (not an average), and that status "
        "bands map correctly."
    )

    def _make_media(self, filename, timestamp_confidence):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            timestamp_confidence=timestamp_confidence,
        )

    def run(self) -> None:

        from sba_resolve.core.models.multicam_candidate import (
            MulticamCandidate,
        )
        from sba_resolve.core.services.multicam_confidence_scorer import (
            AUTO_SYNC_THRESHOLD,
            REVIEW_THRESHOLD,
            MulticamConfidenceScorer,
        )

        # --------------------------------------------------
        # 1. Weakest-link scoring: one high-confidence clip
        #    (95) and one low-confidence clip (35, matching a
        #    GoPro-filename-style fallback) must score based on
        #    the LOW one, not an average (which would be 65).
        # --------------------------------------------------

        high_confidence_clip = self._make_media("clip1.mp4", 95)
        low_confidence_clip = self._make_media("clip2.mp4", 35)

        candidate = MulticamCandidate(
            start_frame=0,
            end_frame=1000,
            ride_day=1,
            clips=[high_confidence_clip, low_confidence_clip],
        )

        scorer = MulticamConfidenceScorer()

        scorer.score([candidate])

        if candidate.confidence != 0.35:
            raise RuntimeError(
                f"Expected weakest-link confidence 0.35 (35/100), "
                f"got {candidate.confidence!r} - scoring may be "
                f"averaging instead of taking the minimum."
            )

        # --------------------------------------------------
        # 2. Two high-confidence clips -> high confidence.
        # --------------------------------------------------

        clip_a = self._make_media("clip3.mp4", 95)
        clip_b = self._make_media("clip4.mp4", 100)

        good_candidate = MulticamCandidate(
            start_frame=0,
            end_frame=1000,
            ride_day=1,
            clips=[clip_a, clip_b],
        )

        scorer.score([good_candidate])

        if good_candidate.confidence != 0.95:
            raise RuntimeError(
                f"Expected confidence 0.95, got "
                f"{good_candidate.confidence!r}."
            )

        # --------------------------------------------------
        # 3. No clips at all -> 0.0, not a crash.
        # --------------------------------------------------

        empty_candidate = MulticamCandidate(
            start_frame=0, end_frame=1000, ride_day=1, clips=[]
        )

        scorer.score([empty_candidate])

        if empty_candidate.confidence != 0.0:
            raise RuntimeError(
                f"Expected 0.0 confidence for a candidate with no "
                f"clips, got {empty_candidate.confidence!r}."
            )

        # --------------------------------------------------
        # 4. Status band mapping.
        # --------------------------------------------------

        if MulticamConfidenceScorer.status_for(0.95) != "Auto-sync":
            raise RuntimeError(
                "0.95 should map to 'Auto-sync'."
            )

        if MulticamConfidenceScorer.status_for(0.75) != "Review":
            raise RuntimeError("0.75 should map to 'Review'.")

        if MulticamConfidenceScorer.status_for(0.35) != "Manual":
            raise RuntimeError("0.35 should map to 'Manual'.")

        # Exact boundary values.
        if (
            MulticamConfidenceScorer.status_for(AUTO_SYNC_THRESHOLD)
            != "Auto-sync"
        ):
            raise RuntimeError(
                "The exact AUTO_SYNC_THRESHOLD value should map "
                "to 'Auto-sync' (>=), not 'Review'."
            )

        if (
            MulticamConfidenceScorer.status_for(REVIEW_THRESHOLD)
            != "Review"
        ):
            raise RuntimeError(
                "The exact REVIEW_THRESHOLD value should map to "
                "'Review' (>=), not 'Manual'."
            )
