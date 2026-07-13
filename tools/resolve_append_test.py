"""
============================================================
SBA AI Studio
Resolve Append Test
RES-006D
============================================================
"""

import DaVinciResolveScript as bmd


def main():

    print("=" * 60)
    print("Resolve Append Test")
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

    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")

    timeline.SetTrackName(
        "video",
        2,
        "TEST TRACK",
    )

    clips = media_pool.GetRootFolder().GetClipList()

    if not clips:
        raise RuntimeError("No clips found in Media Pool.")

    clip = clips[0]

    print()
    print("Trying normal AppendToTimeline()...")

    try:

        result = media_pool.AppendToTimeline(
            [
                {
                    "mediaPoolItem": clip,
                    "trackIndex": 2,
                }
            ]
        )

        print("AppendToTimeline returned :", result)

    except Exception as ex:

        print("AppendToTimeline exception:")
        print(ex)

    print()
    print("Video Tracks")

    for i in range(1, timeline.GetTrackCount("video") + 1):

        print(
            f"{i}: {timeline.GetTrackName('video', i)}"
        )

    print()
    print("Finished.")


if __name__ == "__main__":
    main()