"""
============================================================
SBA AI Studio
Media Pool Command
Remove Empty Duplicate Bins
Version : 3.0.0-RC1
============================================================

Scans the Media Pool root folder for duplicate bins.

Rules

- Keep the first occurrence.
- Remove duplicate bins only if they are empty.
- Never remove bins containing clips.
- Record warnings for duplicate bins containing clips.
"""

from collections import defaultdict


def remove_empty_duplicate_bins(context):
    """
    Remove empty duplicate Media Pool bins.

    Parameters
    ----------
    context : ResolveContext
        Shared Resolve runtime context.
    """

    media_pool = context.media_pool
    root_folder = context.root_folder

    print("Removing empty duplicate bins...")
    print()

    folders_by_name = defaultdict(list)

    # ---------------------------------------------------------
    # Group folders by name
    # ---------------------------------------------------------

    for folder in root_folder.GetSubFolderList():
        folders_by_name[folder.GetName()].append(folder)

    removed = 0

    # ---------------------------------------------------------
    # Process duplicates
    # ---------------------------------------------------------

    for name, folders in folders_by_name.items():

        if len(folders) == 1:
            continue

        # Keep the first folder
        for duplicate in folders[1:]:

            clips = duplicate.GetClipList()

            if clips:

                warning = (
                    f"Duplicate bin '{name}' contains "
                    f"{len(clips)} clip(s). Bin preserved."
                )

                print(f"[KEEP] {warning}")

                context.report.warnings.append(warning)

                continue

            print(f"[DELETE] Empty duplicate bin: {name}")

            media_pool.DeleteFolders([duplicate])

            removed += 1

    print()
    print(f"Duplicate bins removed : {removed}")