# SBA AI Studio - User Manual

This is a practical, task-based guide to using SBA AI Studio. For
release history see `CHANGELOG.md`; for what's built vs. still
planned see `Roadmap.md`. This document covers how to actually use
what's shipped.

---

## 1. What This App Does

SBA AI Studio takes a folder of raw ride footage (GoPro, DJI, Insta360)
and:

1. Scans and validates the footage, working out ride days, scenes, and
   camera overlap
2. Builds a DaVinci Resolve project - bins organized by day and
   camera, one timeline per ride day, clips placed with real timing
   and gap handling
3. Applies camera-specific color LUTs to graded clips
4. Helps you cut a script from a transcript (IntelliScript)
5. Generates YouTube titles, descriptions, tags, chapters, and a
   thumbnail from the finished edit

Two design principles run through the whole app:

- **Never guess.** If something can't be done reliably (multicam audio
  sync, scene labelling), the app tells you clearly instead of silently
  guessing wrong. You get a placeholder track or an honest "not
  configured" rather than a bad automatic decision.
- **You stay in control.** Nothing destructive happens without a
  visible confirmation, and every AI-generated result (script cuts,
  metadata, thumbnails) is meant to be reviewed and edited by hand
  before it's final.

---

## 2. Requirements

- DaVinci Resolve **Studio** (the scripting API used throughout this
  app is Studio-only, not the free version)
- Python environment with the project's dependencies installed
  (`requirements.txt`)
- ExifTool (path configurable in Settings if not on your system PATH)
- One of:
  - **Ollama** running locally (`ollama serve`, with a model pulled,
    e.g. `ollama pull llama3.2`) - free, runs on your own hardware
  - **Groq** API key (free tier available at console.groq.com) - cloud,
    generally faster than a local model

---

## 3. Starting the App

Activate your virtual environment, then:

```powershell
python start.py
```

This opens the desktop GUI. Scanning and planning run independently of
Resolve - you don't need Resolve open at all until you actually import.

---

## 4. The Basic Workflow

### 4.1 Open a Project

