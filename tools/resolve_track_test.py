"""
============================================================
SBA AI Studio
Resolve Track API Test
RES-006C
============================================================
"""

import DaVinciResolveScript as bmd


def main():

    print("=" * 60)
    print("Resolve Track Test")
    print("=" * 60)

    resolve = bmd.scriptapp("Resolve")

    if resolve is None:
        raise RuntimeError("Unable to connect to Resolve.")

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()

    if project is None:
        raise RuntimeError("No Resolve project is open.")

    timeline = project.GetCurrentTimeline()

    if timeline is None:
        raise RuntimeError("No timeline is open.")

    print(f"Timeline : {timeline.GetName()}")

    before = timeline.GetTrackCount("video")
    print(f"Video Tracks Before : {before}")

    print("\nCreating Video Track...")

    result = timeline.AddTrack("video")

    print(f"AddTrack returned : {result}")

    after = timeline.GetTrackCount("video")
    print(f"Video Tracks After : {after}")

    if after > before:

        print("Renaming new track...")

        success = timeline.SetTrackName(
            "video",
            after,
            "HERO13 TEST"
        )

        print(f"SetTrackName returned : {success}")

        print()

        for i in range(1, after + 1):
            print(
                f"Track {i}: "
                f"{timeline.GetTrackName('video', i)}"
            )

    else:
        print("Track was not created.")

    print()
    print("Done.")


if __name__ == "__main__":
    main()