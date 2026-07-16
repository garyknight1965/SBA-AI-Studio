"""
============================================================
SBA AI Studio
Project Database
Version : 1.0.0
Sprint  : ML-030
============================================================

Persists a lightweight fingerprint of every media file seen in
a project between scans, so a later scan can detect:

    - Missing files   (previously seen, absent from this scan)
    - New files       (present now, never seen before)
    - Corrupted files (flagged by the Corruption Detector)

This is the "Project Database" output described for Core Module 1
(Project Scanner) in the SBA AI Studio product handover: a
persistent record of the project's media state. It is not a
Resolve project or timeline artifact - Resolve is never touched
here.

Storage format: one JSON file inside a hidden ".sba" folder at
the root of the scanned project, so it travels with the project
folder itself (e.g. on an external drive) rather than living only
inside the app's own settings.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from sba_resolve.core.models.corruption_report import CorruptionReport
from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.models.project_database_record import (
    ProjectDatabaseRecord,
)
from sba_resolve.core.models.scan_diff import ScanDiff

DB_FOLDER_NAME = ".sba"
DB_FILE_NAME = "project_database.json"


class ProjectDatabase:
    """
    Reads, updates, and persists the Project Database for one
    project root.
    """

    def __init__(self, project_root: str | Path):

        self.project_root = Path(project_root)

        self.db_path = (
            self.project_root / DB_FOLDER_NAME / DB_FILE_NAME
        )

    # -----------------------------------------------------
    # Persistence
    # -----------------------------------------------------

    def load(self) -> dict[str, ProjectDatabaseRecord]:
        """
        Load previously persisted records, keyed by relative
        path (posix style, forward slashes). Returns an empty
        dict if no database exists yet, or if it can't be
        parsed (e.g. corrupted JSON - fails safe rather than
        crashing the scan).
        """

        if not self.db_path.exists():
            return {}

        try:
            raw = json.loads(
                self.db_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}

        records: dict[str, ProjectDatabaseRecord] = {}

        for relative_path, fields in raw.items():

            try:
                records[relative_path] = ProjectDatabaseRecord(
                    **fields
                )
            except TypeError:
                # A record from a future/older schema version -
                # skip it rather than fail the whole load.
                continue

        return records

    def save(
        self,
        records: dict[str, ProjectDatabaseRecord],
    ) -> None:
        """
        Persist records to disk, creating the .sba folder if
        needed.
        """

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        serialisable = {
            relative_path: asdict(record)
            for relative_path, record in records.items()
        }

        self.db_path.write_text(
            json.dumps(serialisable, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # -----------------------------------------------------
    # Building records from a scan
    # -----------------------------------------------------

    def build_records(
        self,
        media_files: list[MediaFile],
        corruption_report: CorruptionReport | None,
        previous: dict[str, ProjectDatabaseRecord],
    ) -> dict[str, ProjectDatabaseRecord]:
        """
        Build the record set for this scan, carrying
        `first_seen` forward from `previous` where a file was
        already known.
        """

        now = datetime.now().isoformat(timespec="seconds")

        corrupted_lookup = {
            item.relative_path: item.reason
            for item in (
                corruption_report.corrupted
                if corruption_report
                else []
            )
        }

        records: dict[str, ProjectDatabaseRecord] = {}

        for media in media_files:

            key = str(media.relative_path).replace("\\", "/")

            existing = previous.get(key)

            records[key] = ProjectDatabaseRecord(
                relative_path=key,
                size=media.size,
                modified=(
                    media.modified.isoformat()
                    if media.modified
                    else ""
                ),
                corrupted=key in corrupted_lookup,
                corruption_reason=corrupted_lookup.get(key, ""),
                first_seen=existing.first_seen if existing else now,
                last_seen=now,
            )

        return records

    # -----------------------------------------------------
    # Diffing
    # -----------------------------------------------------

    def diff(
        self,
        previous: dict[str, ProjectDatabaseRecord],
        current: dict[str, ProjectDatabaseRecord],
    ) -> ScanDiff:
        """
        Compare the previous Project Database against the
        current scan's records.
        """

        previous_keys = set(previous.keys())
        current_keys = set(current.keys())

        new_files = sorted(current_keys - previous_keys)
        missing_files = sorted(previous_keys - current_keys)

        corrupted_files = sorted(
            key
            for key, record in current.items()
            if record.corrupted
        )

        newly_corrupted = sorted(
            key
            for key in corrupted_files
            if key not in previous or not previous[key].corrupted
        )

        unchanged_count = len(
            [
                key
                for key in (current_keys & previous_keys)
                if not current[key].corrupted
            ]
        )

        return ScanDiff(
            new_files=new_files,
            missing_files=missing_files,
            corrupted_files=corrupted_files,
            newly_corrupted=newly_corrupted,
            unchanged_count=unchanged_count,
        )
