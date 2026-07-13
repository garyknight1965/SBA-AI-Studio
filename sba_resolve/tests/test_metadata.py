import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.metadata import MetadataReader


def main():

    reader = MetadataReader()

    filename = input("Video file: ").strip()

    media = reader.read(filename)

    print()
    print("=" * 60)
    print("MEDIA INFORMATION")
    print("=" * 60)

    print(f"Filename   : {media.filename}")
    print(f"Camera     : {media.camera}")
    print(f"Resolution : {media.resolution}")
    print(f"FPS        : {media.fps}")
    print(f"Duration   : {media.duration}")
    print(f"Codec      : {media.codec}")
    print(f"GPS        : {media.gps}")
    print(f"Size       : {media.filesize}")


if __name__ == "__main__":
    main()