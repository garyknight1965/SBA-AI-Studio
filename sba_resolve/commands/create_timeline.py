"""
============================================================
SBA AI Studio
Resolve Command
Create Timeline
RES-006F.7 - ML-057: One Resolve timeline per ride day
============================================================

Builds one Resolve timeline PER RIDE DAY using the ML-011
Planning Engine's PlanningResult, instead of a single flat
"Master" timeline covering the whole project.

The Planning Engine (TimelinePlanningService) still runs exactly
once, project-wide, exactly as before - PlanningResult.placements
still carry real, project-wide record_frame values. Splitting
that project-wide result into one rebased plan per ride day is
business logic, so it lives in the Planning-Engine-side
RideDayGrouper service (sba_resolve.core.services.ride_day_grouper),
NOT here - this module only consumes the resulting
RideDayTimelinePlan objects and translates them into real Resolve
API calls, one timeline at a time.

Each day's timeline name follows Gary's chosen format:
"<base name> Day <N> - <YYYY-MM-DD>" (falls back to
"<base name> Day <N>" if no clip in that day has a known
creation time to derive a date from).

Each camera gets its own stable video track, and every clip is
placed at its real, gap-preserving record_frame position (now
relative to that day's own earliest clip, not the whole
project). Resolve's AppendToTimeline "recordFrame" key was
confirmed to support exact frame placement via
tools/resolve_gap_placement_test.py.

Also writes the Planning Engine's generated markers (ride day
starts, scene starts, multicam windows) onto each day's own
timeline via Timeline.AddMarker(). Same-frame markers are
already merged by TimelineMarkerGenerator before they reach
here, since Resolve only supports one marker per exact frame.

Reads the Resolve PROJECT's configured timeline frame rate via
Project.GetSetting("timelineFrameRate") ONCE, up front - before
any per-day timeline exists - and passes it into the Planning
Engine. Every timeline created in the same Resolve project uses
that project-wide frame rate by default, so one read up front is
correct and avoids a chicken-and-egg problem (the Planning Engine
needs fps before it can compute per-day frame numbers, but which
day's timeline would we even read fps from first?).

Ensures a named track also exists for any camera that ONLY has
clips the Planning Engine could not verify via audio sync
(PlanningResult.unsynced_clips, grouped per day) - these clips
are never appended to the timeline (never guessed), but still
get a labeled, empty home track ready for manual sync in
Resolve. A "Manual Sync Required" report is printed per day
listing every such clip by camera, with its original filename
and the reason sync failed.

Creates a matching, identically-named AUDIO track for every
video track (both the normal per-camera tracks and the
placeholder tracks) on each day's timeline, so a
manually-dragged-in clip's audio has an obvious, correctly
labeled home too.

No Resolve API code lives in the Planning Engine itself
(sba_resolve.core.services.timeline_planning_service,
sba_resolve.core.services.ride_day_grouper, and their
dependencies) - this module is the boundary where planning
output is translated into real Resolve API calls.

RES-006F.7b (2026-07-23, per Gary's follow-up request) also
assembles a "<base name> Master" timeline once every day's
timeline has been built, nesting each day's timeline into it in
ride-day order as a single combined review/export sequence.
Every Resolve Timeline also exists as an item in the Media Pool
once created, so nesting reuses the ordinary AppendToTimeline
mechanism - no special "nest a timeline" API is needed. No
recordFrame is supplied for these appends; Resolve places each
one at the end of the track's existing content in call order,
so no frame math is guessed for the Master's assembly.
"""

from __future__ import annotations

from sba_resolve.core.services.app_settings import (
    load_gap_compression_settings,
    load_multicam_audio_sync_enabled,
)
from sba_resolve.core.services.ride_day_grouper import RideDayGrouper
from sba_resolve.core.services.timeline_fps import (
    DEFAULT_PROJECT_FPS,
    parse_timeline_fps,
)
from sba_resolve.core.services.timeline_planning_service import (
    TimelinePlanningService,
)


