"""
tools/test_chapter_title_bootstrap.py

Standalone diagnostic for ML-055 (chapter title cards). Investigates
two independent candidate mechanisms for placing dynamic Fusion text
without Resolve's manual "click the track first" requirement:

    CANDIDATE A (bootstrap / insert / check_reuse):
    Does a Fusion Text+ composition built by script (via
    InsertFusionCompositionIntoTimeline) get a real, reusable Media
    Pool item back from TimelineItem.GetMediaPoolItem() -- and can
    that item then be re-placed elsewhere via AppendToTimeline
    (confirmed non-rippling) without a ripple? This still needs ONE
    manual track click for the initial insert.

    CANDIDATE B (export_template / import_on_placeholder) -- PREFERRED
    IF IT WORKS, since it eliminates the click structurally rather
    than working around it:
    Can a placeholder item -- placed via AppendToTimeline, the same
    proven-safe mechanism as the logo/intro clip, with an explicit
    trackIndex/recordFrame and NO active-track dependency -- have a
    saved Fusion composition (.comp file, built and exported once by
    hand in Resolve's own Fusion editor) attached to it afterward via
    TimelineItem.ImportFusionComp(path)? If yes, the entire per-chapter
    loop never touches InsertFusionCompositionIntoTimeline or any
    other active-track-dependent API at all -- the only manual step
    left is a one-time human action in Fusion's UI to build and save
    the template, which is normal editing, not a scripting limitation.

Does NOT touch resolve_graphic_inserter.py or graphics_config.py --
deliberately standalone so it can't affect the existing (unwired)
graphics sprint code either way. Only reads two constants from
graphics_config (CHANNEL_BUG_IMAGE_PATH / CHANNEL_BUG_MEDIA_POOL_NAME)
to reuse your already-confirmed-findable logo asset as the Candidate B
placeholder image -- no reason to invent a new test asset when a real
one already works.

Run this with Resolve open, a real project loaded, and a real
timeline active. It creates test tracks and test clips; 'rollback'
removes everything both candidates create.

Usage (Candidate A):
    python tools/test_chapter_title_bootstrap.py bootstrap
    (click the printed track name in Resolve now)
    python tools/test_chapter_title_bootstrap.py insert
    python tools/test_chapter_title_bootstrap.py check_reuse

Usage (Candidate B):
    python tools/test_chapter_title_bootstrap.py bootstrap
    (click the printed track name in Resolve now)
    python tools/test_chapter_title_bootstrap.py insert
    python tools/test_chapter_title_bootstrap.py export_template
    python tools/test_chapter_title_bootstrap.py import_on_placeholder

Cleanup:
    python tools/test_chapter_title_bootstrap.py rollback
"""

import sys
import os

sys.path.insert(0, "..")  # allow running from tools/ directly

from graphics_config import CHANNEL_BUG_IMAGE_PATH, CHANNEL_BUG_MEDIA_POOL_NAME

TEST_TRACK_NAME = "ML055 Bootstrap Test"
TEST_TEXT = "ML-055 Bootstrap"
TEST_PREFIX = "ML055_Bootstrap_"
TEST_COMP_EXPORT_PATH = r"D:\Projects\SBA-AI-Studio\assets\test\ml055_template.comp"


def _connect():
    import DaVinciResolveScript as dvr_script

    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Resolve returned no application object. Is Resolve running?")

    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        raise RuntimeError("No project is currently open in Resolve.")

    timeline = project.GetCurrentTimeline()
    if timeline is None:
        raise RuntimeError("No timeline is currently open/active in the project.")

    media_pool = project.GetMediaPool()
    if media_pool is None:
        raise RuntimeError("Could not access the Media Pool.")

    return resolve, project, timeline, media_pool


def _ensure_empty_track(timeline, name):
    """Creates a brand-new, uniquely-named, empty video track -- same
    pattern as GraphicInserter.prepare_text_track(), kept standalone
    here rather than importing it, so this script has zero dependency
    on the untested production module.
    """
    existing_names = {
        timeline.GetTrackName("video", i)
        for i in range(1, timeline.GetTrackCount("video") + 1)
    }
    final_name = name
    suffix = 2
    while final_name in existing_names:
        final_name = f"{name} ({suffix})"
        suffix += 1

    if not timeline.AddTrack("video"):
        raise RuntimeError(f"Resolve refused to add a new video track for '{final_name}'.")
    new_index = timeline.GetTrackCount("video")
    if not timeline.SetTrackName("video", new_index, final_name):
        raise RuntimeError(f"Added a track but could not rename it to '{final_name}'.")
    return final_name, new_index


