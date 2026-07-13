"""
============================================================
SBA AI Studio
Resolve Command
Import Media

Version : RES-006E.2

Purpose:
    Import media into DaVinci Resolve Media Pool while
    preserving existing MediaPoolItem references.

Fix:
    Existing clips were detected and skipped, causing
    context.imported_items to become empty.

Now:
    Existing Resolve clips are reused and returned to
    the Timeline Builder.
============================================================
"""

from pathlib import Path

from sba_resolve.media_pool.services.resolve_media_pool_service import (
    ResolveMediaPoolService,
)



def import_media(context):
    """
    Imports all media from the current SBA project into Resolve.

    Returns:
        List of Resolve MediaPoolItems.

    Existing clips in Resolve are reused.
    """


    service = ResolveMediaPoolService(context)

    media_entries = context.project_data.get(
        "media",
        []
    )

    imported_items = []


    print("=" * 60)
    print("Import Media")
    print("=" * 60)



    for entry in media_entries:


        source = entry.get(
            "file"
        )


        if not source:

            context.report.errors.append(
                "Media entry missing 'file'."
            )

            continue



        source_path = Path(
            source
        )


        if not source_path.exists():

            print(
                f"[MISS] {source_path}"
            )

            context.report.warnings.append(
                f"Missing: {source_path}"
            )

            continue



        try:

            folder = service.ensure_folder(
                entry
            )


        except RuntimeError as exc:


            print(
                f"[ERR ] {exc}"
            )

            context.report.errors.append(
                str(exc)
            )

            continue



        # --------------------------------------------------
        # Import or reuse existing Resolve clip
        # --------------------------------------------------

        item = service.import_file(
            folder,
            source_path
        )


        if item is None:


            print(
                f"[FAIL] {source_path.name}"
            )


            context.report.errors.append(
                f"Import failed: {source_path}"
            )


            continue



        imported_items.append(
            item
        )


        print(
            f"[ OK ] {source_path.name}"
        )



    # ------------------------------------------------------
    # Preserve Resolve references for Timeline Builder
    # ------------------------------------------------------

    context.imported_items = imported_items



    print()

    print(
        f"Imported : {len(imported_items)}"
    )

    print(
        f"Warnings : {len(context.report.warnings)}"
    )

    print(
        f"Errors   : {len(context.report.errors)}"
    )


    return imported_items