def create_timeline(context):
    """
    Create one Resolve timeline per ride day from imported media.

    Uses the Planning Engine (TimelinePlanningService) to
    determine per-camera track assignment and frame-exact,
    gap-preserving clip placement, then RideDayGrouper to split
    that project-wide result into one rebased plan per ride day,
    then executes each day's plan against the Resolve API as its
    own timeline.

    Returns the LAST timeline built (or None if there was
    nothing to build), matching the previous single-timeline
    return contract for callers/tests that only ever dealt with
    one ride day.
    """

    project = context.project
    media_pool = context.media_pool

    if project is None or media_pool is None:
        raise RuntimeError("Resolve project is not initialized.")

    imported = getattr(context, "imported_items", [])

    if not imported:
        print("No imported clips available.")
        return None

    base_timeline_name = (
        context.project_data.get("timeline_name")
        or context.project_data["project_name"]
    )

    print("=" * 60)
    print("Create Timeline")
    print("=" * 60)

    # -----------------------------------------------------
    # Read the project's configured timeline frame rate ONCE,
    # up front. Placement math (both position and duration) must
    # use this, not a hardcoded assumption, or gap-preserving
    # sync drifts against footage shot at a different native
    # frame rate than the timeline. Every timeline subsequently
    # created in this project uses this same frame rate by
    # default.
    # -----------------------------------------------------

    raw_fps = project.GetSetting("timelineFrameRate")

    project_fps = parse_timeline_fps(raw_fps)

    if project_fps is None:
        print(
            f"WARNING: Could not read the project's timeline "
            f"frame rate (got {raw_fps!r}); using default "
            f"{DEFAULT_PROJECT_FPS} fps."
        )
        project_fps = DEFAULT_PROJECT_FPS
    else:
        print(f"Timeline FPS      : {project_fps}")

    # -----------------------------------------------------
    # Match imported Resolve clips back to their MediaFile
    # objects by filename rather than list position.
    # import_media() can skip missing, duplicate, or failed
    # files, which shifts positions and silently breaks a
    # zip()-based pairing without raising any error. Built once
    # and shared across every day's timeline.
    # -----------------------------------------------------

    imported_by_name = _build_imported_lookup(imported)

    media_files = context.project_data.get("media_objects", [])

    # -----------------------------------------------------
    # Run the Planning Engine ONCE, project-wide - unchanged
    # from before. Splitting the result per ride day happens
    # below, after planning.
    # -----------------------------------------------------

    gap_compression = context.project_data.get("gap_compression")

    if gap_compression is None:
        gap_compression = load_gap_compression_settings()

    if gap_compression.enabled:
        print(
            f"Gap Compression   : ENABLED (gaps over "
            f"{gap_compression.gap_threshold_seconds:.0f}s "
            f"compressed to "
            f"{gap_compression.compressed_gap_seconds:.0f}s)"
        )
    else:
        print("Gap Compression   : disabled")

    enable_multicam_audio_sync = context.project_data.get(
        "enable_multicam_audio_sync"
    )

    if enable_multicam_audio_sync is None:
        enable_multicam_audio_sync = load_multicam_audio_sync_enabled()

    print(
        f"Multicam Audio Sync : "
        f"{'ENABLED' if enable_multicam_audio_sync else 'disabled'}"
    )

    planning_service = TimelinePlanningService(
        fps=project_fps,
        gap_compression=gap_compression,
        enable_multicam_audio_sync=enable_multicam_audio_sync,
    )

    result = planning_service.plan(media_files)

    if not result.placements:
        print("Planning Engine produced no placements.")
        return None

    print()
    print(f"Ride days         : {result.statistics.ride_days}")
    print(f"Scenes            : {result.statistics.scenes}")
    print(f"Planning segments : {len(result.segments)}")
    print(f"Placements        : {len(result.placements)}")

    # -----------------------------------------------------
    # Split into one rebased plan per ride day, and build each
    # one as its own independent Resolve timeline.
    # -----------------------------------------------------

    day_plans = RideDayGrouper.group(result)

    day_timelines: list[tuple[str, object]] = []

    for day_plan in day_plans:

        timeline_name = (
            f"{base_timeline_name} {day_plan.timeline_name_suffix}"
        )

        print()
        print("-" * 60)
        print(f"Timeline : {timeline_name}")
        print("-" * 60)

        timeline = _find_or_create_timeline(
            project, media_pool, timeline_name
        )

        project.SetCurrentTimeline(timeline)

        _build_day_timeline(
            timeline,
            media_pool,
            day_plan,
            imported_by_name,
            project_fps,
        )

        day_timelines.append((timeline_name, timeline))

    # -----------------------------------------------------
    # Assemble a Master timeline that nests every day's
    # timeline, in ride-day order, as a single review/export
    # sequence. Each day timeline is appended as a nested clip -
    # every Resolve Timeline also exists as an item in the Media
    # Pool once created, so this reuses the normal
    # AppendToTimeline mechanism rather than any special nesting
    # API. Sequential placement uses Resolve's own "append at
    # the end of the track" behaviour (no explicit recordFrame),
    # so no frame math is guessed here - the Master's own
    # ordering does the work.
    # -----------------------------------------------------

    master_timeline = _build_master_timeline(
        project, media_pool, base_timeline_name, day_timelines
    )

    return master_timeline or (
        day_timelines[-1][1] if day_timelines else None
    )