def _snapshot_other_tracks(timeline, exclude_track_index):
    snapshot = {}
    for track_index in range(1, timeline.GetTrackCount("video") + 1):
        if track_index == exclude_track_index:
            continue
        snapshot[track_index] = [
            (item.GetName(), item.GetStart(), item.GetEnd())
            for item in timeline.GetItemListInTrack("video", track_index)
        ]
    return snapshot


def run_bootstrap():
    resolve, project, timeline, media_pool = _connect()

    track_name, track_index = _ensure_empty_track(timeline, TEST_TRACK_NAME)
    print(f"Created empty track: '{track_name}' (index {track_index})")
    print(
        f">>> ACTION NEEDED: click on track '{track_name}' in the "
        f"Resolve timeline panel RIGHT NOW to select/activate it. <<<\n"
        f"Only after you've clicked it, run: "
        f"python test_chapter_title_bootstrap.py insert"
    )


def run_insert():
    resolve, project, timeline, media_pool = _connect()

    fps = float(timeline.GetSetting("timelineFrameRate"))
    start_seconds = 5.0
    total_frames = int(round(start_seconds * fps))
    frame_rate = int(round(fps))
    frames = total_frames % frame_rate
    total_secs = total_frames // frame_rate
    secs = total_secs % 60
    total_mins = total_secs // 60
    mins = total_mins % 60
    hours = total_mins // 60
    timecode_str = f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"

    if not timeline.SetCurrentTimecode(timecode_str):
        raise RuntimeError(f"Could not move playhead to {timecode_str}.")

    timeline_item = timeline.InsertFusionCompositionIntoTimeline()
    if timeline_item is None:
        raise RuntimeError(
            "InsertFusionCompositionIntoTimeline() returned nothing. "
            "Confirm the currently active track accepts a Fusion "
            "composition, and that you clicked the test track from "
            "the 'bootstrap' step."
        )
    timeline_item.SetName(f"{TEST_PREFIX}template")

    comp = timeline_item.AddFusionComp()
    if comp is None:
        raise RuntimeError("AddFusionComp() returned nothing.")

    text_tool = comp.AddTool("TextPlus")
    if text_tool is None:
        raise RuntimeError("AddTool('TextPlus') returned nothing.")

    media_out_tool = comp.FindTool("MediaOut1")
    if media_out_tool is None:
        raise RuntimeError("Could not find MediaOut1 in the new Fusion composition.")
    media_out_tool.ConnectInput("Input", text_tool)

    text_tool.SetInput("StyledText", TEST_TEXT, 0)
    text_tool.SetInput("Font", "Impact", 0)
    text_tool.SetInput("Style", "Regular", 0)
    text_tool.SetInput("Size", 0.08, 0)
    text_tool.SetInput("Red1", 1.0, 0)
    text_tool.SetInput("Green1", 1.0, 0)
    text_tool.SetInput("Blue1", 1.0, 0)

    print(f"Inserted Fusion text clip '{timeline_item.GetName()}' at {timecode_str}.")
    print(
        f"Check Resolve now: it should read '{TEST_TEXT}' in white "
        f"text, at {start_seconds}s, on the test track -- and IMPORTANT: "
        f"confirm nothing on your other tracks (footage, etc.) shifted "
        f"position because of this insert."
    )

    media_pool_item = timeline_item.GetMediaPoolItem()
    if media_pool_item is None:
        print(
            "\nCandidate A RESULT: GetMediaPoolItem() returned None. "
            "Not reusable this way -- skip 'check_reuse' and go "
            "straight to Candidate B (export_template)."
        )
    else:
        item_name = media_pool_item.GetName()
        print(
            f"\nCandidate A RESULT: GetMediaPoolItem() returned a real "
            f"item: '{item_name}'. Run 'check_reuse' to test it, or "
            f"skip to Candidate B (export_template) -- either is worth "
            f"checking."
        )


