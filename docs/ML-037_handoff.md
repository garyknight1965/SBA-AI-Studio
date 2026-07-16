# Task ML-037 — Transcript Panel: Wire IntelliScript Editor into the GUI

Wires ML-034's backend (`IntelliScriptEditor`) into a real Transcript
dock panel, following the exact same pattern as the existing YouTube
Metadata panel (dumb widget + signals, background QThread worker,
MainWindow owns file dialogs and orchestration).

---

## Files

| File | Exact path | Type |
|---|---|---|
| `transcript_widget.py` | `D:\Projects\SBA-AI-Studio\ui\widgets\transcript_widget.py` | **NEW** |
| `intelliscript_worker.py` | `D:\Projects\SBA-AI-Studio\ui\workers\intelliscript_worker.py` | **NEW** |
| `test_transcript_ui.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_transcript_ui.py` | **NEW** |
| `dock_manager.py` | `D:\Projects\SBA-AI-Studio\ui\layout\dock_manager.py` | REPLACE existing |
| `main_window.py` | `D:\Projects\SBA-AI-Studio\ui\windows\main_window.py` | REPLACE existing |

`main_window.py` here is built on top of the ML-036 version (corrupted-
file skip on Resolve import) - that logic is untouched, only the new
Transcript wiring was added.

---

## What it does

A new **Transcript** dock panel, alongside Metadata/Statistics/Timeline/
YouTube Metadata:

1. **Load Transcript...** - opens a Resolve transcript export (.txt).
   Reading happens in `MainWindow.load_transcript()`, not the worker,
   so a bad path/encoding error shows up immediately.
2. **Generate IntelliScript** - runs `IntelliScriptEditor` on a
   background thread (`IntelliScriptWorker`), so a slow/unreachable
   Ollama doesn't freeze the GUI. Never touches Resolve.
3. Result shown in an editable text area - review before use. On a
   parse error, the model's raw response is shown instead and **Save
   is disabled**, since a raw unparsed response isn't a usable script.
4. **Save Script...** - saves whatever is currently in the text area
   (including any manual edits made after generation), not a cached
   copy from generation time.

Menu entries added under File: "Load Transcript...", "Generate
IntelliScript", "Save IntelliScript Script...".

---

## Verification

New regression test (`test_transcript_ui.py`) mirrors the existing
YouTube Metadata UI test exactly:

1. Widget display logic - button enable/disable states through the
   whole load → generate → result/parse-error/error → clear cycle.
2. `IntelliScriptWorker.run()` called directly (no real thread, no
   real Ollama) - both the success path and an `OllamaError` failure
   path, confirming the right signal fires with the right payload.
3. `DockManager` creates the panel and clears it on refresh, matching
   the YouTube panel's behaviour on project switch.

Full suite: **32/32 passed** (31 previous + this one).

## Test procedure

```powershell
python run_regression.py
```

Look for `Transcript UI (ML-037)` under `Resolve` - should PASS.

Then manually, with a real Ollama running:

```powershell
python start.py
```

File → Load Transcript... → pick a Resolve transcript export →
Generate IntelliScript → review the result in the Transcript dock →
Save IntelliScript Script...

## Expected result

The generated script appears in the Transcript dock, status bar shows
something like "IntelliScript generated - kept 59 of 77 segments.",
and Save writes exactly what's shown (including any edits you made) to
the file you choose.

## Rollback

Revert `dock_manager.py` and `main_window.py` to their ML-036 versions,
and delete the 3 new files. Nothing else depends on them yet.
