from sba_resolve.core.services.media_library_service import (
    MediaLibraryService,
)

service = MediaLibraryService()

library = service.import_folder(r"D:\Movies\ABR")

print("=" * 60)
print("MEDIA LIBRARY")
print("=" * 60)

print(f"Files      : {library.total_files}")
print(f"Videos     : {len(library.video_files)}")
print(f"Images     : {len(library.image_files)}")
print(f"Audio      : {len(library.audio_files)}")
print(f"Cameras    : {library.cameras}")
print(f"Categories : {library.categories}")
print(f"Total Size : {library.total_size:,} bytes")

print("=" * 60)

stats = service.statistics

print("SCAN")

print(f"Folders : {stats.folders_scanned}")
print(f"Files   : {stats.files_scanned}")
print(f"Errors  : {len(stats.errors)}")

print("=" * 60)

for media in library[:10]:
    print(
        media.camera_display_name,
        media.filename,
        media.created,
    )