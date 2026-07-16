# Task ML-034 — Transcript → IntelliScript AI Editor

Takes a raw DaVinci Resolve transcript export and produces an
IntelliScript-ready script: cuts dead air/filler/rambling asides via
a local Ollama model, keeps everything else word-for-word.

---

## Files (all NEW)

| File | Exact path |
|---|---|
| `transcript_segment.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\models\transcript_segment.py` |
| `resolve_transcript_parser.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\resolve_transcript_parser.py` |
| `intelliscript_assembler.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\intelliscript_assembler.py` |
| `intelliscript_editor.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\intelliscript_editor.py` |

No existing files were touched. `intelliscript_editor.py` uses your
existing `OllamaClient` exactly as-is — no changes there either.

---

## How it works, and why the verbatim guarantee is real (not just prompted)

**`ResolveTranscriptParser`** — reads a Resolve transcript export into
ordered segments. Any block with no `Speaker N` line (pure sound
effects like `(Wind Blowing)`) is marked non-speech and never reaches
the AI at all — that's a mechanical filter, not an editorial call.

**`IntelliScriptEditor`** — sends only the speech segments to Ollama,
numbered, and asks for **keep/cut + paragraph-break decisions only**.
The prompt explicitly tells the model it has no ability to supply
replacement text, and the parser only ever reads `index`/`keep`/
`paragraph_break_before` from the response — there's nowhere for
reworded text to even enter the pipeline.

**`IntelliScriptAssembler`** — pure, deterministic code with no AI
involvement. It reproduces every kept word exactly as transcribed,
with exactly two fixed, mechanical exceptions:
1. A kept segment immediately following a cut, if it starts with
   "And"/"But"/"So"/"Then", has that leading word dropped and the
   next word re-capitalised (e.g. "And the eight," → "The eight,").
2. A kept segment immediately preceding a cut (or the last one
   overall) has a trailing comma changed to a period.

Both only ever touch a connector word or a piece of punctuation that
already existed — never a rewrite.

**Fail-safes in `IntelliScriptEditor`:**
- If Ollama's response can't be parsed as JSON, `parse_error=True` is
  returned with the raw response preserved — no broken script is
  produced.
- If the response is valid JSON but missing decisions for some
  segments (a truncated response on a long transcript), those
  segments default to `keep=True` rather than silently vanishing —
  better to leave in something that should've been cut than to lose
  footage the editor never sees again.

---

## Verification

I validated this two ways before handing it back:

1. **Byte-for-byte reconstruction test** — I manually mapped your two
   uploaded samples (`sunday.txt` raw → `I tell you about my positive
   things.txt` edited) into keep/cut/paragraph decisions and fed them
   through `IntelliScriptAssembler` directly. Output matched your
   sample **exactly**, character for character. This proves the
   mechanical layer (parsing, joining, the two punctuation/connector
   fixes) is correct independent of the AI.

2. **End-to-end test with a fake Ollama client** returning those same
   decisions — `IntelliScriptEditor.build_script()` reproduced the
   exact sample script, plus separate tests confirmed the truncated-
   response and garbage-response fail-safes behave as designed.

3. **Full regression suite**: 29/29 passed, nothing else touched.

I could not test against a *real* running Ollama instance from this
sandbox (no network access to a local Ollama server here) — the
prompt/parsing logic is verified, but worth a real run on your machine
to see how your actual local model performs on the editorial judgment
itself (what it chooses to cut).

---

## Test procedure

```powershell
python -c "
from sba_resolve.core.services.intelliscript_editor import IntelliScriptEditor
editor = IntelliScriptEditor()
raw = open('path\to\your\resolve_transcript_export.txt', encoding='utf-8').read()
result = editor.build_script(raw)
print('parse_error:', result['parse_error'])
print('segments:', result['segment_count'], 'kept:', result['kept_count'])
print(result['script'])
"
```

## Expected result

A clean script printed to console (or write `result['script']` to a
`.txt` file) with dead air/filler/rambling cut, paragraphs grouped by
topic, every kept word matching the original transcript exactly.

## Rollback

Delete the 4 new files. Nothing else in the app references them yet.

## Not built yet (deliberately out of scope for this task)

- No GUI wiring (Transcript page / button to run this) — this is the
  backend service layer only.
- No target-length constraint — per your instruction, the AI cuts
  whatever's genuinely dead air/filler/off-topic and lands wherever
  that lands.
- No scene/topic tagging beyond paragraph grouping — you mentioned
  this as a possible later pass, not part of "both" (take-selection +
  filler removal) for now.
