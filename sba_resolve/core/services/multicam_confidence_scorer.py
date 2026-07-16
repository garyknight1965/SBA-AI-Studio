"""
============================================================
SBA AI Studio
Multicam Confidence Scorer
Version : 1.0.0
Sprint  : ML-031
============================================================

Scores each MulticamCandidate by how much its automatic camera
sync can be trusted, based on the WEAKEST (lowest-confidence)
timestamp among its contributing clips - not an average.

Rationale: if one clip's timestamp is a rough file-modified-time
guess, the whole candidate is only as trustworthy as that guess,
even if every other clip has a solid metadata timestamp. Averaging
would let one bad clip hide behind a good one.
"""

from __future__ import annotations

from typing import Iterable

from sba_resolve.core.models.multicam_candidate import MulticamCandidate

# Confidence (0.0-1.0) at or above which a candidate is trusted
# enough to sync automatically, with no editor review.
AUTO_SYNC_THRESHOLD = 0.90

# Confidence (0.0-1.0) at or above which a candidate is worth
# flagging for a quick editor review, rather than manual sync
# from scratch.
REVIEW_THRESHOLD = 0.60


class MulticamConfidenceScorer:
    """
    Assigns a 0.0-1.0 confidence score to each MulticamCandidate,
    driven by its least-trustworthy contributing clip.
    """

    def score(
        self,
        candidates: Iterable[MulticamCandidate],
    ) -> None:
        """
        Score each candidate in place (sets `.confidence`).
        """

        for candidate in candidates:
            candidate.confidence = self._score_one(candidate)

    # -----------------------------------------------------

    def _score_one(self, candidate: MulticamCandidate) -> float:

        if not candidate.clips:
            return 0.0

        weakest = min(
            getattr(clip, "timestamp_confidence", 0) or 0
            for clip in candidate.clips
        )

        return round(weakest / 100, 4)

    # -----------------------------------------------------

    @staticmethod
    def status_for(confidence: float) -> str:
        """
        Map a 0.0-1.0 confidence score to an editor-facing status:

            Auto-sync : safe to sync automatically
            Review    : sync it, but flag for a quick look
            Manual    : don't trust it, leave to the editor
        """

        if confidence >= AUTO_SYNC_THRESHOLD:
            return "Auto-sync"

        if confidence >= REVIEW_THRESHOLD:
            return "Review"

        return "Manual"