def _build_master_timeline(
    project,
    media_pool,
    base_timeline_name,
    day_timelines,
):
    """
    Creates (or finds) a "<base name> Master" timeline and nests
    each day's timeline into it, in order, as a single combined
    review/export sequence.

    Returns the Master timeline, or None if there were no day
    timelines to nest, or if none of them could be found as
    Media Pool items (should not happen in real Resolve - every
    Timeline is also a Media Pool item - but this is defensive
    rather than assumed).
    """

    if not day_timelines:
        return None

    master_timeline_name = f"{base_timeline_name} Master"

    print()
    print("=" * 60)
    print(f"Master Timeline : {master_timeline_name}")
    print("=" * 60)

    master_timeline = _find_or_create_timeline(
        project, media_pool, master_timeline_name
    )

    project.SetCurrentTimeline(master_timeline)

    nested_count = 0
    missing = []

    for timeline_name, _timeline in day_timelines:

        clip = _find_timeline_media_pool_item(
            media_pool, timeline_name
        )

        if clip is None:
            missing.append(timeline_name)
            continue

        # No recordFrame supplied - Resolve appends at the end
        # of the track's existing content, in call order. This
        # keeps the day timelines in ride-day order without this
        # module computing any frame math itself.
        appended = media_pool.AppendToTimeline(
            [{"mediaPoolItem": clip, "trackIndex": 1}]
        )

        if appended:
            nested_count += 1
        else:
            missing.append(timeline_name)

    print(
        f"Nested {nested_count}/{len(day_timelines)} day "
        f"timeline(s) into the Master timeline."
    )

    if missing:
        print(
            f"WARNING: {len(missing)} day timeline(s) could not "
            f"be nested into the Master timeline (no matching "
            f"Media Pool item found, or Resolve rejected the "
            f"append):"
        )
        for name in missing:
            print(f"  - {name}")

    return master_timeline


def _find_timeline_media_pool_item(media_pool, timeline_name):
    """
    Every Resolve Timeline also exists as an item in the Media
    Pool (in whichever bin it was created in). Finds that
    MediaPoolItem by name so a Timeline can be appended onto
    another timeline as a nested clip, the same way any other
    clip is appended. Returns None if not found.
    """

    root_folder = media_pool.GetRootFolder()

    if root_folder is None:
        return None

    def search(folder):

        for clip in folder.GetClipList() or []:

            try:
                props = clip.GetClipProperty()
            except Exception:
                continue

            is_timeline_clip = props.get("Type") == "Timeline"

            matches_name = (
                props.get("File Name") == timeline_name
                or props.get("Clip Name") == timeline_name
            )

            if is_timeline_clip and matches_name:
                return clip

        for sub_folder in folder.GetSubFolderList() or []:
            found = search(sub_folder)
            if found is not None:
                return found

        return None

    return search(root_folder)


def _find_or_create_timeline(project, media_pool, timeline_name):
    """
    Finds an existing timeline with this exact name, or creates
    a new empty one.
    """

    for index in range(1, project.GetTimelineCount() + 1):
        existing = project.GetTimelineByIndex(index)
        if existing and existing.GetName() == timeline_name:
            print("Using existing timeline.")
            return existing

    timeline = media_pool.CreateEmptyTimeline(timeline_name)

    if timeline is None:
        raise RuntimeError(
            f"Unable to create timeline '{timeline_name}'."
        )

    return timeline


