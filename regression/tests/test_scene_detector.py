"""
============================================================
SBA AI Studio
Scene Detector Regression Test
ML-020
Version : 1.0.0
============================================================

Verifies SceneDetector:
- A gap smaller than the threshold keeps clips in the same
  Scene.
- A gap larger than the threshold starts a new Scene.
- Scenes are numbered sequentially within a Ride Day, starting
  at 1.
- ride_day is stamped correctly onto every Scene.
- Clips out of chronological order are still grouped correctly
  (SceneDetector sorts internally).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class SceneDetectorRegressionTest(BaseRegressionTest):

    name = "Scene Detector (ML-020)"

    category = "Planning"

    description = (
        "Verify SceneDetector groups clips into Scenes using a "
        "smaller gap threshold than Ride Day detection, and "
        "numbers them sequentially per day."
    )

    def _make_media(self, filename, created):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            created=created,
            duration="60",
        )

    def run(self) -> None:

        from sba_resolve.core.services.scene_detector import SceneDetector

        day_start = datetime(2026, 7, 1, 9, 0, 0)

        clips = [
            # Scene 1: two clips 90s apart (small gap).
            self._make_media("clip1.mp4", day_start),
            self._make_media(
                "clip2.mp4", day_start + timedelta(seconds=90)
            ),
            # 20 minute gap (fuel stop) - well above the 5 minute
            # default threshold - new Scene.
            self._make_media(
                "clip3.mp4",
                day_start + timedelta(seconds=90, minutes=20),
            ),
            # 3 minute gap - below the 5 minute threshold - stays
            # in Scene 2.
            self._make_media(
                "clip4.mp4",
                day_start + timedelta(seconds=90, minutes=23),
            ),
            # 40 minute gap (coffee stop) - new Scene.
            self._make_media(
                "clip5.mp4",
                day_start + timedelta(seconds=90, minutes=63),
            ),
        ]

        # Shuffle input order - SceneDetector must sort internally.
        shuffled = [clips[2], clips[0], clips[4], clips[1], clips[3]]

        detector = SceneDetector()

        scenes = detector.detect(shuffled, ride_day=3)

        if len(scenes) != 3:
            raise RuntimeError(
                f"Expected 3 scenes, got {len(scenes)}: "
                f"{[s.clip_count for s in scenes]}"
            )

        if [s.index for s in scenes] != [1, 2, 3]:
            raise RuntimeError(
                f"Expected sequential scene indices [1, 2, 3], "
                f"got {[s.index for s in scenes]}."
            )

        if any(s.ride_day != 3 for s in scenes):
            raise RuntimeError(
                "Expected every scene to be stamped ride_day=3, "
                f"got {[s.ride_day for s in scenes]}."
            )

        if scenes[0].clip_count != 2:
            raise RuntimeError(
                f"Expected Scene 1 to have 2 clips (clip1, "
                f"clip2), got {scenes[0].clip_count}."
            )

        if scenes[1].clip_count != 2:
            raise RuntimeError(
                f"Expected Scene 2 to have 2 clips (clip3, "
                f"clip4 - the 3 minute gap must NOT split them), "
                f"got {scenes[1].clip_count}."
            )

        if scenes[2].clip_count != 1:
            raise RuntimeError(
                f"Expected Scene 3 to have 1 clip (clip5), got "
                f"{scenes[2].clip_count}."
            )

        # Custom threshold: a smaller max_gap should split the 3
        # minute gap too.
        strict_detector = SceneDetector(max_gap=timedelta(minutes=2))

        strict_scenes = strict_detector.detect(shuffled, ride_day=1)

        if len(strict_scenes) != 4:
            raise RuntimeError(
                f"With a 2 minute threshold, expected 4 scenes "
                f"(the 3 minute gap should now split), got "
                f"{len(strict_scenes)}."
            )
