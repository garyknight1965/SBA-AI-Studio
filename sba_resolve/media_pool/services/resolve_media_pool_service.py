"""
============================================================
SBA AI Studio
Resolve Media Pool Service
Version : 3.0.0 RC2
============================================================

Thin wrapper around the DaVinci Resolve Media Pool API.
Business logic belongs in commands.
"""

from pathlib import Path


class ResolveMediaPoolService:
    """Wrapper around Resolve Media Pool operations."""

    def __init__(self, context):
        self.context = context
        self.media_pool = context.media_pool
        self.root_folder = context.root_folder

    def set_current_folder(self, folder):
        self.media_pool.SetCurrentFolder(folder)

    def find_bin(self, name, parent=None):
        parent = parent or self.root_folder
        for folder in parent.GetSubFolderList():
            if folder.GetName() == name:
                return folder
        return None

    def find_bin_by_path(self, bin_path):
        current = self.root_folder
        for part in [p.strip() for p in str(bin_path).split("/") if p.strip()]:
            current = self.find_bin(part, current)
            if current is None:
                return None
        return current

    def find_clip(self, folder, filename):
        for clip in folder.GetClipList():
            props = clip.GetClipProperty()
            clip_name = props.get("File Name") or props.get("Clip Name") or ""
            if clip_name.lower() == filename.lower():
                return clip
        return None

    def clip_exists(self, folder, filepath):
        return self.find_clip(folder, Path(filepath).name) is not None

    def import_file(self, folder, filepath):
        self.set_current_folder(folder)
        imported = self.media_pool.ImportMedia([str(filepath)])
        if not imported:
            return None
        if isinstance(imported, list):
            return imported[0] if imported else None
        return imported

    def delete_folder(self, folder):
        return self.media_pool.DeleteFolders([folder])

    def refresh(self):
        self.media_pool = self.context.project.GetMediaPool()
        self.root_folder = self.media_pool.GetRootFolder()

    def get_bin(self, media_entry):
        bin_path = media_entry.get("bin_path") or media_entry.get("bin")
        if not bin_path:
            return None
        return self.find_bin_by_path(bin_path)

    def ensure_folder(self, media_entry):
        folder = self.get_bin(media_entry)
        if folder is None:
            raise RuntimeError(
                "Media Pool folder not found: "
                f"{media_entry.get('bin_path') or media_entry.get('bin')}"
            )
        return folder