def run_check_reuse():
    resolve, project, timeline, media_pool = _connect()

    root_folder = media_pool.GetRootFolder()
    template_item = None
    for clip in root_folder.GetClipList():
        if clip.GetName() == f"{TEST_PREFIX}template":
            template_item = clip
            break

    if template_item is None:
        raise RuntimeError(
            f"Could not find a Media Pool item named "
            f"'{TEST_PREFIX}template'. Run 'bootstrap' then 'insert' first."
        )

    fps = float(timeline.GetSetting("timelineFrameRate"))
    reuse_track_name, reuse_track_index = _ensure_empty_track(
        timeline, f"{TEST_TRACK_NAME} - Reuse"
    )
    print(f"Created empty track: '{reuse_track_name}' (index {reuse_track_index})")

    before = _snapshot_other_tracks(timeline, reuse_track_index)

    record_frame = int(round(10.0 * fps))
    clip_info = {
        "mediaPoolItem": template_item,
        "startFrame": 0,
        "endFrame": int(round(4.0 * fps)),
        "trackIndex": reuse_track_index,
        "recordFrame": record_frame,
    }
    appended = media_pool.AppendToTimeline([clip_info])
    if not appended:
        print(
            "\nCandidate A RESULT: AppendToTimeline failed for the "
            "reused template item. Try Candidate B instead."
        )
        return

    appended[0].SetName(f"{TEST_PREFIX}reused")
    print(f"Appended reused clip '{appended[0].GetName()}' at 10s on '{reuse_track_name}'.")

    after = _snapshot_other_tracks(timeline, reuse_track_index)

    if before == after:
        print(
            "\nCandidate A RESULT: CONFIRMED. Safe to build ML-055 on "
            "this mechanism (one-time bootstrap + AppendToTimeline "
            "reuse, one shared track, one click ever per app session)."
        )
    else:
        print(
            "\nCandidate A RESULT: WARNING. Another track moved -- do "
            "NOT use this mechanism. Try Candidate B instead."
        )
        print(f"  before: {before}")
        print(f"  after:  {after}")


def run_export_template():
    resolve, project, timeline, media_pool = _connect()

    root_folder = media_pool.GetRootFolder()
    template_clip = None
    for track_index in range(1, timeline.GetTrackCount("video") + 1):
        for item in timeline.GetItemListInTrack("video", track_index):
            if item.GetName() == f"{TEST_PREFIX}template":
                template_clip = item
                break
        if template_clip:
            break

    if template_clip is None:
        raise RuntimeError(
            f"Could not find the '{TEST_PREFIX}template' clip on the "
            f"timeline. Run 'bootstrap' then 'insert' first."
        )

    export_dir = os.path.dirname(TEST_COMP_EXPORT_PATH)
    if not os.path.isdir(export_dir):
        os.makedirs(export_dir)

    if not template_clip.ExportFusionComp(TEST_COMP_EXPORT_PATH, 1):
        raise RuntimeError(
            f"ExportFusionComp() failed writing to '{TEST_COMP_EXPORT_PATH}'."
        )

    print(f"Exported Fusion composition to: {TEST_COMP_EXPORT_PATH}")
    print("Run 'import_on_placeholder' next.")


