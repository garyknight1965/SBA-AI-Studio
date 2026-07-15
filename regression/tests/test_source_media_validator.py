"""
============================================================
SBA AI Studio
Source Media Validator Regression Test
ML-014
Version : 1.0.0
============================================================

Verifies:
- Recognised original-camera filenames (GoPro GX/GH,
  Insta360 VID_ export, DJI) are accepted.
- Images, GoPro .THM sidecars, audio-only files, and files in
  a rejected folder (e.g. Proxy) are rejected with a specific
  reason.
- An .mp4 that doesn't match any known camera pattern (e.g. a
  Resolve render) is rejected as unrecognised, not silently
  accepted.
- MediaValidationReport counts and groups reasons correctly.
"""

from __future__ import annotations

from pathlib import Path

from regression.base_test import BaseRegressionTest


class SourceMediaValidatorRegressionTest(BaseRegressionTest):

    name = "Source Media Validator (ML-014)"

    category = "Scanner"

    description = (
        "Verify Source Media Validation accepts recognised "
        "original-camera filenames and rejects everything else "
        "with an explained reason."
    )

    def _make_media(self, relative_path: str):

        from sba_resolve.core.models.media_file import MediaFile

        path = Path(relative_path)

        return MediaFile(
            filename=path.name,
            full_path=Path("/fake") / path,
            relative_path=path,
            extension=path.suffix.lower(),
            size=1024,
        )

    def run(self) -> None:

        from sba_resolve.core.services.source_media_validator import (
            SourceMediaValidator,
        )

        media_files = [
            # Accepted: GoPro chaptered footage.
            self._make_media("GX010066.MP4"),
            self._make_media("gh010167.mp4"),
            # Accepted: Insta360 Studio export naming.
            self._make_media(
                "VID_20260617_134554_00_003_185033.mp4"
            ),
            # Accepted: DJI original video naming.
            self._make_media("DJI_0001.MP4"),
            # Accepted: confirmed DJI Fly app export naming.
            self._make_media(
                "dji_fly_20260625_151204_0001_"
                "1782454141375_video_beautify.mp4"
            ),
            # Rejected: DJI Fly app's own cache/preview file.
            self._make_media(
                "dji_fly_20260626_095729_0_"
                "1782674091079_video_cache.mp4"
            ),
            # Rejected: image.
            self._make_media("GX010067.jpg"),
            # Rejected: GoPro thumbnail sidecar.
            self._make_media("GX010066.THM"),
            # Rejected: audio-only.
            self._make_media("voiceover.wav"),
            # Rejected: located in a Proxy folder.
            self._make_media("Proxy/GX010066.MP4"),
            # Rejected: .mp4 that matches no known camera
            # pattern - almost certainly a render/export, not
            # raw footage.
            self._make_media("Sunday Ride Master.mp4"),
            # Rejected: cloud-sync/file-manager soft-delete marker.
            self._make_media(
                ".trashed-1781209346-GX010223.MP4"
            ),
        ]

        validator = SourceMediaValidator()

        report = validator.validate(media_files)

        if report.accepted_count != 5:
            raise RuntimeError(
                f"Expected 5 accepted files, got "
                f"{report.accepted_count}: "
                f"{[m.filename for m in report.accepted]}"
            )

        accepted_names = {m.filename for m in report.accepted}

        expected_accepted = {
            "GX010066.MP4",
            "gh010167.mp4",
            "VID_20260617_134554_00_003_185033.mp4",
            "DJI_0001.MP4",
            "dji_fly_20260625_151204_0001_"
            "1782454141375_video_beautify.mp4",
        }

        if accepted_names != expected_accepted:
            raise RuntimeError(
                f"Accepted set mismatch. Expected "
                f"{expected_accepted}, got {accepted_names}."
            )

        if report.rejected_count != 7:
            raise RuntimeError(
                f"Expected 7 rejected files, got "
                f"{report.rejected_count}: "
                f"{[m.filename for m in report.rejected]}"
            )

        rejected_by_name = {
            item.filename: item.reason for item in report.rejected
        }

        dji_cache_name = (
            "dji_fly_20260626_095729_0_"
            "1782674091079_video_cache.mp4"
        )

        if "cache" not in rejected_by_name[dji_cache_name].lower():
            raise RuntimeError(
                "Expected the DJI Fly cache file to be rejected "
                f"as a cache/preview file, got reason: "
                f"{rejected_by_name[dji_cache_name]!r}"
            )

        if "image" not in rejected_by_name["GX010067.jpg"].lower():
            raise RuntimeError(
                "Expected GX010067.jpg to be rejected as an "
                f"image, got reason: "
                f"{rejected_by_name['GX010067.jpg']!r}"
            )

        if "thumbnail" not in rejected_by_name["GX010066.THM"].lower():
            raise RuntimeError(
                "Expected GX010066.THM to be rejected as a "
                f"thumbnail sidecar, got reason: "
                f"{rejected_by_name['GX010066.THM']!r}"
            )

        if "audio" not in rejected_by_name["voiceover.wav"].lower():
            raise RuntimeError(
                "Expected voiceover.wav to be rejected as "
                f"audio-only, got reason: "
                f"{rejected_by_name['voiceover.wav']!r}"
            )

        if "proxy" not in rejected_by_name["GX010066.MP4"].lower():
            raise RuntimeError(
                "Expected the Proxy-folder GX010066.MP4 to be "
                f"rejected for its folder, got reason: "
                f"{rejected_by_name['GX010066.MP4']!r}"
            )

        render_reason = rejected_by_name["Sunday Ride Master.mp4"]

        if "doesn't match" not in render_reason and (
            "does not match" not in render_reason
        ):
            raise RuntimeError(
                "Expected 'Sunday Ride Master.mp4' to be "
                f"rejected as an unrecognised pattern, got "
                f"reason: {render_reason!r}"
            )

        trashed_name = ".trashed-1781209346-GX010223.MP4"

        if "trash" not in rejected_by_name[trashed_name].lower():
            raise RuntimeError(
                "Expected the .trashed- file to be rejected as "
                f"a soft-delete marker, got reason: "
                f"{rejected_by_name[trashed_name]!r}"
            )

        # Report grouping/count sanity.
        reason_counts = report.rejected_by_reason()

        if sum(reason_counts.values()) != report.rejected_count:
            raise RuntimeError(
                "rejected_by_reason() counts don't sum to "
                "rejected_count."
            )
