# Task ML-038 — Location-Based Grouping (Media Organisation)

Builds the "group by location" capability from Core Module 2 (Media
Organisation) in the product handover doc. `ReverseGeocoder` already
existed (used for YouTube metadata's "places" field) but nothing
grouped clips by location - this adds that.

---

## Files (all NEW)

| File | Exact path |
|---|---|
| `location_group.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\models\location_group.py` |
| `location_grouper.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\location_grouper.py` |
| `test_location_grouper.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_location_grouper.py` |

No existing files were touched.

---

## What it does

`LocationGrouper.group(media_files)` reverse-geocodes each clip's GPS
and groups them into `LocationGroup` objects - clips at the same place
(within ReverseGeocoder's existing ~1km cache precision) land together.
Clips with no GPS data, or an unresolvable lookup (offline, rate-
limited, bad response), land in a single `Unknown Location` group
rather than being dropped or crashing anything.

Groups come back sorted alphabetically by place name, with `Unknown
Location` always last - so a list of locations reads real places
first, with the "couldn't identify this" bucket clearly separated at
the end rather than interleaved alphabetically.

---

## Deliberately NOT wired into scan_project() - please read before using

`ReverseGeocoder` makes real network calls, rate-limited to ~1
request/second per distinct location cluster. Every other place this
gets used in the codebase (YouTube metadata generation, via
`RideSummaryBuilder._places_for()`) runs inside a background
`QThread` (`YouTubeMetadataWorker`) specifically so this network
activity never blocks the GUI.

`WorkspaceController.scan_project()`, by contrast, runs synchronously
on the GUI thread when called from `MainWindow.scan_project()`. Wiring
`LocationGrouper` in there directly would freeze the UI for however
long geocoding takes on a multi-stop ride - a real regression in
responsiveness that today's scan (all local, no network) doesn't have.

So this task is the grouping capability itself, ready to be called
from wherever makes sense next - most likely a new background worker
(mirroring `YouTubeMetadataWorker`) if you want it surfaced in the GUI,
or reused directly if you build a CLI/report tool around it. I didn't
guess at which GUI surface you'd want (Statistics panel? A new
"Locations" tree view? Folded into YouTube metadata's places?) since
that's a real design decision, not just wiring.

---

## Verification

New regression test uses a fake geocoder (fixed lookup table, no real
network calls or rate-limit delay) covering:
- Multiple clips at the same place group together
- No-GPS and unresolvable-lookup clips both land in `Unknown Location`
- Alphabetical sort with `Unknown Location` always last

Full suite: **33/33 passed** (32 previous + this one).

## Test procedure

```powershell
python run_regression.py
```

Look for `Location Grouper (ML-038)` under `Planning` - should PASS.

## Rollback

Delete the 3 new files. Nothing else references them yet.

## Suggested next step

If you want this in the GUI, the natural next task is a background
worker + a small panel (or a tab on an existing one) - happy to build
that next once you've decided where it should live.
