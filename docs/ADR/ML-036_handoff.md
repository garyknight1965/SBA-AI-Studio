# Task ML-036 — Skip Corrupted Files Before Resolve Import

Closes the loop ML-035 opened: the Corruption Detector correctly
flags `GX010219.MP4` now, but nothing was stopping it from still being
sent to Resolve's import step anyway, where it failed again with no
useful reason (`[FAIL]`, `Errors: 1`, nothing else).

---

## Files

| File | Exact path | Type |
|---|---|---|
| `main_window.py` | `D:\Projects\SBA-AI-Studio\ui\windows\main_window.py` | REPLACE existing |
| `test_resolve_import_corruption_skip.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_resolve_import_corruption_skip.py` | **NEW** |

---

## What changed

In `import_to_resolve()`, media is now split into `media_list`
(clean) and `corrupted_media` (flagged by ML-035's `.corrupted` on
`MediaFile`) **before** bins, day-grouping, or `project_data` are
built. Only clean files ever reach `ResolveConnector`/`ImportMedia`.

- If **some** files are corrupted: they're skipped, the status bar
  and a message box tell you exactly which files and why (using the
  `corruption_reason` ML-035 already attaches), and the rest of the
  import proceeds normally.
- If **every** scanned file is corrupted: import is stopped before
  ever touching Resolve, with a clear message instead of a confusing
  "0 imported, 0 errors" run.

The filtering itself is a new pure static method,
`MainWindow._split_media_by_corruption()` - no Qt/QMessageBox
involved - specifically so it can be regression-tested directly
without risking a blocked `QMessageBox.exec()` in headless test runs.

Nothing else in `main_window.py` changed.

---

## Verification

- New regression test exercises the split logic directly (mixed
  clean+corrupted, all-clean, all-corrupted) - no real Resolve
  connection or GUI interaction needed.
- Full suite: **31/31 passed** (30 previous + this one).

## Test procedure

```powershell
python run_regression.py
```

Look for `Resolve Import Corruption Skip (ML-036)` under `Resolve` -
should PASS.

Then re-run the real project:

```powershell
python start.py
```

Scan, then Import to Resolve. `GX010219.MP4` should no longer appear
in the Resolve import step at all - you should see a message box
(and status bar text) saying 1 file was skipped, naming it and the
corruption reason, while the other 20 import normally with a clean
"Success" result instead of "Status: FAILED".

## Expected result

Something like:

```
Imported (with skipped files)

Project imported into DaVinci Resolve.

1 corrupted file(s) were skipped and never sent to Resolve:
  - GX010219.MP4 (No 'moov' box found - recording likely stopped before the index was written (camera freeze or power loss mid-recording))
```

## Rollback

Revert `main_window.py` to its previous version and delete
`test_resolve_import_corruption_skip.py`.
