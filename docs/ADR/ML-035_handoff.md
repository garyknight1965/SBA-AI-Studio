# Task ML-035 — Corruption Detector: catch missing/truncated moov

Triggered by a real failure: `GX010219.MP4` failed to import into
Resolve and doesn't play anywhere else, yet the ML-030 Corruption
Detector reported it clean (0 corrupted out of 21). This fixes that
real gap.

---

## Files

| File | Exact path | Type |
|---|---|---|
| `corruption_detector.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\corruption_detector.py` | REPLACE existing |
| `test_corruption_detector.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_corruption_detector.py` | **NEW** |

---

## What was wrong, and what changed

ML-030's check only read the first 16 bytes (box type) and confirmed
the file was readable at its reported end. That's not enough to catch
the actual real-world failure mode your handover doc calls out:
**a camera freeze or power loss mid-recording**, which leaves an MP4
with:
- a perfectly valid `ftyp` header
- a plausible file size
- readable bytes end-to-end

...but **no `moov` box at all** - no index for Resolve or any other
player to use. Header-only and end-of-file checks both pass a file
like this; only a real player/decoder (or a structural walk) notices.

**The fix**: `CorruptionDetector` now walks the top-level ISO-BMFF box
structure for `.mp4`/`.mov`/`.braw` files - reading only box headers
(8-16 bytes each), never decoding video/audio payload - and flags:

- **No `moov` box found** - the camera-freeze case, worded exactly as
  that in the report so it's immediately clear what likely happened
- **No `mdat` box found** - no actual media data
- **An impossible box size** (bigger than the remaining file, or a
  truncated box header) - a write that was cut off mid-box

Everything else from ML-030 (zero-byte check, JPEG/PNG/WAV magic
bytes, permission/I-O error handling) is unchanged.

---

## Verification

1. Built 4 synthetic files: a genuinely valid MP4 (ftyp+moov+mdat), a
   moov-missing MP4 (the exact real-world failure), a truncated-box
   MP4, and a garbage-header MP4. Confirmed: valid passes clean,
   all three broken cases are correctly flagged, with the moov-missing
   case specifically reporting the camera-freeze explanation.
2. Wrote `test_corruption_detector.py` to lock this in permanently -
   there was no formal regression test for the Corruption Detector
   before now, which is exactly how this gap went unnoticed.
3. Full suite: **30/30 passed** (29 previous + the new test).

## Test procedure

```powershell
python run_regression.py
```//
Look for `Corruption Detector (ML-035)` under `Scanner` - should PASS.

Then re-run a real scan against the project containing GX010219.MP4:

```powershell
python start.py
```

`GX010219.MP4` should now show up in the Corruption Detector's output
as corrupted (with a "No 'moov' box found" reason), rather than
passing silently only to fail later at Resolve import.

## Expected result

```
Corruption Detector: 21 checked, 1 corrupted
Corrupted files:
  - GX010219.MP4 (No 'moov' box found - recording likely stopped before the index was written (camera freeze or power loss mid-recording))
```

## Rollback

Revert `corruption_detector.py` to the ML-030 version and delete
`test_corruption_detector.py`.

## Known scope limit

This assumes classic (non-fragmented) MP4/MOV structure with top-level
`moov`+`mdat` boxes, which is what GoPro/DJI/Insta360 camera footage
always produces. It would false-positive on a fragmented MP4 (`moof`/
`mdat` pairs, e.g. some screen-recording or livestream export tools) -
not a concern for camera footage, but worth knowing if you ever feed
it something outside that category.
