"""
============================================================
SBA AI Studio
Resolve Command
Synchronize Bins
Version : ML-024
============================================================

Synchronizes Media Pool bins with the requested bin paths.

Version ML-024 adds support for NESTED bin paths (e.g.
"Day 1/GoPro HERO13 Black") - each requested bin now lives
inside a per-day folder containing a sub-bin per camera,
instead of one flat list of camera bins at the project root.
Any missing folder along the path (the day folder itself, then
the camera sub-folder within it) is created automatically via
ResolveMediaPoolService.ensure_bin_path().
"""

from sba_resolve.media_pool.services.resolve_media_pool_service import (
    ResolveMediaPoolService,
)


def sync_bins(context):
    """
    Synchronize Media Pool bins with the Bridge project.
    Creates only missing bins (and any missing parent folder
    along a nested path, e.g. the day folder for a new day).
    """

    service = ResolveMediaPoolService(context)

    print("Synchronizing bins...")
    print()

    # Requested bin paths, e.g. "Day 1/GoPro HERO13 Black".
    requested_bins = context.project_data.get("bins", [])

    for bin_path in requested_bins:

        existing = service.find_bin_by_path(bin_path)

        if existing is not None:

            print(f"[OK ] {bin_path}")

            context.report.bins_existing += 1

            continue

        print(f"[NEW] {bin_path}")

        service.ensure_bin_path(bin_path)

        context.report.bins_created += 1

    print()
    print("Bin synchronization complete.")
