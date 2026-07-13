"""
Resolve Bridge
Cleanup Empty Duplicate Bins
"""


def cleanup_bins(project):

    media_pool = project.GetMediaPool()
    root = media_pool.GetRootFolder()

    print()
    print("=" * 60)
    print("Cleaning duplicate bins")
    print("=" * 60)

    folders = root.GetSubFolderList()

    seen = {}

    for folder in folders:

        name = folder.GetName()

        if name not in seen:
            seen[name] = folder
            continue

        clips = folder.GetClipList()

        if len(clips) == 0:

            print(f"Removing empty duplicate : {name}")

            media_pool.DeleteFolders([folder])

        else:

            print(f"Keeping duplicate with clips : {name}")

    print()
    print("Cleanup complete.")