"""
============================================================
SBA AI Studio
Resolve Command
Create Project
============================================================
"""

def create_project(context):
    """
    Create or open a DaVinci Resolve project.
    """

    resolve = context.resolve
    project_name = context.project_data["project_name"]

    project_manager = resolve.GetProjectManager()

    print(f"Project : {project_name}")

    project = project_manager.LoadProject(project_name)

    if project is None:

        print("Creating project...")

        project = project_manager.CreateProject(project_name)

        context.report.project_created = True

    else:

        print("Opening existing project...")

    context.project = project
    context.media_pool = project.GetMediaPool()
    context.root_folder = context.media_pool.GetRootFolder()

    print("Project ready.")