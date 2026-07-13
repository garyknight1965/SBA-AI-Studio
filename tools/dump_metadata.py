import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.metadata import MetadataReader

reader = MetadataReader()

filename = input("Video file: ").strip()

metadata = reader.read(filename)

print()
print("=" * 80)
print("RAW METADATA")
print("=" * 80)

pprint(metadata)