"""
tools/test_graphic_inserter.py

Manual smoke test for resolve_graphic_inserter.py, matching the test
procedure in the ML-044/045/046 Part 1 task handoff:

    1. Call the module directly with a test timecode/text/template
       reference on a sample project.
    2. Confirm a correctly named, correctly positioned, correctly timed
       clip appears on a new track.
    3. Confirm deleting that one clip fully reverts the timeline (no
       other tracks/clips touched).

Run this with Resolve open, a real project loaded, and a real timeline
active.

Four independent smoke tests, plus a diagnostic:
    - insert_image: places the real channel bug logo (Power Bin lookup,
      graphics_config.CHANNEL_BUG_MEDIA_POOL_NAME, with disk fallback)
    - insert_intro: places "Intro 2026" (Power Bin only, full native
      duration) as an overlay at time 0 on its own track -- confirm it
      does NOT shift or affect anything already on the main track
    - prepare_text_track: STEP 1 of 2 for text inserts. Creates a new,
      empty, uniquely-named video track and prints its name. This is a
      REQUIRED separate step -- CONFIRMED via testing that skipping it
      and going straight to insert_text places the clip on whatever
      track happens to be active in the UI (e.g. your real footage).
    - insert_text: STEP 2 of 2. Only run this AFTER prepare_text_track
      and AFTER manually clicking that exact track in Resolve.
    - list_assets: diagnostic, lists everything the Media Pool API can see

Usage:
    python tools/test_graphic_inserter.py insert_image
    python tools/test_graphic_inserter.py insert_intro
    python tools/test_graphic_inserter.py prepare_text_track
    (click the printed track name in Resolve now)
    python tools/test_graphic_inserter.py insert_text
    python tools/test_graphic_inserter.py rollback
"""

import sys

sys.path.insert(0, "..")  # allow running from tools/ directly

from resolve_graphic_inserter import GraphicInserter, GraphicRequest
from graphics_config import (
    CHANNEL_BUG_IMAGE_PATH,
    CHANNEL_BUG_MEDIA_POOL_NAME,
    INTRO_CLIP_MEDIA_POOL_NAME,
    INTRO_CLIP_IMAGE_PATH,
)


TEST_PREFIX = "AI_SmokeTest_"
TEST_TRACK_NAME = "AI Smoke Test"
TEXT_LABEL = "Smoke Test Clip"


def run_insert_image_test():
    inserter = GraphicInserter()
    inserter.connect()

    request = GraphicRequest(
        media_pool_name=CHANNEL_BUG_MEDIA_POOL_NAME,
        image_path=CHANNEL_BUG_IMAGE_PATH,
        start_seconds=5.0,
        duration_seconds=4.0,
        track_name=TEST_TRACK_NAME,
        clip_name_prefix=TEST_PREFIX,
        scale=1.0,
        position="bottom_right",
        opacity=0.35,
    )

    clip_name = inserter.insert(request)
    print(f"Inserted clip: {clip_name}")
    print(
        f"Check Resolve now: your logo should appear on track "
        f"'{TEST_TRACK_NAME}' at 5s, lasting 4s, bottom-right, at 35% "
        f"opacity."
    )


def run_list_assets():
    inserter = GraphicInserter()
    inserter.connect()

    clips = inserter.list_all_media_pool_clips()
    print(f"Found {len(clips)} clip(s) in the Media Pool (including Power Bins if visible):")
    for folder_path, clip_name in clips:
        print(f"  {folder_path} / {clip_name}")
    print()
    print(
        "Look for your logo and 'Intro 2026' in this list -- check exact "
        "spelling/capitalization/extension, and confirm the Power Bin "
        "folder path actually shows up here at all."
    )


def run_insert_intro_test():
    inserter = GraphicInserter()
    inserter.connect()

    request = GraphicRequest(
        media_pool_name=INTRO_CLIP_MEDIA_POOL_NAME,
        image_path=INTRO_CLIP_IMAGE_PATH,
        start_seconds=0.0,
        use_full_duration=True,
        track_name=TEST_TRACK_NAME,
        clip_name_prefix=TEST_PREFIX,
        scale=1.0,
        position="default",
        opacity=1.0,
    )

    clip_name = inserter.insert(request)
    print(f"Inserted clip: {clip_name}")
    print(
        f"Check Resolve now: 'Intro 2026' should appear on its own new "
        f"track '{TEST_TRACK_NAME}' starting at 0s, running its full "
        f"native length. IMPORTANT: confirm your existing footage on the "
        f"main track is completely unaffected -- nothing should have "
        f"shifted."
    )


def run_prepare_text_track():
    inserter = GraphicInserter()
    inserter.connect()

    track_name = inserter.prepare_text_track(TEST_TRACK_NAME, TEXT_LABEL)
    print(f"Created empty track: '{track_name}'")
    print(
        f">>> ACTION NEEDED: click on track '{track_name}' in the Resolve "
        f"timeline panel RIGHT NOW to select/activate it. <<<\n"
        f"Only after you've clicked it, run: python test_graphic_inserter.py insert_text"
    )


def run_insert_text_test():
    inserter = GraphicInserter()
    inserter.connect()

    request = GraphicRequest(
        text=TEXT_LABEL,
        start_seconds=12.0,
        duration_seconds=4.0,
        track_name=TEST_TRACK_NAME,
        clip_name_prefix=TEST_PREFIX,
        scale=1.0,
        position="default",
        opacity=1.0,
    )

    clip_name = inserter.insert(request)
    print(f"Inserted clip: {clip_name}")
    print(
        f"Check Resolve now: a clip named '{clip_name}' should appear "
        f"reading '{TEXT_LABEL}' in white Impact-style text, at 12s, "
        f"lasting ~4s (duration control still unconfirmed). IMPORTANT: "
        f"confirm it landed on the track you just clicked (from "
        f"prepare_text_track), NOT your main Video 1 track -- if it's "
        f"on Video 1, the manual track-click step wasn't done before "
        f"running this."
    )


def run_rollback_test():
    inserter = GraphicInserter()
    inserter.connect()

    removed = inserter.remove_by_prefix(TEST_PREFIX)
    print(f"Removed {removed} clip(s) with prefix '{TEST_PREFIX}'.")
    print(
        "Check Resolve now: the smoke test clip should be gone, and "
        "nothing else on the timeline should have changed."
    )


if __name__ == "__main__":
    valid = ("insert_image", "prepare_text_track", "insert_text", "insert_intro", "list_assets", "rollback")
    if len(sys.argv) != 2 or sys.argv[1] not in valid:
        print(f"Usage: python test_graphic_inserter.py [{'|'.join(valid)}]")
        sys.exit(1)

    if sys.argv[1] == "insert_image":
        run_insert_image_test()
    elif sys.argv[1] == "prepare_text_track":
        run_prepare_text_track()
    elif sys.argv[1] == "insert_text":
        run_insert_text_test()
    elif sys.argv[1] == "insert_intro":
        run_insert_intro_test()
    elif sys.argv[1] == "list_assets":
        run_list_assets()
    else:
        run_rollback_test()
