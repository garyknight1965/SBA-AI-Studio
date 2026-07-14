"""
============================================================
SBA AI Studio
Resolve Gap Placement Test
RES-006G (exploratory)
============================================================

Purpose:

Find out whether DaVinci Resolve's scripting API lets us place
a clip at an exact frame position on a track - leaving a real,
visible gap before it - rather than always appending clips
back-to-back with no space between them.

This is required for the synced multicam timeline feature:
if a camera was switched off for part of the ride, its track
needs an empty gap for that period instead of its next clip
sliding forward to fill the space.

This script does NOT change your app. It only experiments
directly against the Resolve API and prints what happened, so
we can decide how the real feature should place clips.

How to run:

1. Open a DaVinci Resolve project with a timeline that has
   at least 2 clips already imported into the Media Pool.
2. Workspace -> Console -> Py3
3. Paste and run this whole script (or run it via the Console's
   "Run Script" if you have this file saved locally).
4. Look at the printed output AND look at the timeline in
   Resolve afterwards - check track 3 ("GAP TEST") visually.
"""

import DaVinciResolveScript as bmd


GAP_FRAMES = 150  # ~5 seconds at 30fps - deliberately large so the
                   # gap is obvious to see on the timeline


def main():

    print("=" * 60)
    print("Resolve Gap Placement Test")
    print("=" * 60)

    resolve = bmd.scriptapp("Resolve")

    if resolve is None:
        raise RuntimeError("Unable to connect to Resolve.")

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()

    if project is None:
        raise RuntimeError("No project open.")

    media_pool = project.GetMediaPool()

    timeline = project.GetCurrentTimeline()

    if timeline is None:
        raise RuntimeError("No timeline open.")

    print("Timeline :", timeline.GetName())
    print("Frame rate:", timeline.GetSetting("timelineFrameRate"))

    # --------------------------------------------------------
    # Get two clips to work with (search all bins recursively -
    # imported clips live in camera-named sub-bins, not root)
    # --------------------------------------------------------

    def collect_clips(folder):
        found = list(folder.GetClipList())
        for subfolder in folder.GetSubFolderList():
            found.extend(collect_clips(subfolder))
        return found

    clips = collect_clips(media_pool.GetRootFolder())

    if not clips or len(clips) < 2:
        raise RuntimeError("Need at least 2 clips in the Media Pool.")

    clip_a = clips[0]
    clip_b = clips[1]

    print(f"Clip A : {clip_a.GetName()}")
    print(f"Clip B : {clip_b.GetName()}")

    # --------------------------------------------------------
    # Ensure a dedicated test track exists (track 3)
    # --------------------------------------------------------

    while timeline.GetTrackCount("video") < 3:
        if not timeline.AddTrack("video"):
            raise RuntimeError("Unable to add test video track.")

    timeline.SetTrackName("video", 3, "GAP TEST")

    print()
    print("Using video track 3 ('GAP TEST') for this experiment.")
    print()

    # --------------------------------------------------------
    # Step 1: append Clip A normally at the start of the track
    # --------------------------------------------------------

    result_a = media_pool.AppendToTimeline(
        [
            {
                "mediaPoolItem": clip_a,
                "trackIndex": 3,
            }
        ]
    )

    print("Append Clip A (normal, no position) :", bool(result_a))

    items_after_a = timeline.GetItemListInTrack("video", 3)

    if items_after_a:
        end_of_a = items_after_a[-1].GetEnd()
        print(f"Clip A ends at frame : {end_of_a}")
    else:
        end_of_a = None
        print("WARNING: Could not read Clip A position after append.")

    # ----------------------------------------