def _build_imported_lookup(imported):
    """
    Builds a {lowercased filename: Resolve clip} lookup from the
    imported Resolve clips, warning about any clips that appear
    to be internal Resolve duplicates (same underlying object,
    or same underlying file path, requested under more than one
    name).
    """

    imported_by_name = {}

    clip_identity_seen: dict[int, str] = {}
    clip_path_seen: dict[str, str] = {}
    duplicate_identity_warnings = []
    duplicate_path_warnings = []

    for clip in imported:
        try:
            props = clip.GetClipProperty()
            name = props.get("File Name") or props.get("Clip Name")
            file_path = props.get("File Path")
        except Exception:
            name = None
            file_path = None

        if not name:
            continue

        imported_by_name[name.lower()] = clip

        identity = id(clip)
        if identity in clip_identity_seen:
            duplicate_identity_warnings.append(
                (clip_identity_seen[identity], name)
            )
        else:
            clip_identity_seen[identity] = name

        if file_path:
            if file_path in clip_path_seen:
                duplicate_path_warnings.append(
                    (clip_path_seen[file_path], name, file_path)
                )
            else:
                clip_path_seen[file_path] = name

    if duplicate_identity_warnings:
        print()
        print(
            f"WARNING: {len(duplicate_identity_warnings)} pair(s) "
            f"of requested filenames resolved to the SAME "
            f"underlying Resolve clip object - Resolve's Media "
            f"Pool may be deduplicating these internally:"
        )
        for first_name, second_name in duplicate_identity_warnings:
            print(f"  - {first_name}  <->  {second_name}")

    if duplicate_path_warnings:
        print()
        print(
            f"WARNING: {len(duplicate_path_warnings)} pair(s) of "
            f"requested filenames report the SAME underlying "
            f"'File Path' from Resolve - these are almost "
            f"certainly the same media item internally, despite "
            f"having different requested filenames:"
        )
        for first_name, second_name, file_path in (
            duplicate_path_warnings
        ):
            print(f"  - {first_name}  <->  {second_name}")
            print(f"    File Path: {file_path}")

    return imported_by_name


