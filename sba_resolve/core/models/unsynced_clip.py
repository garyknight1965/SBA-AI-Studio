"""
============================================================
SBA AI Studio
Unsynced Clip
ML-054 Step 2b
Version: 1.0.0
============================================================

Represents a clip that was part of a detected multicam
candidate but could not be verified via audio sync (see
MulticamAudioSyncService) - never guessed onto the timeline.
Resolve-independent: the Resolve Builder layer (create_timeline.py,
Step 2c) uses these to build a named empty placeholder track and
filename markers per camera, for manual sync in Resolve.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UnsyncedClip:
    """
    A clip that was excluded from automatic timeline placement
    because its audio sync could not be verified.
    """

    camera_name: str

    clip_name: str

    reason: str

    # Which ride day this clip belongs to. Populated by
    # TimelinePlanningService from the originating placement.
    # Used at the Resolve Builder boundary (create_timeline.py)
    # to group unsynced clips onto the correct per-day timeline.
    ride_day: int = 0