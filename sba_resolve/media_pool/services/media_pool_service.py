"""
============================================================
SBA AI Studio
Resolve Media Pool Service
Version : 3.0.1
RES-006E Fix - Preserve Resolve MediaPoolItems
============================================================

Thin wrapper around the DaVinci Resolve Media Pool API.

Responsibilities:
- Resolve folder handling
- Find existing MediaPoolItems
- Import media
- Return valid MediaPoolItem references

Business logic remains in commands.
============================================================
"""

from pathlib import Path


class ResolveMediaPoolService:
    """
    Wrapper around Resolve Media Pool operations.
    """

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

        parts = [
            p.strip()
            for p in str(bin_path).split("/")
            if p.strip()
        ]

        for part in parts:

            current = self.find_bin(
                part,
                current
            )

            if current is None:
                return None

        return current



    def find_clip(self, folder, filename):

        if folder is None:
            return None


        for clip in folder.GetClipList():

            try:

                props = clip.GetClipProperty()

                clip_name = (
                    props.get("File Name")
                    or props.get("Clip Name")
                    or ""
                )

            except Exception:

                continue


            if clip_name.lower() == filename.lower():

                return clip


        return None



    def clip_exists(self, folder, filepath):

        return (
            self.find_clip(
                folder,
                Path(filepath).name
            )
            is not None
        )



    def import_file(self, folder, filepath):
        """
        Return an existing MediaPoolItem if Resolve already
        contains the file.

        Otherwise import the file and return the new item.

        RES-006E:
        Never discard existing Resolve references.
        """

        filepath = Path(filepath)

        self.set_current_folder(folder)


        # --------------------------------------------------
        # Existing Resolve item
        # --------------------------------------------------

        existing = self.find_clip(
            folder,
            filepath.name
        )


        if existing:

            print(
                f"[EXISTING] {filepath.name}"
            )

            return existing



        # --------------------------------------------------
        # New import
        # --------------------------------------------------

        imported = self.media_pool.ImportMedia(
            [
                str(filepath)
            ]
        )


        if not imported:

            print(
                f"[IMPORT FAILED] {filepath.name}"
            )

            return None



        if isinstance(imported, list):

            if len(imported) == 0:

                return None


            return imported[0]


        return imported



    def delete_folder(self, folder):

        return self.media_pool.DeleteFolders(
            [
                folder
            ]
        )



    def refresh(self):

        self.media_pool = (
            self.context.project.GetMediaPool()
        )

        self.root_folder = (
            self.media_pool.GetRootFolder()
        )



    def get_bin(self, media_entry):

        bin_path = (
            media_entry.get("bin_path")
            or media_entry.get("bin")
        )


        if not bin_path:

            return None


        return self.find_bin_by_path(
            bin_path
        )



    def ensure_folder(self, media_entry):

        folder = self.get_bin(
            media_entry
        )


        if folder is None:

            raise RuntimeError(
                "Media Pool folder not found: "
                f"{media_entry.get('bin_path') or media_entry.get('bin')}"
            )


        return folder