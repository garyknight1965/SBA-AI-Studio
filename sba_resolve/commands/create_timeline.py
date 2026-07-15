"""
============================================================
SBA AI Studio
Resolve Command
Create Timeline
RES-006F.4 - Real Timeline FPS + Multi-Track Timeline + Markers
============================================================

Builds the Resolve timeline using the ML-011 Planning Engine's
PlanningResult, instead of a single naive sequential append.

Each camera gets its own stable video track, and every clip is
placed at its real, gap-preserving record_frame position.
Resolve's AppendToTimeline "recordFrame" key was confirmed to
support exact frame placement via
tools/resolve_gap_placement_test.py.

RES-006F.3 additionally writes the Planning Engine's generated
markers (ride day starts, multicam windows) onto the timeline
via Timeline.AddMarker(). Same-frame markers are already merged
by TimelineMarkerGenerator before they reach here, since Resolve
only supports one marker per exact frame.

RES-006F.4 reads the timeline's actual frame rate via
Timeline.GetSetting("timelineFrameRate") and passes it into the
Planning Engine, instead of assuming a fixed 25fps. Previously,
footage shot at a different native frame rate than the timeline
(e.g. 29.97fps GoPro footage on a 24fps timeline) would drift out
of true real-time sync.

No Resolve API code lives in the Planning Engine itself
(sba_resolve.core.services.timeline_planning_service and its
dependencies) - this module is the boundary where planning
output is translated into real Resolve API calls.
"""

from __future__ import annotations

