import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.project import Project
from core.scanner import Scanner


def main():

    folder = input("Folder to scan: ").strip()

    project = Project("ABR Festival 2026")

    project.set_media_folder(folder)

    scanner = Scanner(folder)

    library = scanner.scan()

    project.set_library(library)

    project.save("projects/ABR Festival 2026.sba")

    print()
    print("=" * 60)
    print("PROJECT SAVED")
    print("=" * 60)

    print()

    print("Project:")
    print(project.name)

    print()

    print("Saved to:")

    print("projects/ABR Festival 2026.sba")


if __name__ == "__main__":
    main()