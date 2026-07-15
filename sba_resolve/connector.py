"""
============================================================
SBA AI Studio
Resolve Connector
Version : 3.1.1 RC1
============================================================
"""

from sba_resolve.context import ResolveContext
from sba_resolve.commands.create_project import create_project
from sba_resolve.core.services.app_settings import (
    load_timeline_creation_enabled,
)
from sba_resolve.core.services.resolve_locator import (
    ensure_resolve_module_importable,
)
from sba_resolve.media_pool.media_pool_manager import MediaPoolManager
from sba_resolve.commands.create_timeline import create_timeline


class ResolveConnector:
    def __init__(self, project_data):
        ensure_resolve_module_importable()

        import DaVinciResolveScript as bmd

        self.context = ResolveContext()
        self.context.project_data = project_data
        print('='*60) ; print('SBA Resolve Connector') ; print('='*60); print()
        print('Connecting to Resolve...')
        self.context.resolve = bmd.scriptapp('Resolve')
        if self.context.resolve is None:
            raise RuntimeError('Unable to connect to DaVinci Resolve.')
        print('Connected.'); print()

    def create_project(self):
        print('STEP 1 : Create / Open Project'); print(); create_project(self.context)

    def media_pool(self):
        print('STEP 2 : Media Pool Manager'); print(); MediaPoolManager(self.context).run()

    def print_summary(self):
        r=self.context.report
        print() ; print('='*60); print('SBA Resolve Report'); print('='*60); print()
        print('Project'); print('-------'); print(self.context.project_data['project_name']); print()
        print('Bins'); print('----'); print(f'Created              : {r.bins_created}'); print(f'Existing             : {r.bins_existing}'); print()
        print('Media'); print('-----'); print(f'Imported             : {r.media_imported}'); print(f'Skipped              : {r.media_skipped}'); print(f'Missing              : {r.media_missing}'); print(f'Failed               : {r.media_failed}'); print()
        print(f'Warnings             : {len(r.warnings)}'); print(f'Errors               : {len(r.errors)}'); print()
        status='SUCCESS'
        if r.errors: status='FAILED'
        elif r.warnings: status='SUCCESS WITH WARNINGS'
        print(f'Status               : {status}') ; print('='*60)

    def run(self):
        print('='*60); print('Starting Resolve Pipeline'); print('='*60); print(); self.create_project(); self.media_pool(); print()
        if load_timeline_creation_enabled():
            print('STEP 3 : Create Timeline'); print(); create_timeline(self.context)
        else:
            print('STEP 3 : Create Timeline - SKIPPED (enable_timeline_creation is false in config/settings.json)')
        self.print_summary()
