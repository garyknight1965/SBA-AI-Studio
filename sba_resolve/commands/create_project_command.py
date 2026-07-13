"""
============================================================
SBA AI Studio
Create Project Command
Version : 1.0.0
Sprint : RV-002
============================================================
"""

from __future__ import annotations

from sba_resolve.context import ResolveContext


class CreateProjectCommand:
    """
    Creates or opens a Resolve project.
    """

    def __init__(self, context: ResolveContext):

        self.context = context

    def execute(
        self,
        project_name: str,
    ):

        pm = self.context.project_manager

        if pm is None:
            raise RuntimeError(
                "Project Manager not available."
            )

        project = pm.LoadProject(project_name)

        if project is None:

            project = pm.CreateProject(project_name)

            if project is None:

                raise RuntimeError(
                    f"Unable to create project '{project_name}'."
                )

            self.context.report.project_created = True

        self.context.project = project

        self.context.media_pool = project.GetMediaPool()

        self.context.root_folder = (
            self.context.media_pool.GetRootFolder()
        )

        return project