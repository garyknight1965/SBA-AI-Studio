"""
============================================================
SBA AI Studio
Insta360 View Assigner
ML-015-001
Version : 1.0.0 Alpha
============================================================

Insta360 cameras (X3 confirmed; likely other dual-lens models
too) can export more than one file for the exact same real
recording moment - e.g. two lens views of one clip. These
correctly share an identical resolved capture timestamp (they
really were captured simultaneously), but the Planning Engine
currently has no way to tell them apart: every Insta360 file
gets the same camera identity ("Insta360 X3"), so paired views
collide onto the same timeline track instead of stacking on
separate tracks as two synced views of the same moment.

This service groups Insta360 files by their VID_ filename
prefix (date + time + sequence + chapter, everything except the
final distinguishing number) and, whenever a group has more than
one file, assigns each member a distinct CameraProfile.view
("View 1", "View 2", ...). CameraProfile.display_name then
folds this into the camera identity (e.g. "Insta360 X3 (View
1)"), which PlanningSegmentBuilder and TimelinePlacementBuilder
already use for segment grouping and track assignment - so no
change is needed there.

Files with a unique (ungrouped) VID_ prefix are left untouched
(view stays "", so they display as plain "Insta360 X3").
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from sba_resolve.core.models.camera_profile import CameraManufacturer


class Insta360ViewAssigner:
    """
    Assigns distinct view labels to Insta360 files that share
    the same recording moment, so they get separate timeline
    tracks instead of colliding.
    """

    # VID_{date}_{time}_{seq}_{chapter}_{trailing}.mp4
    # Grouping key is everything up to (not including) the final
    # trailing number - that's the part observed to differ
    # between paired views of the same moment.
    _GROUP_PATTERN = re.compile(
        r"^VID_(\d{8})_(\d{6})_(\d+)_(\d+)_",
        re.IGNORECASE,
    )

    def assign(self, media_files: Iterable) -> None:
        """
        Mutates `media.camera_profile.view` in place for every
        Insta360 file that shares its VID_ group prefix with at
        least one other file in `media_files`.
        """

        groups: dict[str, list] = defaultdict(list)

        for media in media_files:

            if not self._is_insta360(media):
                continue

            key = self._group_key(media.filename)

            if key is None:
                continue

            groups[key].append(media)

        for members in groups.values():

            if len(members) < 2:
                # Single file for this moment - leave view blank,
                # it displays as plain "Insta360 X3".
                continue

            # Stable, deterministic ordering so the same files
            # always get the same view label across runs.
            members.sort(key=lambda m: m.filename.lower())

            for index, media in enumerate(members, start=1):
                media.camera_profile.view = f"View {index}"

    @staticmethod
    def _is_insta360(media) -> bool:

        profile = getattr(media, "camera_profile", None)

        if profile is None:
            return False

        return profile.manufacturer == CameraManufacturer.INSTA360

    @classmethod
    def _group_key(cls, filename: str) -> str | None:

        match = cls._GROUP_PATTERN.match(filename)

        if not match:
            return None

        return "_".join(match.groups())
