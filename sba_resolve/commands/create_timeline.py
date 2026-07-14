"""
============================================================
SBA AI Studio
Resolve Command
Create Timeline
RES-006F.2 - Planning-Driven Multi-Track Timeline
============================================================

Builds the Resolve timeline using the ML-011 Planning Engine's
PlanningResult, instead of a single naive sequential append.

Each camera gets its own stable video track, and every clip is
placed at its real, gap-preserving record_frame position.
Resolve's AppendToTimeline "recordFrame" key was confirmed to
support exact frame placement via
tools/resolve_gap_placement_test.py.

No Resolve API code lives in the Planning Engine itself
(sba_resolve.core.services.timeline_planning_service and its
dependencies) - this module is the boundary where planning
output is translated into real Resolve API calls.
"""

from __future__ import annotations

from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)


def create_timeline(context):
    """
    Create a Resolve timeline from imported media.

    Uses the Planning Engine (TimelinePlanningService) to
    determine per-camera track assignment and frame-exact,
    gap-preserving clip placement, then executes it against
    the Resolve API.
    """

    project = context.project
    media_pool = context.media_pool

    if project is None or media_pool is None:
        raise RuntimeError("Resolve project is not initialized.")

    imported = getattr(context, "imported_items", [])

    if not imported:
        print("No imported clips available.")
        return None

    timeline_name = (
        context.project_data.get("timeline_name")
        or f"{context.project_data['project_name']} Master"
    )

    print("=" * 60)
    print("Create Timeline")
    print("=" * 60)
    print(f"Timeline : {timeline_name}")

    # -----------------------------------------------------
    # Find or create the timeline
    # -----------------------------------------------------

    timeline = None

    for index in range(1, project.GetTimelineCount() + 1):
        existing = project.GetTimelineByIndex(index)
        if existing and existing.GetName() == timeline_name:
            timeline = existing
            print("Using existing timeline.")
            break

    if timeline is None:
        timeline = media_pool.CreateEmptyTimeline(timeline_name)
        if timeline is None:
            raise RuntimeError(
                f"Unable to create timeline '{timeline_name}'."
            )

    project.SetCurrentTimeline(timeline)

    # -----------------------------------------------------
    # Match imported Resolve clips back to their MediaFile
    # objects by filename rather than list position.
    # import_media() can skip missing, duplicate, or failed
    # files, which shifts positions and silently breaks a
    # zip()-based pairing without raising any error.
    # -----------------------------------------------------

    imported_by_name = {}

    for clip in imported:
        try:
            props = clip.GetClipProperty()
            name = props.get("File Name") or props.get("Clip Name")
        except Exception:
            name = None
        if name:
            imported_by_name[name.lower()] = clip

    media_files = context.project_data.get("media_objects", [])

    # -----------------------------------------------------
    # Run the Planning Engine
    # -----------------------------------------------------

    planning_service = TimelinePlanningService()

    result = planning_service.plan(media_files)

    if not result.placements:
        print("Planning Engine produced no placements.")
        return timeline

    print()
    print(f"Ride days         : {result.statistics.ride_days}")
    print(f"Planning segments : {len(result.segments)}")
    print(f"Placements        : {len(result.placements)}")

    # -----------------------------------------------------
    # Ensure enough video tracks exist, named per camera
    # -----------------------------------------------------

    track_names: dict[int, str] = {}

    for placement in result.placements:
        track_names.setdefault(
            placement.track_index,
            placement.camera_name,
        )

    max_track = max(track_names)

    while timeline.GetTrackCount("video") < max_track:
        if not timeline.AddTrack("video"):
            raise RuntimeError("Unable to add video track.")

    for track_index, camera_name in track_names.items():
        timeline.SetTrackName(
            "video",
            track_index,
            camera_name or f"Track {track_index}",
        )

    # -----------------------------------------------------
    # Build the AppendToTimeline batch from TimelinePlacements
    # -----------------------------------------------------

    append_items = []
    skipped = []

    for placement in sorted(
        result.placements,
        key=lambda p: (p.track_index, p.record_frame),
    ):

        clip = imported_by_name.get(placement.clip_name.lower())

        if clip is None:
            skipped.append(placement.clip_name)
            continue

        append_items.append(
            {
                "mediaPoolItem": clip,
                "trackIndex": placement.track_index,
                "recordFrame": placement.record_frame,
            }
        )

    if skipped:
        print()
        print(
            f"WARNING: {len(skipped)} placed clip(s) had no "
            f"matching imported Resolve item and were skipped:"
        )
        for name in skipped[:10]:
            print(f"  - {name}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")

    if not append_items:
        print("No placements could be matched to imported clips.")
        return timeline

    if not media_pool.AppendToTimeline(append_items):
        raise RuntimeError("Failed to append clips to timeline.")

    print()
    print(
        f"Timeline created with {len(append_items)} clips "
        f"across {max_track} track(s)."
    )

    return timeline
