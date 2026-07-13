"""
============================================================
SBA AI Studio
Resolve Command
Synchronize Bins
Version : Sprint 2 RC1
============================================================
"""


def sync_bins(context):
    """
    Synchronize Media Pool bins with the Bridge project.
    Creates only missing bins.
    """

    media_pool = context.media_pool
    root_folder = context.root_folder

    print("Synchronizing bins...")
    print()

    # Current folders
    existing_bins = {
        folder.GetName(): folder
        for folder in root_folder.GetSubFolderList()
    }

    # Requested folders
    requested_bins = context.project_data.get("bins", [])

    for bin_name in requested_bins:

        if bin_name in existing_bins:

            print(f"[OK ] {bin_name}")

            context.report.bins_existing += 1

            continue

        print(f"[NEW] {bin_name}")

        media_pool.AddSubFolder(
            root_folder,
            bin_name
        )

        context.report.bins_created += 1

    print()
    print("Bin synchronization complete.")