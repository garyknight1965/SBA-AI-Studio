"""
============================================================
SBA AI Studio
Resolve Connector
Version : 3.3.0
============================================================

Version 3.2.0 (2026-07-24): added a gated STEP 4 - Auto Camera
LUTs - calling apply_camera_luts_to_timeline() right after
timeline creation, matching the existing enable_timeline_creation
gating pattern. Gated by load_auto_camera_luts_enabled() (config
key "enable_auto_camera_luts", OFF by default). Only runs at all
if timeline creation itself ran (STEP 3) - applying LUTs to a
timeline that was never created, or was skipped, makes no sense.

Version 3.3.0 (2026-07-24): adds apply_camera_luts_now() - a
standalone, on-demand entry point for re-running just the LUT
step against whatever project is CURRENTLY OPEN in Resolve
(via ProjectManager.GetCurrentProject(), not LoadProject() by
name - this never creates or opens a project, only uses one
that's already open). For use after manually syncing/placing
clips that were left as "Manual Sync Required" placeholders
during the main pipeline run (e.g. HERO8 Black multicam clips,
since audio sync is disabled by default) - re-running the whole
pipeline isn't needed just to grade newly-placed clips, only this
one step. Wired to a File menu action in main_window.py.
"""
from sba_resolve.context import ResolveContext
from sba_resolve.commands.create_project import create_project
from sba_resolve.core.services.app_settings import (
    load_timeline_creation_enabled,
    load_auto_camera_luts_enabled,
)
from sba_resolve.core.services.resolve_locator import (
    ensure_resolve_module_importable,
)
from sba_resolve.media_pool.media_pool_manager import MediaPoolManager
from sba_resolve.commands.create_timeline import create_timeline
from sba_resolve.commands.apply_camera_luts_to_timeline import (
    apply_camera_luts_to_timeline,
)
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
        timeline_created = False
        if load_timeline_creation_enabled():
            print('STEP 3 : Create Timeline'); print(); create_timeline(self.context); timeline_created = True
        else:
            print('STEP 3 : Create Timeline - SKIPPED (enable_timeline_creation is false in config/settings.json)')
        print()
        if timeline_created and load_auto_camera_luts_enabled():
            print('STEP 4 : Auto Camera LUTs'); print(); apply_camera_luts_to_timeline(self.context)
        elif timeline_created:
            print('STEP 4 : Auto Camera LUTs - SKIPPED (enable_auto_camera_luts is false in config/settings.json)')
        else:
            print('STEP 4 : Auto Camera LUTs - SKIPPED (no timeline was created)')
        self.print_summary()


def apply_camera_luts_now(media_list):
    """
    Standalone, on-demand re-run of the Auto Camera LUT step
    against whatever project is CURRENTLY OPEN in Resolve.

    Deliberately does NOT create or load a project by name (unlike
    ResolveConnector.create_project(), which calls LoadProject())
    - this only ever acts on a project the person already has open
    in Resolve, via ProjectManager.GetCurrentProject(). If nothing
    is open, this raises rather than silently creating one, since
    creating a new empty project would be a confusing side effect
    of what's meant to be a narrow "re-grade the clips I just
    synced" action.

    Also does not touch the Media Pool or create a timeline - this
    only calls apply_camera_luts_to_timeline(), which itself only
    reads whatever timeline is already current and walks its
    already-placed clips.

    media_list is used the same way ResolveConnector's
    project_data["media_objects"] is - to match camera profiles to
    timeline clips by filename (see apply_camera_luts_to_timeline.py's
    _apply()). Pass self.workspace.media from the caller.
    """
    ensure_resolve_module_importable()
    import DaVinciResolveScript as bmd

    resolve = bmd.scriptapp('Resolve')
    if resolve is None:
        raise RuntimeError('Unable to connect to DaVinci Resolve.')

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if project is None:
        raise RuntimeError(
            'No project is currently open in DaVinci Resolve - '
            'open the project first, then try again.'
        )

    context = ResolveContext()
    context.resolve = resolve
    context.project = project
    context.project_data = {"media_objects": list(media_list)}

    return apply_camera_luts_to_timeline(context)
