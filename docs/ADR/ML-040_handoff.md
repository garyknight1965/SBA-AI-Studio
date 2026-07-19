# Task ML-040 — Locations Panel (GUI wiring for ML-038)

Wires ML-038's `LocationGrouper` into a real GUI panel, following the
exact same pattern as YouTube Metadata and Transcript: dumb widget +
signals, background QThread worker, MainWindow owns orchestration.

---

## Files

| File | Exact path | Type |
|---|---|---|
| `locations_widget.py` | `D:\Projects\SBA-AI-Studio\ui\widgets\locations_widget.py` | **NEW** |
| `location_grouping_worker.py` | `D:\Projects\SBA-AI-Studio\ui\workers\location_grouping_worker.py` | **NEW** |
| `test_locations_ui.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_locations_ui.py` | **NEW** |
| `dock_manager.py` | `D:\Projects\SBA-AI-Studio\ui\layout\dock_manager.py` | REPLACE existing |
| `main_window.py` | `D:\Projects\SBA-AI-Studio\ui\windows\main_window.py` | REPLACE existing |

`main_window.py` is built on top of the last verified GitHub state
(with the Transcript panel and corruption-skip logic already in it) -
only the Locations wiring was added.

---

## What it does

A new **Locations** dock panel:

1. **Group by Location** button - runs `LocationGrouper` on a
   background thread (`LocationGroupingWorker`), same reasoning as
   ML-038's handoff: `ReverseGeocoder` makes real, rate-limited network
   calls, so this must never run on the GUI thread. It's a manual
   trigger, not automatic on scan, for the same reason.
2. Results shown as a simple list: place name + clip count per group,
   `Unknown Location` included like any other group rather than hidden.
3. Menu entry added under File: "Group by Location".

## Verification

New regression test mirrors the Transcript/YouTube UI test pattern:

1. Widget display logic (button states, group list population, status
   text, error display, clear).
2. `LocationGroupingWorker.run()` called directly (no real thread) with
   a fake geocoder injected - both success and failure paths, no real
   network call made.
3. `DockManager` creates the panel and clears it on refresh.

Full suite: **38/38 passed** (37 previous + this one).

## Test procedure

```powershell
python run_regression.py
```

Look for `Locations UI (ML-040)` under `Resolve` - should PASS.

Then manually:

```powershell
python start.py
```

Scan a project with GPS data, then File → Group by Location (or the
button in the Locations dock). Expect a short delay (real network
calls, ~1/second per distinct location) before the list populates.

## Rollback

Revert `dock_manager.py` and `main_window.py` to their previous
versions, delete the 3 new files.