**File > Open Project...** - pick the folder containing your raw
footage for this ride. The workspace tree, media browser, and map all
refresh to reflect the new project. (Opening a new project clears any
loaded transcript/IntelliScript result from the previous one - they
don't carry over.)

### 4.2 Scan Project

**File > Scan Project** - reads every file in the folder, validates it
as real video footage (rejecting images, sidecar files, cache/proxy
files, cloud-trash markers, with the reason shown for each), extracts
metadata via ExifTool, resolves accurate capture timestamps per
camera, detects ride days and scenes, and checks for file corruption.

The status bar shows a summary; the Media Browser and map populate
with what was found. If GPS data is present, a route line is drawn on
the map - a real road-following route if you've configured an
OpenRouteService API key (Settings > Map), otherwise a straight
pin-to-pin approximation.

### 4.3 Import to Resolve

**File > Import to Resolve** - connects to Resolve, creates or opens
the project, syncs Media Pool bins (organized Day > Camera), imports
every valid clip, and (if enabled) builds one timeline per ride day
plus a combined Master timeline nesting them in order.

A results dialog shows success/failure with a "Show Details..."
expander containing the full console log - bin/media counts, ride day
and placement statistics, any skipped/corrupted files, and (if
enabled) the camera LUT application report.

If some clips can't be reliably auto-synced (see Multicam below),
you'll see a separate "Manual Sync Required" report listing exactly
which clips need manual placement in Resolve, and why.

### 4.4 Multicam Footage

Only GoPro HERO13 Black clips auto-place onto the timeline
automatically by default. Every other camera in an overlapping
multicam scene gets an empty, clearly named placeholder track instead
- real-world testing found audio-based sync unreliable across every
camera pairing tried, so the app doesn't guess. Drag those clips onto
their placeholder track and sync them by ear/eye in Resolve as you
normally would.

(Settings has an experimental "Attempt audio sync" toggle if you want
to try it yourself on a cleaner audio setup - off is recommended.)

---

## 5. Camera LUTs

Applies a per-camera-manufacturer color LUT to clips that are already
placed on a timeline, via Resolve's `TimelineItem.SetLUT()`.

### 5.1 Setting Up LUTs

1. Get the correct LUT for each camera's actual color profile - not a
   generic one:
   - **GoPro** (if shooting Protune Flat): GoPro's own "Protune Flat to
     Rec.709" LUT, from GoPro's support site. If you shoot GoPro's
     standard/vivid profile instead, skip a LUT for GoPro entirely.
   - **DJI** (if shooting D-Log): DJI's own "D-Log to Rec.709" LUT for
     your specific drone/gimbal model, from DJI's support site. If
     shooting D-Cinelike, a LUT isn't strictly necessary.
   - **Insta360** (if shooting Log/Flat): Insta360's own Log-to-Rec.709
     LUT from their support site. If shooting Standard color mode, skip
     it.
2. Copy the downloaded `.cube` file into Resolve's LUT folder:
   `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\` -
   a subfolder per brand (e.g. `GoPro\`) keeps things tidy.
3. Restart Resolve (or reopen Project Settings > Color Management >
   Lookup Tables) so it picks up the new file.
4. In **Edit > Settings... > Camera LUTs**, click "Browse..." next to
   each camera and pick the file from inside Resolve's LUT folder -
   this fills in the correct value automatically, including exact
   capitalization. **Don't type the path by hand** - Resolve's LUT
   matching is case-sensitive, and a mismatched case (e.g. `Gopro` vs.
   the real `gopro` folder) will silently fail every clip.

### 5.2 Automatic Application

Check **"Auto-apply after timeline creation"** in Settings > Camera
LUTs to have LUTs applied automatically right after each day's
timeline is created during Import to Resolve. Off by default.

### 5.3 Manual Re-Application

**File > Apply Camera LUTs to Timeline** re-runs just the LUT step at
any time, against whatever project is currently open in Resolve - no
need to re-run the whole import. Use this after manually syncing
placeholder-track clips (see 4.4) that weren't on the timeline yet
when the automatic pass ran.

A results dialog shows Applied / Already Correct / Skipped / Failed
counts, with the full per-clip log available via "Show Details...".

**If a LUT reports Failed:** almost always a mismatch between the
value in Settings and what Resolve's LUT catalog actually has
installed - check capitalization first, then confirm Resolve has
actually refreshed since the file was added.

---

## 6. Transcript -> IntelliScript

1. Export a transcript from your already-cut Resolve timeline (Resolve
   generates these from its transcription feature).
2. **File > Load Transcript && Generate IntelliScript...** - pick the
   exported `.txt` file. The AI reads every segment and decides
   keep/cut and paragraph grouping - it never rewrites, paraphrases, or
   invents wording. Every word that survives is exactly as spoken.
3. Review the result in the Transcript panel. The status bar shows how
   many segments were kept out of the total.
4. **File > Save IntelliScript Script...** to save the resulting script
   to a `.txt` file - this is a deliberate, explicit save, never
   automatic.

The editorial guidance the AI uses (what counts as filler, how to
group paragraphs) is editable in **Settings > IntelliScript Prompt**,
with a Reset to Default button if you want to try changes and back
out.

---

## 7. YouTube Metadata

**File > Generate YouTube Metadata** - produces:

- 5 title options (the best one auto-fills the Title field; the other
  4 sit in "Other title options")
- A structured description: hook opening, natural mention of every
  place visited, editing-credit line worked in naturally, a call to
  action, and hashtags
- 15 SEO tags
- A suggested export filename
- A pinned-comment suggestion
- Thumbnail overlay text suggestion (feeds into the Thumbnail panel
  automatically, see below)
- A chapters section, if a transcript has been loaded AND an
  IntelliScript has already been generated for this project (real
  edited-video timing, not raw footage timing - if either input is
  missing, no chapters section is added rather than showing wrong
  timestamps)

The brand-voice/style guidance (channel tone, description structure) is
editable in **Settings > YouTube Metadata Prompt**, with Reset to
Default available.

Everything generated is meant to be reviewed and edited by hand before
you actually publish - nothing here posts to YouTube automatically.

---

## 8. Thumbnail

In the Thumbnail panel, click **Suggest Frames** to pull a handful of
candidate still frames evenly spread across your footage (a
deterministic pick from real frames - not an AI guess at "the best
one", since that's a judgement call left to you). Click one to preview
it composited with overlay text and your channel logo.

The overlay text pre-fills from YouTube Metadata's suggestion if one
exists, but stays fully editable - typing updates the live preview.
Long text auto-shrinks or wraps across up to 3 lines rather than
running off the frame.

Set your logo image once in **Settings > Thumbnail** (composited into
the bottom-right corner, auto-sized so it can't swamp the frame).

Save the result as a 1280x720 PNG ready for YouTube.

---

## 9. Locations

**File > Group by Location** - groups clips by GPS-derived location
(reverse-geocoded), useful for seeing which stops/places the ride
actually covered. Runs on a background thread since it makes real
network calls.

---

## 10. Settings Reference (Edit > Settings...)

| Section | What it controls |
|---|---|
| **Appearance** | Dark/light theme, applied immediately on OK |
| **DaVinci Resolve** | Timeline creation on/off; experimental multicam audio sync (off recommended); Resolve module path (blank = auto-detect) |
| **Camera LUTs** | Per-camera LUT file (GoPro/DJI/Insta360) and the auto-apply toggle - see Section 5 |
| **Gap Compression** | Off by default; compresses real-time gaps longer than a threshold down to a short fixed gap instead of leaving the full real-world pause on the timeline |
| **AI Provider** | Ollama (local) vs. Groq (cloud) - takes effect on the very next AI call, no restart needed; API key never logged anywhere |
| **IntelliScript Prompt** | Editorial guidance for keep/cut decisions - see Section 6 |
| **YouTube Metadata Prompt** | Brand-voice guidance for generated metadata - see Section 7 |
| **Map** | OpenRouteService API key for real road-following routes (optional - falls back to straight lines with no key) |
| **Tools** | ExifTool path |
| **Thumbnail** | Channel logo image path - see Section 8 |

Settings are only written to `config/settings.json` when you click
**OK** - Cancel leaves the file completely untouched.

---

## 11. Troubleshooting

**"Unable to connect to DaVinci Resolve"** - make sure Resolve is
actually running before triggering an Import to Resolve or a manual
Camera LUT re-application.

**A camera LUT shows "Failed" in the report** - see Section 5.3.
Almost always a case-sensitive mismatch between the configured value
and Resolve's real LUT catalog; re-pick via "Browse..." in Settings
rather than typing the path.

**Some clips are missing from the timeline entirely** - check the
"Manual Sync Required" report from the last import; clips left there
need manual placement in Resolve first (see Section 4.4).

**YouTube metadata has no chapters section** - this is deliberate, not
a bug: chapters only appear once both a transcript is loaded AND an
IntelliScript has been generated for the current project. Generate
both first if you want chapters included.

**A file was rejected during scanning** - the app tells you why for
every rejected file (e.g. "Image file, not video footage"). This is
expected behaviour, not an error - only real video footage should ever
reach Resolve.

**Regression suite, for anyone modifying the app's code:**
```powershell
python run_regression.py --all
```
Run this before every commit - see `README.md`'s Development Workflow
section for the full process.
