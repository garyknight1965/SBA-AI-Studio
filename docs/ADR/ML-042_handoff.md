# Task ML-042 — Remove Unused Timeline Panel

Removes the Timeline dock panel: a read-only Day/Scene text preview
that had no interactive use and duplicated information already
visible in the Workspace Tree / Media Browser.

---

## Files

| File | Exact path | Type |
|---|---|---|
| `dock_manager.py` | `D:\Projects\SBA-AI-Studio\ui\layout\dock_manager.py` | REPLACE existing |
| `main_window.py` | `D:\Projects\SBA-AI-Studio\ui\windows\main_window.py` | REPLACE existing |
| `test_ui_widgets.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_ui_widgets.py` | REPLACE existing |

**DELETE this file** (no longer used anywhere):
`D:\Projects\SBA-AI-Studio\ui\widgets\timeline_widget.py`

---

## What changed

- `DockManager` no longer creates, docks, or refreshes a Timeline
  panel. The `_refresh_timeline_preview()` method and its
  `TimelinePlanningService` import are removed entirely (that service
  itself is untouched - still used elsewhere for real planning work).
- `main_window.py`'s central widget placeholder text ("Timeline
  Preview") was also stale and referenced the removed concept -
  cleared to an empty label rather than left misleading.
- `test_ui_widgets.py` had its Timeline-panel assertions removed, and
  its module docstring/description updated to match what the test
  actually verifies now (Statistics duration fix + selection wiring
  only).

I checked every reference across the codebase before removing
anything - only these 3 files touched the Timeline panel at all, so
this is a clean, fully self-contained removal.

---

## Verification

Full suite: **38/38 passed**, same count as before (one test's scope
shrank, none were deleted).

## Test procedure

```powershell
python run_regression.py
```

Then:

```powershell
python start.py
```

The "Timeline" dock should no longer appear at all. Everything else
(Workspace, Media Browser, Metadata, Statistics, YouTube Metadata,
Transcript, Locations) should look and behave exactly as before.

## Rollback

Revert `dock_manager.py`, `main_window.py`, and `test_ui_widgets.py` to
their previous versions, and restore `timeline_widget.py` (available in
git history if you need it back).
