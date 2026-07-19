# Task ML-041 — Fix Weak YouTube Titles/Descriptions

Root cause found: the prompt handed the model `Project name:
12-05-2026 castle` as a fact, then explicitly told it *"do not guess
a country or region from... the project name, or anything else"* -
banning the one piece of real, user-supplied context (that this ride
involved a castle) in the same breath it was given. That contradiction
is very likely why titles/descriptions have felt generic.

That strict rule existed for a real reason - your test suite already
documents a prior incident where the model hallucinated "Normandy
Coast" for a ride with no GPS data. The fix here narrows the rule
instead of removing it: the model can use specific words *you already
wrote* (project name, or new optional notes), but still can't invent
anything beyond them.

---

## Files

| File | Exact path | Type |
|---|---|---|
| `youtube_metadata_generator.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\youtube_metadata_generator.py` | REPLACE existing |
| `youtube_metadata_worker.py` | `D:\Projects\SBA-AI-Studio\ui\workers\youtube_metadata_worker.py` | REPLACE existing |
| `youtube_metadata_widget.py` | `D:\Projects\SBA-AI-Studio\ui\widgets\youtube_metadata_widget.py` | REPLACE existing |
| `main_window.py` | `D:\Projects\SBA-AI-Studio\ui\windows\main_window.py` | REPLACE existing |
| `test_youtube_metadata_generator.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_youtube_metadata_generator.py` | REPLACE existing |
| `test_youtube_metadata_ui.py` | `D:\Projects\SBA-AI-Studio\regression\tests\test_youtube_metadata_ui.py` | REPLACE existing |

`main_window.py` is built on top of the last verified state (Transcript
panel, corruption-skip, Locations panel already in it) - only the
notes-passthrough line was added.

---

## What changed

1. **Project name is now usable.** The prompt explicitly tells the
   model: specific words in the project name (e.g. "castle") are a
   trustworthy fact it CAN use - but not to elaborate beyond what's
   actually said (e.g. don't invent *which* castle).

2. **New optional notes field**, in the YouTube Metadata panel - type
   any real detail (a landmark, an event) before generating. Same
   trust level as the project name: usable, not invented from.

3. **Anti-hallucination guardrail kept, but narrowed** rather than
   removed - country/region/city names still can't be invented from
   nowhere; they now can come from the project name or notes, in
   addition to GPS-derived places.

---

## Verification

- Extended the existing `test_youtube_metadata_generator.py` with two
  new sections: one confirming the old contradiction is gone and the
  project name is explicitly marked usable, one confirming
  `extra_notes` appears in the prompt when given and produces no
  dangling empty section when not.
- Explicitly re-confirmed the anti-hallucination instruction is still
  present in the prompt (guarding against reopening the "Normandy
  Coast" bug your test suite already protects against).
- Updated `test_youtube_metadata_ui.py` for the new field (button
  states, `additional_notes()` read-back, `clear()` resets it).
- Full suite: **38/38 passed**.

## Test procedure

```powershell
python run_regression.py
```

Then manually, with a real project and Ollama running:

```powershell
python start.py
```

Scan a project, optionally type a note in the YouTube Metadata panel's
new field, click Generate. Compare the title/description against a
previous generation for the same project - it should now actually
reference whatever's in the folder name (and any note you added).

## Rollback

Revert all 6 files to their previous versions.
