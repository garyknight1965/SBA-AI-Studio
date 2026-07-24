"""
============================================================
SBA AI Studio
Apply Camera LUTs To Timeline
Version : 1.2.0
============================================================

Applies a per-camera-manufacturer LUT (configured via
load_camera_luts() in app_settings.py) to every clip already
placed on the current timeline, via TimelineItem.SetLUT(). This
is the timeline-level counterpart to the Media-Pool-level
approach originally attempted as ML-072 (SetClipProperty("Input
LUT", ...)), which was reverted after live testing confirmed
Resolve's scripting API doesn't actually apply it. This is the
real, working mechanism.

Version 1.2.0 (2026-07-24): fixed a mangled-encoding bug where
the success/failure symbols were being printed as garbled bytes
("Ã¢Å"“"-style mojibake, saved in source as literal "âœ“"/"âœ—")
instead of real checkmark/cross characters - likely from a prior
save/read encoding mismatch. Now printed as plain "[OK]"/"[FAIL]"
instead of a unicode symbol, to avoid any repeat of the same
class of encoding issue on a Windows console.
"""
from __future__ import annotations
from sba_resolve.core.services.app_settings import load_camera_luts
def apply_camera_luts_to_timeline(context):
    project = context.project
    if project is None:
        raise RuntimeError("Resolve project is not initialized.")
    timeline = project.GetCurrentTimeline()
    if timeline is None:
        raise RuntimeError("No current timeline.")
    camera_luts = load_camera_luts()
    counts = {
        "applied": 0,
        "already": 0,
        "failed": 0,
        "skipped": 0,
    }
    media_files = {
        m.filename.lower(): m
        for m in context.project_data.get("media_objects", [])
    }
    print("=" * 70)
    print("AUTO CAMERA LUT")
    print("=" * 70)
    print("Timeline:", timeline.GetName())
    for track in range(1, timeline.GetTrackCount("video") + 1):
        items = timeline.GetItemListInTrack("video", track)
        for item in items:
            _apply(item, media_files, camera_luts, counts)
    print()
    print("=" * 70)
    print("Applied :", counts["applied"])
    print("Already :", counts["already"])
    print("Skipped :", counts["skipped"])
    print("Failed  :", counts["failed"])
    print("=" * 70)
    return counts
def detect_camera_from_filename(name):
    name = name.upper()
    if name.startswith(("GH", "GX", "GP")):
        return "GoPro"
    if name.startswith("DJI_"):
        return "DJI"
    if name.startswith(("VID_", "INS_")):
        return "Insta360"
    return None
def _apply(item, media_files, camera_luts, counts):
    mpi = item.GetMediaPoolItem()
    if mpi is None:
        counts["skipped"] += 1
        return
    props = mpi.GetClipProperty()
    clip_name = props.get("Clip Name") or props.get("File Name")
    if not clip_name:
        counts["skipped"] += 1
        return
    media = media_files.get(clip_name.lower())
    manufacturer = None
    if media:
        profile = getattr(media, "camera_profile", None)
        if profile and profile.is_known():
            manufacturer = profile.manufacturer.value
    if manufacturer is None:
        manufacturer = detect_camera_from_filename(clip_name)
    if manufacturer is None:
        print(f"{clip_name} -> Unknown")
        counts["skipped"] += 1
        return
    lut = camera_luts.get(manufacturer)
    if not lut:
        print(f"{clip_name} -> {manufacturer} -> No LUT configured")
        counts["skipped"] += 1
        return
    try:
        current = item.GetLUT(1)
        if current == lut:
            print(f"{clip_name} -> already correct")
            counts["already"] += 1
            return
    except Exception:
        pass
    print(f"{clip_name}")
    print(f"Camera : {manufacturer}")
    print(f"LUT    : {lut}")
    try:
        ok = item.SetLUT(1, lut)
    except Exception as e:
        print(e)
        ok = False
    if ok:
        print("[OK] Applied\n")
        counts["applied"] += 1
    else:
        print("[FAIL] Failed\n")
        counts["failed"] += 1
