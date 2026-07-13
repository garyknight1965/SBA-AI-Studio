"""
============================================================
SBA AI Studio
Camera Assignment Repository
CORE-011C
Version : 1.0.0 Alpha
============================================================

Maps CameraProfiles to project-specific CameraAssignments.
"""

from __future__ import annotations

from typing import Dict

from sba_resolve.core.models.camera_assignment import CameraAssignment
from sba_resolve.core.models.camera_profile import CameraProfile


class CameraAssignmentRepository:
    """
    Stores and resolves CameraAssignments for the current project.

    For now this is an in-memory repository.
    Later it will be backed by the project configuration.
    """

    def __init__(self) -> None:

        self._assignments: Dict[str, CameraAssignment] = {}

    @staticmethod
    def _key(profile: CameraProfile) -> str:

        return f"{profile.manufacturer.value}:{profile.model}"

    def register(self, assignment: CameraAssignment) -> None:

        self._assignments[
            self._key(assignment.profile)
        ] = assignment

    def resolve(
        self,
        profile: CameraProfile,
    ) -> CameraAssignment | None:

        return self._assignments.get(
            self._key(profile)
        )

    def contains(
        self,
        profile: CameraProfile,
    ) -> bool:

        return self._key(profile) in self._assignments

    def clear(self) -> None:

        self._assignments.clear()

    @property
    def count(self) -> int:

        return len(self._assignments)

    def __len__(self) -> int:

        return self.count