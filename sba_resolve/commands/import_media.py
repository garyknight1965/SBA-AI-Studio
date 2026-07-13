"""
Resolve Bridge
Import Media
"""

def import_media(project, project_data):

    media_pool = project.GetMediaPool()

    print()
    print("Importing media...")
    print()

    for media in project_data["media"]:

        file_path = media["file"]

        print(f"Importing: {file_path}")

        media_pool.ImportMedia([file_path])

    print()
    print("Media import complete.")