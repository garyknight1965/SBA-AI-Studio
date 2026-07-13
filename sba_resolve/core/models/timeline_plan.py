"""
============================================================
SBA AI Studio
Timeline Plan
Version : 1.0.0
Sprint : ML-009
============================================================

Represents a timeline before it is created in DaVinci Resolve.

A TimelinePlan is generated from a MediaLibrary and contains
an ordered collection of TimelineTracks and TimelineClips.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sba_resolve.core.models.media_file import MediaFile


@dataclass(slots=True)
class TimelineClip:
    """
    Represents one clip in a timeline.
    """

    media: MediaFile

    start_time: float = 0.0

    duration: float = 0.0

    track: int = 1

    selected: bool = True


@dataclass(slots=True)
class TimelineTrack:
    """
    Represents one timeline track.
    """

    name: str

    clips: list[TimelineClip] = field(default_factory=list)

    def add(self, clip: TimelineClip) -> None:
        self.clips.append(clip)

    @property
    def clip_count(self) -> int:
        return len(self.clips)


@dataclass(slots=True)
class TimelineDay:
    """
    Groups clips captured on the same day.
    """

    day: date

    tracks: list[TimelineTrack] = field(default_factory=list)

    def add_track(self, track: TimelineTrack) -> None:
        self.tracks.append(track)


class TimelinePlan:
    """
    Complete timeline description.
    """

    def __init__(self) -> None:

        self.days: list[TimelineDay] = []

        self.source_files: list[Path] = []

    def add_day(self, day: TimelineDay) -> None:
        self.days.append(day)

    @property
    def total_days(self) -> int:
        return len(self.days)

    @property
    def total_tracks(self) -> int:
        return sum(len(day.tracks) for day in self.days)

    @property
    def total_clips(self) -> int:
        return sum(
            len(track.clips)
            for day in self.days
            for track in day.tracks
        )

    def summary(self) -> dict:

        return {
            "days": self.total_days,
            "tracks": self.total_tracks,
            "clips": self.total_clips,
        }