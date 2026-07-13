"""
============================================================
SBA AI Studio
Resolve Command
Verify Media
Version : 3.1.0 RC1
============================================================
"""

from pathlib import Path

from sba_resolve.media_pool.services.resolve_media_pool_service import (
    ResolveMediaPoolService,
)


def verify_media(context):
    """
    Verify that every Bridge media entry exists in the expected
    Resolve Media Pool bin.
    """

    service = ResolveMediaPoolService(context)

    media_entries = context.project_data.get("media", [])

    verified = 0
    missing = 0

    print("Verifying media...")
    print()

    for entry in media_entries:

        source = entry.get("file")

        if not source:
            continue

        try:
            folder = service.ensure_folder(entry)
        except RuntimeError as exc:
            print(f"[ERR ] {exc}")
            context.report.errors.append(str(exc))
            continue

        filename = Path(source).name

        clip = service.find_clip(folder, filename)

        if clip is None:
            print(f"[MISS] {filename}")
            missing += 1
            context.report.warnings.append(
                f"Media not found in Resolve: {filename}"
            )
        else:
            print(f"[ OK ] {filename}")
            verified += 1

    print()
    print("Verification complete.")
    print(f"Verified : {verified}")
    print(f"Missing  : {missing}")