from sba_resolve.core.services.app_settings import (
    load_gap_compression_settings,
)
from sba_resolve.core.services.timeline_fps import (
    DEFAULT_PROJECT_FPS,
    parse_timeline_fps,
)
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
    # Read the real timeline frame rate. Placement math (both
    # position and duration) must use this, not a hardcoded
    # assumption, or gap-preserving sync drifts against footage
    # shot at a different native frame rate than the timeline.
    # -----------------------------------------------------

    raw_fps = timeline.GetSetting("timelineFrameRate")

    project_fps = parse_timeline_fps(raw_fps)

    if project_fps is None:
        print(
            f"WARNING: Could not read timeline frame rate "
            f"(got {raw_fps!r}); using default "
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
    # zip()-based pairing without raising any error.
    # -----------------------------------------------------

    imported_by_name = {}

    # Tracks which requested filename each underlying clip was
    # first seen under - by BOTH Python object identity and by
    # Resolve's own reported "File Path" property (id() alone can
    # be unreliable across a scripting/COM bridge, which may hand
    # back a fresh wrapper object per call even for the same
    # underlying item - comparing the reported file path is a
    # more reliable, Resolve-native signal). If Resolve's Media
    # Pool ever returns the SAME underlying clip for two different
    # requested filenames (e.g. it deduplicated a paired Insta360
    # dual-lens export internally, treating both views as one
    # media item), this catches it directly rather than us
    # continuing to guess blind - it would fully explain why one
    # of the pair can never be placed as a distinct timeline item.
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

    media_files = context.project_data.get("media_objects", [])

    # -----------------------------------------------------
    # Run the Planning Engine
    # -----------------------------------------------------
    #
    # gap_compression is read from project_data if the caller
    # supplied one (e.g. the GUI loads it from
    # config/settings.json - see load_gap_compression_settings());
    # otherwise it falls back to the same config file directly, so
    # this also works for callers (tests, scripts) that don't set
    # it explicitly. Either way, an untouched, default
    # settings.json means Gap Compression stays OFF and placement
    # is exactly the original, fully gap-preserving behaviour.

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

    planning_service = TimelinePlanningService(
        fps=project_fps,
        gap_compression=gap_compression,
    )

    result = planning_service.plan(media_files)

    if not result.placements:
        print("Planning Engine produced no placements.")
        return timeline

    print()
    print(f"Ride days         : {result.statistics.ride_days}")
    print(f"Scenes            : {result.statistics.scenes}")
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

    print()
    print("Planned placements:")

    zero_duration_clips = []

    for placement in sorted(
        result.placements,
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

    # -----------------------------------------------------
    # Append per-track, not as one mixed batch.
    #
    # Diagnosed via ML-017: two clips sharing the exact same
    # recordFrame as another clip elsewhere in the SAME batch
    # (same real moment, different track - e.g. paired Insta360
    # views) were silently vanishing from the timeline entirely,
    # even though AppendToTimeline still returned a full-count,
    # truthy result. Splitting into one AppendToTimeline call per
    # track removes any possibility of Resolve treating same-frame
    # items on different tracks as a single-call conflict.
    # -----------------------------------------------------

    items_by_track: dict[int, list] = {}

    for item in append_items:
        items_by_track.setdefault(item["trackIndex"], []).append(item)

    appended_items = []

    for track_index in sorted(items_by_track):

        track_items = items_by_track[track_index]

        track_appended = media_pool.AppendToTimeline(track_items)

        # An empty/falsy result for THIS track doesn't necessarily
        # mean total failure - it may mean every clip requested
        # for this track was silently dropped by Resolve, which
        # the count-mismatch warning below already reports. Only
        # a totally empty result across every track (checked
        # after the loop) is treated as a hard failure.
        if track_appended:
            appended_items.extend(track_appended)

    if not appended_items:
        raise RuntimeError("Failed to append clips to timeline.")

    if len(appended_items) != len(append_items):

        # AppendToTimeline can silently drop individual clips
        # (e.g. an overlap with existing content on the same
        # video track at the same recordFrame) while still
        # returning a non-empty, truthy list for the ones that
        # DID succeed. Checking only truthiness (the previous
        # behaviour) would report "SUCCESS" even when some clips
        # never actually reached the timeline.

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
    # Verify every clip actually landed WHERE requested, not
    # just that a full-count list came back. AppendToTimeline
    # can return a correctly-sized, truthy list of TimelineItems
    # while one or more of them ends up at the wrong frame (or
    # isn't findable on its requested track at all) due to an
    # internal Resolve conflict - the count check above can't
    # catch that. Ask the timeline itself, per track, what's
    # really there.
    # -----------------------------------------------------

    _verify_placements(timeline, append_items)

    # -----------------------------------------------------
    # Write ride-day and multicam markers onto the timeline
    # -----------------------------------------------------
    #
    # Resolve only supports one marker per exact frame (see
    # TimelineMarkerGenerator._merge_by_frame, which already
    # merges same-frame markers before they reach here). A
    # failed AddMarker() call is reported but doesn't abort the
    # timeline build - the clips are already placed correctly
    # regardless of marker outcome.

    if result.markers:

        markers_added = 0
        markers_failed = []

        for marker in result.markers:

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
        print(f"Markers added : {markers_added}/{len(result.markers)}")

        if markers_failed:
            print(
                f"WARNING: {len(markers_failed)} marker(s) failed "
                f"to add at frame(s): {markers_failed}"
            )

    return timeline


def _verify_placements(timeline, append_items):
    """
    Cross-checks every requested placement against what the
    timeline itself reports via GetItemListInTrack(), across
    EVERY video track - not just the one requested.

    AppendToTimeline's return value can look like full success
    (a truthy list, the right length, no exception) even when a
    clip's real position on the timeline doesn't match what was
    requested, lands on a completely different track than
    requested, or can't be found anywhere at all - the
    count-only check earlier in create_timeline() can't catch
    any of these. This asks Resolve's own timeline state
    directly instead of trusting AppendToTimeline's return
    value, and searches the whole timeline (not just the
    requested track) so a clip that landed on the wrong track
    entirely is reported as exactly that, rather than as
    "missing".

    Prints a WARNING naming every mismatch found. Never raises -
    this is diagnostic only, so a bad placement is reported but
    doesn't abort the rest of the build (markers, etc).
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

        # Not on the requested track - search every other video
        # track before concluding it's missing entirely.
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
