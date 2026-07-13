"""
============================================================
SBA AI Studio
Resolve Command
Create Timeline V2
RES-006E - Camera Aware Timeline Foundation
============================================================
"""

from datetime import datetime


def _sort_key(item):
    created = getattr(item, "created", None)

    if isinstance(created, datetime):
        return created

    return datetime.min


def _get_camera_name(media_file):
    """
    Get the normalized camera display name from MediaFile.
    """

    try:
        return media_file.camera_display_name
    except Exception:
        pass

    return (
        getattr(media_file, "camera_model", None)
        or getattr(media_file, "camera_make", None)
        or "Unknown Camera"
    )


def create_timeline(context):
    """
    Create a Resolve timeline from imported media.

    RES-006E:
    - Preserve MediaFile metadata
    - Build camera groups
    - Prepare camera-aware timeline creation
    """

    project = context.project
    media_pool = context.media_pool

    if project is None or media_pool is None:
        raise RuntimeError(
            "Resolve project is not initialized."
        )

    imported = getattr(
        context,
        "imported_items",
        []
    )

    if not imported:
        print("No imported clips available.")
        return None


    timeline_name = (
        context.project_data.get("timeline_name")
        or f"{context.project_data['project_name']} Master"
    )


    print("=" * 60)
    print("SBA AI Studio Timeline Builder")
    print("=" * 60)
    print(f"Timeline : {timeline_name}")


    # --------------------------------------------------------
    # Create or reuse timeline
    # --------------------------------------------------------

    timeline = None

    for index in range(
        1,
        project.GetTimelineCount() + 1
    ):

        existing = project.GetTimelineByIndex(index)

        if (
            existing
            and existing.GetName() == timeline_name
        ):
            timeline = existing
            break


    if timeline is None:

        timeline = media_pool.CreateEmptyTimeline(
            timeline_name
        )

        if timeline is None:
            raise RuntimeError(
                f"Unable to create timeline '{timeline_name}'."
            )


    project.SetCurrentTimeline(timeline)



    # --------------------------------------------------------
    # Match Resolve clips back to MediaFile objects
    # --------------------------------------------------------

    imported_by_name = {}

    for clip in imported:

        try:
            props = clip.GetClipProperty()

            name = (
                props.get("File Name")
                or props.get("Clip Name")
            )

        except Exception:

            name = None


        if name:
            imported_by_name[
                name.lower()
            ] = clip



    media_files = sorted(
        context.project_data.get(
            "media_objects",
            []
        ),
        key=_sort_key,
    )



    # --------------------------------------------------------
    # Build MediaFile -> Resolve Clip assignments
    # --------------------------------------------------------

    assignments = []

    seen = set()


    for media_file in media_files:

        full_path = getattr(
            media_file,
            "full_path",
            None
        )

        if full_path is None:
            continue


        filename = full_path.name.lower()


        resolve_clip = imported_by_name.get(
            filename
        )


        if resolve_clip is None:
            continue


        if id(resolve_clip) in seen:
            continue


        seen.add(
            id(resolve_clip)
        )


        assignments.append(
            {
                "media": media_file,
                "clip": resolve_clip,
            }
        )



    if not assignments:

        print(
            "WARNING: Metadata matching failed."
        )

        assignments = [
            {
                "media": None,
                "clip": clip
            }
            for clip in imported
        ]



    # --------------------------------------------------------
    # Camera grouping
    # --------------------------------------------------------

    camera_groups = {}


    for item in assignments:

        media_file = item["media"]


        if media_file:

            camera = _get_camera_name(
                media_file
            )

        else:

            camera = "Unknown Camera"


        camera_groups.setdefault(
            camera,
            []
        ).append(item)



    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("Camera Summary")
    print("=" * 60)


    total = 0


    for camera in sorted(camera_groups):

        count = len(
            camera_groups[camera]
        )

        total += count

        print(
            f"{camera:<35}{count:>5} clips"
        )


    print("-" * 60)

    print(
        f"{'Total Clips':<35}{total:>5}"
    )



    # --------------------------------------------------------
    # RES-006E MVP
    #
    # Keep current timeline creation behaviour.
    # Track routing comes in RES-006F.
    # --------------------------------------------------------

    ordered = [
        item["clip"]
        for item in assignments
    ]


    if not media_pool.AppendToTimeline(
        ordered
    ):

        raise RuntimeError(
            "Failed to append clips to timeline."
        )


    print()
    print(
        f"Timeline created with {len(ordered)} clips."
    )

    print(
        "RES-006E complete."
    )


    return timeline