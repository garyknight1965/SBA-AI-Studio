"""
============================================================
SBA AI Studio
Apply Camera LUTs To Timeline
Version : 1.0.0
Sprint  : ML-072b (replaces the reverted ML-072 Media Pool
          approach - see create_timeline.py's docstring note)
============================================================

Applies a per-camera-manufacturer LUT to every clip on the
CURRENT Resolve timeline, via TimelineItem.SetLUT(nodeIndex,
lutPath) - NOT MediaPoolItem.SetClipProperty("Input LUT", ...),
which was confirmed via live testing to be silently rejected by
Resolve's scripting API regardless of value format (see
create_timeline.py's ML-072 docstring note for the full story).

This is a SEPARATE, manually-triggered action - not part of
create_timeline()'s automatic flow - because GoPro/DJI/Insta360
footage in this project is imported but NOT auto-placed onto any
timeline; Gary drags it onto a timeline himself, whenever he's
ready, and only THEN does a TimelineItem exist for
SetLUT() to act on. Run this after you've finished placing clips
on a timeline (any timeline - it always acts on whichever one is
currently open/active in Resolve).

Camera detection reuses the same MediaFile.camera_profile the
rest of the app already computed (via MetadataMapper /
CameraRecognitionEngine at scan time) - matched to each timeline
item by filename, the same lookup pattern
create_timeline.py's _build_imported_lookup() uses for Media Pool
clips. A timeline item whose filename isn't found among
context.project_data["media_objects"] (e.g. a clip added to the
timeline some other way, outside this app's own scan) is silently
skipped, same reasoning as everywhere else in this app: a LUT is
cosmetic grading setup, never worth failing over.

Per app_settings.load_camera_luts()'s docstring, each configured
value must be exactly what Resolve's own LUT browser shows - a
LUT-folder-relative path (e.g. "GoPro/HERO13_Look.cube"), the same
value the Settings dialog's "Browse..." button already produces.
TimelineItem.SetLUT() accepts either an absolute path or a path
relative to Resolve's own LUT folder, per Resolve's own scripting
documentation - unlike the Media Pool clip property, this one is
confirmed (via multiple independent third-party scripts found
during troubleshooting) to actually work.

A camera manufacturer with no entry in camera_luts is left
untouched - opt-in per camera, same as the reverted Media Pool
version. Clips whose camera wasn't recognized, or that have no
LUT configured for their manufacturer, are silently skipped and
counted, not raised.
"""

from __future__ import annotations

from sba_resolve.core.services.app_settings import load_camera_luts


def apply_camera_luts_to_timeline(context) -> dict:
    """
    Applies each configured camera LUT (app_settings.
    load_camera_luts()) to every clip on Resolve's CURRENT
    timeline, matched to a camera via the MediaFile objects
    already scanned for this project (context.project_data
    ["media_objects"]).

    Returns:
        {
            "applied": int,
            "skipped_no_lut_configured": int,
            "skipped_camera_unknown": int,
            "skipped_clip_not_found": int,
            "failed": int,
        }

    Prints a summary line, same style as every other Resolve
    command in this app. Never raises for a missing/unset LUT,
    an unrecognized camera, or an individual SetLUT() failure -
    this is cosmetic grading setup, never worth blocking the
    person's work over. Does raise RuntimeError if there is no
    current timeline at all, since that means there is nothing
    to act on and the person likely ran this before placing any
    clips.
    """

    project = context.project

    if project is None:
        raise RuntimeError("Resolve project is not initialized.")

    timeline = project.GetCurrentTimeline()

    if timeline is None:
        raise RuntimeError(
            "No current timeline in Resolve. Open (or create) the "
            "timeline you've placed clips on before running this."
        )

    camera_luts = load_camera_luts()

    counts = {
        "applied": 0,
        "skipped_no_lut_configured": 0,
        "skipped_camera_unknown": 0,
        "skipped_clip_not_found": 0,
        "failed": 0,
    }

    print("=" * 60)
    print("Apply Camera LUTs To Timeline")
    print("=" * 60)
    print(f"Timeline : {timeline.GetName()}")

    if not camera_luts:
        print(
            "No camera LUTs configured in Settings - nothing to do."
        )
        return counts

    media_files_by_filename = {
        media_file.filename.lower(): media_file
        for media_file in context.project_data.get("media_objects", [])
    }

    track_count = timeline.GetTrackCount("video")

    for track_index in range(1, track_count + 1):

        for timeline_item in timeline.GetItemListInTrack(
            "video", track_index
        ):

            _apply_one_clip(
                timeline_item, media_files_by_filename, camera_luts, counts
            )

    print()
    print(
        f"Applied              : {counts['applied']}\n"
        f"No LUT configured    : {counts['skipped_no_lut_configured']}\n"
        f"Camera unrecognized  : {counts['skipped_camera_unknown']}\n"
        f"Clip not found       : {counts['skipped_clip_not_found']}\n"
        f"Failed               : {counts['failed']}"
    )

    return counts


def _apply_one_clip(
    timeline_item, media_files_by_filename, camera_luts, counts
) -> None:
    """
    Applies (or skips) a LUT for one TimelineItem, updating
    `counts` in place. Split out from the main loop just to keep
    apply_camera_luts_to_timeline() readable - not meant to be
    called on its own.
    """

    try:
        media_pool_item = timeline_item.GetMediaPoolItem()
        clip_name = (
            media_pool_item.GetClipProperty().get("Clip Name")
            or media_pool_item.GetClipProperty().get("File Name")
            if media_pool_item
            else None
        )
    except Exception:
        clip_name = None

    if not clip_name:
        counts["skipped_clip_not_found"] += 1
        return

    media_file = media_files_by_filename.get(clip_name.lower())

    if media_file is None:
        counts["skipped_clip_not_found"] += 1
        return

    profile = getattr(media_file, "camera_profile", None)

    if profile is None or not profile.is_known():
        counts["skipped_camera_unknown"] += 1
        return

    lut_reference = camera_luts.get(profile.manufacturer.value)

    if not lut_reference:
        counts["skipped_no_lut_configured"] += 1
        return

    try:
        # Node 1 - the first node in this clip's grade. A fresh
        # clip with no existing grade has exactly one (empty)
        # node, so this is always valid; if Gary has already
        # started grading a clip by hand, this still targets node
        # 1 specifically (the earliest node), never overwriting
        # whatever nodes he's added after it.
        success = timeline_item.SetLUT(1, lut_reference)
    except Exception:
        success = False

    if success:
        counts["applied"] += 1
    else:
        counts["failed"] += 1