def _build_day_timeline(
    timeline,
    media_pool,
    day_plan,
    imported_by_name,
    project_fps,
):
    """
    Builds ONE ride day's worth of tracks, clip placements, and
    markers onto an already-found-or-created timeline.

    day_plan.placements/markers are already rebased relative to
    this day's own earliest clip (see RideDayGrouper) -
    everything here just executes that plan against the real
    Resolve API, exactly as the single-timeline builder always
    did.
    """

    # -----------------------------------------------------
    # Ensure enough video tracks exist, named per camera
    # -----------------------------------------------------

    track_names: dict[int, str] = {}

    for placement in day_plan.placements:
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
    # Ensure a named track also exists for any camera that ONLY
    # has unsynced clips (no successful placement at all for
    # that camera, on this day). These clips never reach
    # AppendToTimeline, but still need a labeled home track
    # ready for manual sync in Resolve.
    # -----------------------------------------------------

    unsynced_by_camera: dict[str, list] = {}

    for unsynced_clip in day_plan.unsynced_clips:
        unsynced_by_camera.setdefault(
            unsynced_clip.camera_name, []
        ).append(unsynced_clip)

    camera_to_track_index = {
        camera_name: track_index
        for track_index, camera_name in track_names.items()
    }

    for camera_name in sorted(unsynced_by_camera):

        if camera_name in camera_to_track_index:
            continue

        max_track += 1

        if timeline.GetTrackCount("video") < max_track:
            if not timeline.AddTrack("video"):
                raise RuntimeError("Unable to add video track.")

        timeline.SetTrackName(
            "video",
            max_track,
            camera_name or f"Track {max_track}",
        )

        track_names[max_track] = camera_name
        camera_to_track_index[camera_name] = max_track

    # -----------------------------------------------------
    # Create a matching, identically-named AUDIO track for every
    # camera video track above (both the normal per-camera
    # tracks and the placeholder tracks), so a clip's audio has
    # an obvious, correctly-labeled home too - not just its
    # video.
    # -----------------------------------------------------

    max_audio_track = len(track_names)

    while timeline.GetTrackCount("audio") < max_audio_track:
        if not timeline.AddTrack("audio"):
            raise RuntimeError("Unable to add audio track.")

    for audio_track_index, camera_name in enumerate(
        [track_names[i] for i in sorted(track_names)], start=1
    ):
        timeline.SetTrackName(
            "audio",
            audio_track_index,
            camera_name or f"Track {audio_track_index}",
        )

    # -----------------------------------------------------
    # Build the AppendToTimeline batch from this day's
    # TimelinePlacements
    # -----------------------------------------------------

    print()
    print("Planned placements:")

    zero_duration_clips = []

    for placement in sorted(
        day_plan.placements,
        key=lambda p: (p.track_index, p.record_frame),
    ):

        elapsed_seconds = placement.record_frame / project_fps

        hours = int(elapsed_seconds // 3600)
        minutes = int((elapsed_seconds % 3600) // 60)
        seconds = elapsed_seconds % 60

        duration_seconds = placement.duration_frames / project_fps

        if placement.duration_frames <= 0:
            zero_duration_clips.append(placement.clip_name)

        print(
            f"  Track {placement.track_index} | "
            f"frame {placement.record_frame:>10} "
            f"(+{hours:02d}:{minutes:02d}:{seconds:05.2f}) | "
            f"dur {placement.duration_frames:>6} "
            f"({duration_seconds:6.2f}s) | "
            f"{placement.clip_name}"
        )

    if zero_duration_clips:
        print()
        print(
            f"WARNING: {len(zero_duration_clips)} clip(s) have a "
            f"zero or invalid duration - they'll be placed at "
            f"the correct frame but effectively invisible/"
            f"unplayable on the timeline:"
        )
        for name in zero_duration_clips[:10]:
            print(f"  - {name}")
        if len(zero_duration_clips) > 10:
            print(f"  ... and {len(zero_duration_clips) - 10} more")

    append_items = []
    skipped = []

    for placement in sorted(
        day_plan.placements,
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
        return

    # -----------------------------------------------------
    # Append per-track, not as one mixed batch.
    # -----------------------------------------------------

    items_by_track: dict[int, list] = {}

    for item in append_items:
        items_by_track.setdefault(item["trackIndex"], []).append(item)

    appended_items = []

    for track_index in sorted(items_by_track):

        track_items = items_by_track[track_index]

        track_appended = media_pool.AppendToTimeline(track_items)

        if track_appended:
            appended_items.extend(track_appended)

    if not appended_items:
        raise RuntimeError("Failed to append clips to timeline.")

    if len(appended_items) != len(append_items):

        requested_names = {
            item["mediaPoolItem"].GetClipProperty().get("File Name")
            or item["mediaPoolItem"].GetClipProperty().get("Clip Name")
            for item in append_items
        }

        placed_names = set()

        for timeline_item in appended_items:
            try:
                mpi = timeline_item.GetMediaPoolItem()
                props = mpi.GetClipProperty() if mpi else {}
                name = props.get("File Name") or props.get("Clip Name")
            except Exception:
                name = None
            if name:
                placed_names.add(name)

        dropped_names = requested_names - placed_names

        print()
        print(
            f"WARNING: requested {len(append_items)} clip "
            f"placement(s), but Resolve only placed "
            f"{len(appended_items)}. "
            f"{len(append_items) - len(appended_items)} clip(s) "
            f"were silently dropped by Resolve - most likely an "
            f"overlap with existing content already on the same "
            f"video track at the same recordFrame."
        )

        if dropped_names:
            print("Dropped clip(s):")
            for name in sorted(dropped_names)[:10]:
                print(f"  - {name}")
            if len(dropped_names) > 10:
                print(f"  ... and {len(dropped_names) - 10} more")

    print()
    print(
        f"Timeline created with {len(appended_items)} clips "
        f"across {max_track} track(s)."
    )

    # -----------------------------------------------------
    # Report every clip that could not be automatically
    # synced/placed on this day - grouped by camera, with
    # original filenames and the reason, so nothing is silently
    # missing from the timeline. No timeline markers are created
    # for these - the named empty track plus this report is the
    # complete signal.
    # -----------------------------------------------------

    if day_plan.unsynced_clips:

        print()
        print("=" * 60)
        print("Manual Sync Required")
        print("=" * 60)

        for camera_name in sorted(unsynced_by_camera):

            clips = unsynced_by_camera[camera_name]

            print()
            print(camera_name)
            print("Status         : Manual Sync Required")
            print(
                f"Track Created  : Yes (Track "
                f"{camera_to_track_index[camera_name]})"
            )
            print("Media Added    : No")
            print(f"Clips ({len(clips)}):")

            for clip in clips:
                print(f"  - {clip.clip_name}")
                print(f"    Reason: {clip.reason}")

    # -----------------------------------------------------
    # Verify every clip actually landed WHERE requested
    # -----------------------------------------------------

    _verify_placements(timeline, append_items)

    # -----------------------------------------------------
    # Write this day's ride-day/scene/multicam markers onto its
    # own timeline
    # -----------------------------------------------------

    if day_plan.markers:

        markers_added = 0
        markers_failed = []

        for marker in day_plan.markers:

            added = timeline.AddMarker(
                marker.frame,
                marker.colour,
                marker.title,
                marker.description,
                1,
            )

            if added:
                markers_added += 1
            else:
                markers_failed.append(marker.frame)

        print()
        print(f"Markers added : {markers_added}/{len(day_plan.markers)}")

        if markers_failed:
            print(
                f"WARNING: {len(markers_failed)} marker(s) failed "
                f"to add at frame(s): {markers_failed}"
            )


def _verify_placements(timeline, append_items):
    """
    Cross-checks every requested placement against what the
    timeline itself reports via GetItemListInTrack(), across
    EVERY video track - not just the one requested.
    """

    track_count = timeline.GetTrackCount("video") or 0

    track_item_cache: dict[int, list] = {}

    def track_items(index):
        if index not in track_item_cache:
            track_item_cache[index] = (
                timeline.GetItemListInTrack("video", index) or []
            )
        return track_item_cache[index]

    def find_by_name(index, requested_name):
        for timeline_item in track_items(index):
            try:
                mpi = timeline_item.GetMediaPoolItem()
                mpi_props = mpi.GetClipProperty() if mpi else {}
                name = (
                    mpi_props.get("File Name")
                    or mpi_props.get("Clip Name")
                )
            except Exception:
                name = None

            if name and name.lower() == requested_name.lower():
                try:
                    return timeline_item.GetStart()
                except Exception:
                    return None

        return None

    problems = []

    for item in append_items:

        requested_track = item["trackIndex"]
        requested_frame = item["recordFrame"]

        try:
            props = item["mediaPoolItem"].GetClipProperty()
            requested_name = (
                props.get("File Name") or props.get("Clip Name")
            )
        except Exception:
            requested_name = None

        if requested_name is None:
            continue

        actual_frame = find_by_name(requested_track, requested_name)

        if actual_frame is not None:

            if actual_frame != requested_frame:
                problems.append(
                    (
                        requested_track,
                        requested_name,
                        requested_frame,
                        requested_track,
                        actual_frame,
                    )
                )

            continue

        actual_track = None

        for other_index in range(1, track_count + 1):

            if other_index == requested_track:
                continue

            found_frame = find_by_name(other_index, requested_name)

            if found_frame is not None:
                actual_track = other_index
                actual_frame = found_frame
                break

        problems.append(
            (
                requested_track,
                requested_name,
                requested_frame,
                actual_track,
                actual_frame,
            )
        )

    if problems:

        print()
        print(
            f"WARNING: {len(problems)} clip(s) did not land where "
            f"requested:"
        )

        for (
            requested_track,
            name,
            requested_frame,
            actual_track,
            actual_frame,
        ) in problems[:15]:

            if actual_track is None:
                print(
                    f"  - {name}: requested Track {requested_track} "
                    f"frame {requested_frame}, NOT FOUND on ANY "
                    f"video track"
                )
            elif actual_track != requested_track:
                print(
                    f"  - {name}: requested Track {requested_track} "
                    f"frame {requested_frame}, actually landed on "
                    f"Track {actual_track} frame {actual_frame}"
                )
            else:
                print(
                    f"  - {name}: requested Track {requested_track} "
                    f"frame {requested_frame}, actually at frame "
                    f"{actual_frame} on the same track"
                )

        if len(problems) > 15:
            print(f"  ... and {len(problems) - 15} more")

    return problems