def run_import_on_placeholder():
    resolve, project, timeline, media_pool = _connect()

    if not os.path.isfile(TEST_COMP_EXPORT_PATH):
        raise RuntimeError(
            f"'{TEST_COMP_EXPORT_PATH}' does not exist. Run "
            f"'export_template' first."
        )

    root_folder = media_pool.GetRootFolder()
    placeholder_item = None
    for clip in root_folder.GetClipList():
        if clip.GetName() == CHANNEL_BUG_MEDIA_POOL_NAME:
            placeholder_item = clip
            break

    if placeholder_item is None:
        if not os.path.isfile(CHANNEL_BUG_IMAGE_PATH):
            raise RuntimeError(
                f"Placeholder image not found in Media Pool as "
                f"'{CHANNEL_BUG_MEDIA_POOL_NAME}', and fallback file "
                f"does not exist on disk either: '{CHANNEL_BUG_IMAGE_PATH}'."
            )
        imported = media_pool.ImportMedia([CHANNEL_BUG_IMAGE_PATH])
        if not imported:
            raise RuntimeError(f"ImportMedia failed for '{CHANNEL_BUG_IMAGE_PATH}'.")
        placeholder_item = imported[0]

    fps = float(timeline.GetSetting("timelineFrameRate"))
    placeholder_track_name, placeholder_track_index = _ensure_empty_track(
        timeline, f"{TEST_TRACK_NAME} - Placeholder"
    )
    print(f"Created empty track: '{placeholder_track_name}' (index {placeholder_track_index})")

    before = _snapshot_other_tracks(timeline, placeholder_track_index)

    record_frame = int(round(15.0 * fps))
    clip_info = {
        "mediaPoolItem": placeholder_item,
        "startFrame": 0,
        "endFrame": int(round(4.0 * fps)),
        "trackIndex": placeholder_track_index,
        "recordFrame": record_frame,
    }
    appended = media_pool.AppendToTimeline([clip_info])
    if not appended:
        print(
            "\nCandidate B RESULT: AppendToTimeline failed for the "
            "placeholder image. Cannot test ImportFusionComp on it."
        )
        return

    placeholder_placed = appended[0]
    placeholder_placed.SetName(f"{TEST_PREFIX}placeholder")
    print(f"Placed placeholder clip '{placeholder_placed.GetName()}' at 15s -- NO track click was needed for this step.")

    comp = placeholder_placed.ImportFusionComp(TEST_COMP_EXPORT_PATH)
    if comp is None:
        print(
            "\nCandidate B RESULT: ImportFusionComp() returned None. "
            "This mechanism does not work -- fall back to Candidate A "
            "(check_reuse) results instead."
        )
        return

    after = _snapshot_other_tracks(timeline, placeholder_track_index)

    print(f"Check Resolve now: '{placeholder_placed.GetName()}' at 15s should now show '{TEST_TEXT}' text.")

    if before == after:
        print(
            "\nCandidate B RESULT: CONFIRMED. ImportFusionComp() "
            "attached the saved template to an AppendToTimeline-placed "
            "item, and no other track moved. This is the mechanism to "
            "build ML-055 on -- zero manual clicks required per "
            "chapter, ever."
        )
    else:
        print(
            "\nCandidate B RESULT: WARNING. ImportFusionComp() worked, "
            "but another track moved -- investigate before using this."
        )
        print(f"  before: {before}")
        print(f"  after:  {after}")


def run_rollback():
    resolve, project, timeline, media_pool = _connect()

    removed = 0
    track_count = timeline.GetTrackCount("video")
    for track_index in range(1, track_count + 1):
        for item in timeline.GetItemListInTrack("video", track_index):
            if item.GetName().startswith(TEST_PREFIX):
                if timeline.DeleteClips([item]):
                    removed += 1

    track_count = timeline.GetTrackCount("video")
    for track_index in range(track_count, 0, -1):
        track_name = timeline.GetTrackName("video", track_index)
        if not track_name.startswith(TEST_TRACK_NAME):
            continue
        if not timeline.GetItemListInTrack("video", track_index):
            timeline.DeleteTrack("video", track_index)

    root_folder = media_pool.GetRootFolder()
    template_clips = [
        clip for clip in root_folder.GetClipList()
        if clip.GetName() == f"{TEST_PREFIX}template"
    ]
    if template_clips:
        media_pool.DeleteClips(template_clips)

    print(
        f"Removed {removed} test clip(s), any now-empty test track(s), "
        f"and the template Media Pool item."
    )
    print(
        f"NOTE: '{TEST_COMP_EXPORT_PATH}' was left on disk -- delete it "
        f"by hand if you don't want to keep it."
    )
    print("Check Resolve now: the timeline should be back to its original state.")


if __name__ == "__main__":
    valid = ("bootstrap", "insert", "check_reuse", "export_template", "import_on_placeholder", "rollback")
    if len(sys.argv) != 2 or sys.argv[1] not in valid:
        print(f"Usage: python test_chapter_title_bootstrap.py [{'|'.join(valid)}]")
        sys.exit(1)

    {
        "bootstrap": run_bootstrap,
        "insert": run_insert,
        "check_reuse": run_check_reuse,
        "export_template": run_export_template,
        "import_on_placeholder": run_import_on_placeholder,
        "rollback": run_rollback,
    }[sys.argv[1]]()