"""
============================================================
SBA AI Studio
Resolve Command
Create Timeline
MVP-001-003
============================================================
"""

from datetime import datetime


def _sort_key(item):
    created = getattr(item, "created", None)
    if isinstance(created, datetime):
        return created
    return datetime.min


def create_timeline(context):
    """
    Create a Resolve timeline from imported media.
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

    # Remove existing timeline with same name if present
    for tl in project.GetTimelineCount() and range(1, project.GetTimelineCount() + 1) or []:
        existing = project.GetTimelineByIndex(tl)
        if existing and existing.GetName() == timeline_name:
            project.SetCurrentTimeline(existing)
            print("Using existing timeline.")
            timeline = existing
            break
    else:
        timeline = media_pool.CreateEmptyTimeline(timeline_name)
        if timeline is None:
            raise RuntimeError(f"Unable to create timeline '{timeline_name}'.")

    project.SetCurrentTimeline(timeline)

    # Match imported Resolve clips back to their MediaFile objects by
    # filename rather than list position. import_media() can skip missing,
    # duplicate, or failed files, which shifts positions and silently
    # breaks a zip()-based pairing without raising any error.
    imported_by_name = {}
    for clip in imported:
        try:
            props = clip.GetClipProperty()
            name = props.get("File Name") or props.get("Clip Name")
        except Exception:
            name = None
        if name:
            imported_by_name[name.lower()] = clip

    media = sorted(
        context.project_data.get("media_objects", []),
        key=_sort_key,
    )

    ordered = []
    seen_clips = set()
    for m in media:
        full_path = getattr(m, "full_path", None)
        filename = full_path.name if full_path is not None else None
        clip = imported_by_name.get(filename.lower()) if filename else None
        if clip is not None and id(clip) not in seen_clips:
            ordered.append(clip)
            seen_clips.add(id(clip))

    # Fall back to whatever import order we have if matching produced
    # nothing usable (e.g. clip properties unavailable), rather than
    # silently building an empty timeline.
    if not ordered:
        ordered = imported

    if not media_pool.AppendToTimeline(ordered):
        raise RuntimeError("Failed to append clips to timeline.")

    print(f"Timeline created with {len(ordered)} clips.")

    return timeline
