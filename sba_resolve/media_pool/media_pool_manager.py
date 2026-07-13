"""
============================================================
SBA AI Studio
Media Pool Manager
Version : 3.0.0 RC2
============================================================
"""

from sba_resolve.commands.sync_bins import sync_bins
from sba_resolve.media_pool.commands.remove_empty_duplicate_bins import (
    remove_empty_duplicate_bins,
)
from sba_resolve.media_pool.commands.import_media import import_media


class MediaPoolManager:
    """
    Coordinates all Media Pool operations.
    """

    def __init__(self, context):
        self.context = context

    def synchronize_bins(self):
        print("=" * 60)
        print("Media Pool")
        print("=" * 60)
        print()
        print("Stage 1 : Synchronize Bins")
        print()
        sync_bins(self.context)

    def cleanup_duplicate_bins(self):
        print()
        print("Stage 2 : Remove Empty Duplicate Bins")
        print()
        remove_empty_duplicate_bins(self.context)

    def import_media(self):
        print()
        print("Stage 3 : Import Media")
        print()
        import_media(self.context)

    def run(self):
        self.synchronize_bins()
        self.cleanup_duplicate_bins()
        self.import_media()
