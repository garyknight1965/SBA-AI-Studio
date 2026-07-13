from pathlib import Path
import sys
import os

# ------------------------------------------------------------------
# Add project root to Python path
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("cwd      :", os.getcwd())
print("root     :", PROJECT_ROOT)
print("sys.path :", sys.path[0])

# ------------------------------------------------------------------

from sba_resolve.core.metadata.exiftool_engine import ExifToolEngine
from sba_resolve.core.metadata.metadata_mapper import MetadataMapper

engine = ExifToolEngine(
    exiftool_path=r"C:\Tools\ExifTool\exiftool\exiftool.exe"
)

from sba_resolve.core.metadata.metadata_normalizer import MetadataNormalizer

metadata = engine.read_folder(r"D:\Movies")
metadata = MetadataNormalizer.normalize(metadata)

media = MetadataMapper.map_many(
    metadata,
    Path(r"D:\Movies"),
)

print("=" * 60)
print(f"Mapped {len(media)} media files")
print("=" * 60)

for clip in media[:10]:
    print(clip)