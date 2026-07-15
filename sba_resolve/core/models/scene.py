"""
============================================================
SBA AI Studio
Scene
ML-020-001
Version : 1.0.0 Alpha
============================================================

Represents one detected Scene within a Ride Day.

A Scene is the smallest editing unit: a distinct real-world
stop or stretch of riding (per the project's Ride Reconstruction
vision - "Leaving Hotel", "Fuel Stop", "Coffee Stop", "Mountain
Pass", "Castle Visit", "Hotel Arrival").

SceneDetector (which produces these) detects scene BOUNDARIES
from recording gaps - it does not attempt to label WHAT a scene
is. Labelling requires signals this project doesn't have yet
(GPS, motion/audio analysis), so scenes are numbered, not named,
until a future labelling layer exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Scene:

    ride_day: int

    index: int

    start_time: datetime

    end_time: datetime

    clips: list = field(default_factory=list)

    @property
    def duration(self):
        return self.end_time - self.start_time

    @property
    def clip_count(self):
        return len(self.clips)
