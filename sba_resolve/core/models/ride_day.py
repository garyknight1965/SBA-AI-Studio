from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RideDay:

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