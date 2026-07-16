# Task ML-032 — Complete ML-031 Timestamp/Multicam Confidence Wiring

This isn't new work — it completes ML-031, which existed on your machine
as regression tests + a working `ConfidenceEngine`, but the actual model
fields and resolver method those tests expect were never added. This is
why `run_regression.py` was failing on your side even though nothing in
my earlier ML-030 handoff should have touched these files.

---

## Files (all MODIFIED, complete replacement files)

| File | Exact path |
|---|---|
| `timestamp_resolver.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\metadata\timestamp_resolver.py` |
| `metadata_mapper.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\metadata\metadata_mapper.py` |
| `media_file.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\models\media_file.py` |
| `multicam_candidate.py` | `D:\Projects\SBA-AI-Studio\sba_resolve\core\models\multicam_candidate.py` |
| `multicam_confidence_scorer.py` (**NEW**) | `D:\Projects\SBA-AI-Studio\sba_resolve\core\services\multicam_confidence_scorer.py` |

`media_file.py` here is built on top of the ML-030 version I gave you
before (still has `corrupted`/`corruption_reason`) — this doesn't undo
that, it adds two more fields after it.

---

## What was actually missing, and what I added

1. **`TimestampResolver.resolve_with_source()`** (new classmethod,
   `resolve()` untouched) — same resolution order as `resolve()`
   (CreateDate → MediaCreateDate → DateTimeOriginal → DJI filename →
   Insta360 filename → file-modified time), but also returns *which*
   source won, e.g. `("DJI Filename", datetime(...))`.

2. **`MediaFile.timestamp_source` / `timestamp_confidence`** — two new
   fields, appended at the end of the dataclass (keyword-safe, same
   approach as ML-030).

3. **`MetadataMapper.map()`** — now calls `resolve_with_source()` once,
   feeds the source name into `ConfidenceEngine.score()` (which already
   existed and already had the right scores — that part of ML-031 was
   done, just never wired to anything), and populates both new fields.

4. **`MulticamCandidate.ride_day`** — the field the tests construct
   candidates with; added at the end, keyword-safe against the one
   existing construction site in `multicam_detector.py`.

5. **`MulticamConfidenceScorer`** (new service) — scores each candidate
   by its **weakest** contributing clip (not an average), so one
   low-confidence clip can't hide behind a high-confidence one. Also
   provides `status_for()`, mapping a score to `Auto-sync` / `Review` /
   `Manual`:
   - `AUTO_SYNC_THRESHOLD = 0.90`
   - `REVIEW_THRESHOLD = 0.60`

---

## Test procedure

```powershell
python start.py
python run_regression.py
```

I ran this against a fresh clone of your GitHub repo with your two
uploaded test files (`test_timestamp_confidence.py`,
`test_multicam_confidence_scorer.py`) dropped into `regression/tests/`:
**28/28 passed**, including both of those and every previously-passing
test.

## Expected result

```
Timestamp Confidence (ML-031)      PASS
...
Multicam Confidence Scorer (ML-031)PASS
```

## Caveat — please confirm on your machine

Your regression log also showed two failures for **"Ride Summary Scene
Facts (ML-030)"**, both on the same `ride_day` kwarg error this fixes.
That test file isn't in the GitHub repo (must be local-only, alongside
your Chapter Generator / Editing Assistant Generator work), so I
couldn't run it myself to confirm. Please run your full local
`run_regression.py` after applying these files and let me know if
anything's still red — if `ride_day` was the only thing missing, it
should now be clean.

## Rollback

Revert all 4 modified files to their previous versions and delete
`multicam_confidence_scorer.py`. Nothing else depends on the new
service yet.
