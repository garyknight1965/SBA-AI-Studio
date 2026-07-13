from sba_resolve.core.project_scanner import ProjectScanner

scanner = ProjectScanner(r"D:\Movies\ABR")   # <-- change to one of your media folders

media = scanner.scan()

print("=" * 60)
print("Scanner Statistics")
print("=" * 60)
print(f"Folders scanned : {scanner.statistics.folders_scanned}")
print(f"Files scanned   : {scanner.statistics.files_scanned}")
print(f"Media found     : {scanner.statistics.media_found}")
print(f"Files skipped   : {scanner.statistics.files_skipped}")
print(f"Folders skipped : {scanner.statistics.folders_skipped}")
print(f"Errors          : {len(scanner.statistics.errors)}")
print(f"Elapsed         : {scanner.statistics.elapsed:.2f} sec")
print("=" * 60)

if media:
    print("\nFirst 10 files:")
    for item in media[:10]:
        print(item.relative_path)