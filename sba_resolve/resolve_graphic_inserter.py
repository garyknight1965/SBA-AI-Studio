"""
resolve_graphic_inserter.py

Shared insertion primitive for all AI-driven graphics features:
    - ML-044 Title Cards
    - ML-045 Channel Bug Overlay
    - ML-046 Lower-Third Labels
    - ML-055 Chapter Title Cards

This module owns every direct call into the DaVinciResolveScript API for
graphics work. ML-044/045/046/055 each build their own suggestion/approval
logic on top of this, but none of them talk to Resolve directly -- they all
go through GraphicInserter so there is exactly one place that knows how to
add a track, clone a Fusion Title template, set its text, and place it on
the timeline.

Design constraints this module follows (per Gary's rules):
    - Additive only. Nothing here modifies an existing clip's trim points,
      an existing track's other clips, or anything already on the timeline.
      Every operation this module performs is "add a new tagged clip."
    - Rollback = delete. Every clip this module creates is renamed with a
      feature-specific prefix (see graphics_config.py). Deleting all clips
      with a given prefix fully reverts that feature's work and nothing
      else. There is no other state to restore.
    - No silent failures. If Resolve isn't running, no project is open, or
      the template can't be found, this raises a clear exception rather
      than silently no-op'ing -- Gary's task handoff test procedures check
      for named clips appearing, so a silent failure would be invisible
      until much later.

Requires the DaVinciResolveScript module to be importable, which means
Resolve must be running and the environment variables
RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB must be set as per Blackmagic's
standard scripting setup. See:
https://documents.blackmagicdesign.com/UserManuals/DaVinciResolveScriptingGuide.pdf

Three distinct insertion paths:

    - MEDIA ASSET (channel bug logo, intro clip): an image or video file
      on disk. CONFIRMED via testing: Power Bins are NOT reachable
      through Resolve's scripting API at all -- GetRootFolder() only
      walks the current project's own Media Pool tree. Both the logo and
      the intro clip are therefore looked up by media_pool_name first
      (in case they're already imported into the current project) and
      imported from image_path on disk otherwise. Placed as-is, no text,
      no per-item styling beyond scale/position/opacity. The intro clip
      (ML-050, Phase 1) uses this same path with use_full_duration=True
      and is placed as an overlay on its own track at time 0 -- it does
      NOT shift/ripple the existing timeline. True prepend (shifting
      everything back) is a deliberately deferred future phase, since
      that touches existing timeline state and needs the
      duplicate-timeline safety net per the rollback standard, not
      simple tag-and-delete.

    - NATIVE TEXT (title cards, lower-thirds, built live): no template
      exists to clone, so these are built from Resolve's built-in Text+
      generator and styled in code (font, color, background box) to
      match the channel branding, per-request text set directly on the
      generator. Requires the manual prepare_text_track() + click +
      insert() two-step process -- see _insert_native_text.

    - TEMPLATED TEXT (ML-055 chapter title cards): a saved Fusion .comp
      template, built once by hand in Resolve's Fusion editor and
      exported via ExportFusionComp(). Placed via ImportFusionComp()
      onto an item anchored with AppendToTimeline -- CONFIRMED via
      testing (tools/test_graphic_inserter.py, Candidate B, 2026-07-20
      on Gary's real Resolve setup) that this is genuinely non-rippling
      and needs NO manual track click, unlike the native text path
      above. This is the preferred mechanism for any future dynamic-text
      feature that can tolerate a pre-built template rather than
      building the Text+ node graph live.

CAVEAT (flagged deliberately, not glossed over -- applies to the NATIVE
TEXT path only, NOT the TEMPLATED TEXT path): Resolve's scripting API has
real limitations around targeting an arbitrary, specific track when
inserting a generator via InsertGeneratorIntoTimeline() /
InsertFusionCompositionIntoTimeline() -- confirmed via testing that these
insert relative to the currently active/selected track in the UI, not a
track index chosen purely by script, with no scriptable override
(confirmed again independently via the samuelgursky/davinci-resolve-mcp
project's source, which wraps these same calls with no workaround either).
This is why the TEMPLATED TEXT path (AppendToTimeline + ImportFusionComp)
was built for ML-055 -- it sidesteps this limitation structurally instead
of working around it.
"""

from dataclasses import dataclass
from typing import Optional
import os

from sba_resolve.graphics_config import GraphicsSettings, DEFAULT_SETTINGS


class ResolveConnectionError(RuntimeError):
    """Raised when Resolve, a project, or a timeline can't be reached."""


class AssetNotFoundError(RuntimeError):
    """Raised when an image asset file can't be found on disk, or a
    Media Pool item can't be located/imported."""


class GraphicPlacementError(RuntimeError):
    """Raised when a clip could not be placed on the timeline."""


@dataclass
class GraphicRequest:
    """One approved graphic to insert.

    Exactly one of (image_path and/or media_pool_name), text (native,
    built live), or text+template_path (templated, ML-055) should be set:
        - media_pool_name / image_path: an asset that already exists in
          Resolve (e.g. the logo or "Intro 2026" in Gary's Power Bin) or
          on disk. media_pool_name is checked first; image_path is only
          used as a fallback import if no matching Media Pool item is
          found. Works for images and video clips alike -- both are just
          media pool items to AppendToTimeline.
        - text (with template_path left None): text to display via
          Resolve's native Text+ generator, styled per graphics_config's
          TITLE_TEXT_* constants. Used for title cards and lower-thirds,
          where there's no saved template to clone. Needs the manual
          prepare_text_track() + click step -- see insert().
        - text + template_path: ML-055 chapter title cards. text gets
          written into a saved Fusion .comp template's TextPlus tool.
          No manual click needed -- see _insert_templated_text.

    start_seconds: position on the *current edited timeline*, in seconds
        from timeline start. Callers are responsible for making sure this
        timecode is already correct for the edited timeline (this module
        does no timecode translation of its own).
    duration_seconds: how long the clip stays on screen. Ignored if
        use_full_duration is True.
    use_full_duration: if True (typical for a full intro clip), use the
        asset's own native length instead of duration_seconds.
    track_name: which dedicated AI track this belongs on (created if it
        doesn't exist).
    clip_name_prefix: tag prefix applied to the resulting timeline item,
        used for later identification/rollback.
    scale: relative scale to apply (1.0 = as imported/generated).
    position: named position preset, interpreted by _apply_transform().
    opacity: 0.0-1.0.
    template_path: path to a saved Fusion .comp file (ML-055). When set,
        text must also be set, and media_pool_name/image_path must NOT
        be set -- see _insert_templated_text.
    """
    start_seconds: float
    track_name: str
    clip_name_prefix: str
    duration_seconds: Optional[float] = None
    use_full_duration: bool = False
    media_pool_name: Optional[str] = None
    image_path: Optional[str] = None
    text: Optional[str] = None
    scale: float = 1.0
    position: str = "default"
    opacity: float = 1.0
    template_path: Optional[str] = None

    def __post_init__(self):
        has_asset = self.media_pool_name is not None or self.image_path is not None
        has_text = self.text is not None
        if has_asset == has_text:
            raise ValueError(
                "GraphicRequest needs exactly one of (media_pool_name/"
                "image_path) or text set, got media_pool_name="
                f"{self.media_pool_name!r} image_path={self.image_path!r} "
                f"text={self.text!r}"
            )
        if self.template_path is not None and self.text is None:
            raise ValueError(
                "template_path requires text to be set too (the chapter "
                "label to write into the template)."
            )
        if self.template_path is not None and has_asset:
            raise ValueError(
                "template_path is for templated text requests -- it "
                "can't be combined with media_pool_name/image_path."
            )
        if not has_asset and not self.use_full_duration and self.duration_seconds is None:
            raise ValueError(
                "Text requests need duration_seconds set (use_full_duration "
                "only applies to real media assets)."
            )
        if has_asset and not self.use_full_duration and self.duration_seconds is None:
            raise ValueError(
                "Asset requests need either duration_seconds or "
                "use_full_duration=True."
            )


class GraphicInserter:
    def __init__(self, settings: GraphicsSettings = DEFAULT_SETTINGS):
        self.settings = settings
        self._resolve = None
        self._project = None
        self._timeline = None
        self._media_pool = None
        self._fps = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connects to the running Resolve instance and the currently
        open project/timeline. Must be called before any insert.

        Raises ResolveConnectionError if Resolve isn't running, no
        project is open, or no timeline is current.
        """
        try:
            import DaVinciResolveScript as dvr_script
        except ImportError as exc:
            raise ResolveConnectionError(
                "Could not import DaVinciResolveScript. Confirm Resolve is "
                "running and RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB "
                "environment variables are set."
            ) from exc

        resolve = dvr_script.scriptapp("Resolve")
        if resolve is None:
            raise ResolveConnectionError(
                "Resolve returned no application object. Is Resolve running?"
            )

        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if project is None:
            raise ResolveConnectionError(
                "No project is currently open in Resolve."
            )

        timeline = project.GetCurrentTimeline()
        if timeline is None:
            raise ResolveConnectionError(
                "No timeline is currently open/active in the project."
            )

        media_pool = project.GetMediaPool()
        if media_pool is None:
            raise ResolveConnectionError("Could not access the Media Pool.")

        self._resolve = resolve
        self._project = project
        self._timeline = timeline
        self._media_pool = media_pool
        self._fps = float(timeline.GetSetting("timelineFrameRate"))

    def _require_connection(self) -> None:
        if self._timeline is None:
            raise ResolveConnectionError(
                "Not connected. Call connect() before inserting graphics."
            )

    # ------------------------------------------------------------------
    # Media asset lookup (channel bug logo, intro clip, or any other
    # already-existing Power Bin asset)
    # ------------------------------------------------------------------

    def _resolve_asset(self, media_pool_name: Optional[str], image_path: Optional[str]):
        """Returns a Media Pool item for this request's asset.

        Lookup order:
            1. If media_pool_name is given, search the *current
               project's* Media Pool for a clip with that exact name
               (CONFIRMED: this does not include Power Bins -- testing
               showed GetRootFolder() only walks the current project's
               own bin tree, never the separate Power Bin storage).
            2. If not found (or no media_pool_name given at all) and
               image_path is given, import that file from disk and, if a
               media_pool_name was specified, rename the imported clip to
               match so future lookups in *this* project find it without
               re-importing.

        Both the channel bug logo and the intro clip ("Intro 2026") use
        this same disk-fallback path, since Power Bin assets can't be
        reached directly by script. ML-055's templated text path also
        reuses this for its anchor placeholder (the same logo image).

        Raises AssetNotFoundError if nothing can be found or imported.
        """
        self._require_connection()

        if media_pool_name is not None:
            root_folder = self._media_pool.GetRootFolder()
            existing = self._search_folder_for_clip(root_folder, media_pool_name)
            if existing is not None:
                return existing

        if image_path is None:
            raise AssetNotFoundError(
                f"Could not find a Media Pool item named "
                f"'{media_pool_name}' and no image_path fallback was "
                f"given to import from disk."
            )

        if not os.path.isfile(image_path):
            raise AssetNotFoundError(
                f"'{media_pool_name}' was not found in the Media Pool, "
                f"and the fallback file does not exist on disk either: "
                f"'{image_path}'."
            )

        imported = self._media_pool.ImportMedia([image_path])
        if not imported:
            raise AssetNotFoundError(
                f"Resolve's ImportMedia failed for '{image_path}'."
            )

        clip = imported[0]
        if media_pool_name is not None:
            clip.SetClipProperty("Clip Name", media_pool_name)
        return clip

    def _search_folder_for_clip(self, folder, name: str):
        for clip in folder.GetClipList():
            if clip.GetName() == name:
                return clip
        for sub_folder in folder.GetSubFolderList():
            found = self._search_folder_for_clip(sub_folder, name)
            if found is not None:
                return found
        return None

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def _ensure_track(self, track_name: str) -> int:
        """Returns the 1-based video track index matching track_name,
        creating a new track with that name if none exists.

        Safe for AppendToTimeline-based inserts -- both real media
        assets (images/video like the logo and intro) and ML-055's
        templated text path, since both go through AppendToTimeline,
        which is genuine overwrite-style placement. Multiple items can
        safely share one track under this mechanism. Do NOT use this
        for the NATIVE text/Fusion path -- see prepare_text_track.
        """
        self._require_connection()

        track_count = self._timeline.GetTrackCount("video")
        for i in range(1, track_count + 1):
            if self._timeline.GetTrackName("video", i) == track_name:
                return i

        if not self._timeline.AddTrack("video"):
            raise GraphicPlacementError(
                f"Resolve refused to add a new video track for '{track_name}'."
            )
        new_index = self._timeline.GetTrackCount("video")
        if not self._timeline.SetTrackName("video", new_index, track_name):
            raise GraphicPlacementError(
                f"Added a track but could not rename it to '{track_name}'."
            )
        return new_index

    def prepare_text_track(self, base_track_name: str, label: str) -> str:
        """STEP 1 OF 2 for a NATIVE text/Fusion graphic (NOT needed for
        ML-055's templated path -- see _insert_templated_text, which
        uses _ensure_track instead). Creates a brand-new, uniquely-named,
        empty video track and returns its name.

        The caller MUST show this name to the user and have them
        manually click that track in the Resolve UI before calling
        insert() with the matching text request (STEP 2). This is a
        real, unavoidable two-step process -- confirmed via testing
        that InsertFusionCompositionIntoTimeline() only ever lands on
        whatever track is currently active in the UI, with no
        scriptable way to target a track directly. Skipping the manual
        click step silently places the clip on whatever track happened
        to be active already (e.g. a real footage track).

        A dedicated new track (rather than reusing one) also guarantees
        the ripple-insert this call type performs has nothing else on
        that track to disturb.
        """
        self._require_connection()

        safe_label = "".join(ch if ch.isalnum() else "_" for ch in label)[:40]
        candidate = f"{base_track_name} - {safe_label}"

        existing_names = {
            self._timeline.GetTrackName("video", i)
            for i in range(1, self._timeline.GetTrackCount("video") + 1)
        }
        final_name = candidate
        suffix = 2
        while final_name in existing_names:
            final_name = f"{candidate} ({suffix})"
            suffix += 1

        if not self._timeline.AddTrack("video"):
            raise GraphicPlacementError(
                f"Resolve refused to add a new video track for '{final_name}'."
            )
        new_index = self._timeline.GetTrackCount("video")
        if not self._timeline.SetTrackName("video", new_index, final_name):
            raise GraphicPlacementError(
                f"Added a track but could not rename it to '{final_name}'."
            )
        return final_name

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------

    def _seconds_to_frames(self, seconds: float) -> int:
        return int(round(seconds * self._fps))

    def insert(self, request: GraphicRequest) -> str:
        """Inserts one approved graphic onto the timeline.

        Returns the final clip name actually applied (prefix + label),
        so callers can log/display what was created.

        Three dispatch paths:
            1. request.template_path set (ML-055): the confirmed-safe
               templated mechanism -- AppendToTimeline anchor +
               ImportFusionComp. No manual click needed.
            2. request.media_pool_name / image_path set: a real media
               asset (logo, intro clip), placed via AppendToTimeline.
               No manual click needed.
            3. request.text set alone (no template_path): the NATIVE
               text/Fusion path. InsertFusionCompositionIntoTimeline()
               only ever lands on whatever track is currently
               active/selected in the Resolve UI -- there is no
               scriptable way to change that. Call prepare_text_track()
               FIRST, click the track it creates in the Resolve UI,
               THEN call insert() -- calling insert() directly without
               that manual step will silently place the clip on
               whatever track was already active (e.g. your real
               Video 1), exactly as happened in testing.

        Raises AssetNotFoundError / GraphicPlacementError on failure.
        Never partially applies -- if any step fails, nothing is left
        placed for this request.
        """
        self._require_connection()

        if request.template_path is not None:
            # ML-055: confirmed-safe templated path (Candidate B,
            # CONFIRMED 2026-07-20) -- genuinely additive/overwrite via
            # AppendToTimeline, safe to share one track, no manual click.
            track_index = self._ensure_track(request.track_name)
            timeline_item = self._insert_templated_text(request, track_index)
        elif request.media_pool_name is not None or request.image_path is not None:
            # Safe to share one track -- AppendToTimeline is genuinely
            # additive/overwrite-style, confirmed via testing.
            track_index = self._ensure_track(request.track_name)
            timeline_item = self._insert_asset(request, track_index)
        else:
            # Text/Fusion inserts ripple onto whatever track is active
            # in the UI -- track creation must happen separately, before
            # this call, via prepare_text_track(), with the user
            # manually clicking that track in between. There is no
            # scriptable track_index for this call type since Resolve
            # ignores it -- placement depends entirely on the UI's
            # active track at the moment this runs.
            track_index = None
            timeline_item = self._insert_native_text(request, track_index=None)

        clip_label = self._build_clip_name(request)
        timeline_item.SetName(clip_label)

        print(
            f"DEBUG: placed '{clip_label}' -- requested track_index="
            f"{track_index if track_index is not None else 'n/a (UI-active track)'}, "
            f"actual start={timeline_item.GetStart()}, "
            f"end={timeline_item.GetEnd()}, duration="
            f"{timeline_item.GetDuration() if hasattr(timeline_item, 'GetDuration') else 'n/a'}"
        )

        self._apply_transform(
            timeline_item,
            scale=request.scale,
            position=request.position,
            opacity=request.opacity,
        )

        return clip_label

    def _insert_asset(self, request: GraphicRequest, track_index: int):
        """Places an existing Media Pool / Power Bin asset (image or
        video -- e.g. the channel bug logo or the "Intro 2026" clip) at
        the requested timecode/track. Imports from disk as a fallback
        only if no Media Pool match is found (see _resolve_asset).

        If request.use_full_duration is True, uses the asset's own
        native length instead of request.duration_seconds -- this is
        the normal case for a full intro clip, where trimming to an
        arbitrary duration wouldn't make sense.
        """
        media_item = self._resolve_asset(request.media_pool_name, request.image_path)

        start_frame = self._seconds_to_frames(request.start_seconds)

        if request.use_full_duration:
            native_frames = media_item.GetClipProperty("Frames")
            print(f"DEBUG: GetClipProperty('Frames') returned {native_frames!r} (type {type(native_frames).__name__})")
            if not native_frames:
                raise GraphicPlacementError(
                    f"Could not read native frame count for "
                    f"'{request.media_pool_name or request.image_path}' "
                    f"to apply use_full_duration."
                )
            duration_frames = int(native_frames)
            print(f"DEBUG: computed duration_frames={duration_frames}, start_frame={start_frame}")
        else:
            duration_frames = self._seconds_to_frames(request.duration_seconds)

        clip_info = {
            "mediaPoolItem": media_item,
            "startFrame": 0,
            "endFrame": duration_frames,
            "trackIndex": track_index,
            "recordFrame": start_frame,
        }

        appended = self._media_pool.AppendToTimeline([clip_info])
        if not appended:
            asset_id = request.media_pool_name or request.image_path
            raise GraphicPlacementError(
                f"AppendToTimeline failed for asset '{asset_id}' "
                f"at {request.start_seconds}s on track '{request.track_name}'."
            )
        return appended[0]

    def _insert_templated_text(self, request: GraphicRequest, track_index: int):
        """ML-055. Places request.text using the confirmed-safe
        templated mechanism (Candidate B, CONFIRMED 2026-07-20 on
        Gary's real Resolve setup -- see
        tools/test_chapter_title_bootstrap.py): places the channel bug
        logo image as an anchor via AppendToTimeline (non-rippling,
        scriptable track/frame, no manual click needed), then attaches
        request.template_path (a saved Fusion .comp built once by hand)
        onto that placed item via ImportFusionComp(), then writes
        request.text into the template's TextPlus tool.

        Unlike _insert_native_text, this is genuinely safe to share one
        track across many calls -- there is no ripple-insert involved
        at all, since the anchor placement goes through AppendToTimeline
        exactly like a real media asset (logo/intro).
        """
        from sba_resolve.graphics_config import (
            CHANNEL_BUG_MEDIA_POOL_NAME,
            CHANNEL_BUG_IMAGE_PATH,
        )

        anchor_item = self._resolve_asset(CHANNEL_BUG_MEDIA_POOL_NAME, CHANNEL_BUG_IMAGE_PATH)

        start_frame = self._seconds_to_frames(request.start_seconds)
        duration_frames = self._seconds_to_frames(request.duration_seconds)

        clip_info = {
            "mediaPoolItem": anchor_item,
            "startFrame": 0,
            "endFrame": duration_frames,
            "trackIndex": track_index,
            "recordFrame": start_frame,
        }
        appended = self._media_pool.AppendToTimeline([clip_info])
        if not appended:
            raise GraphicPlacementError(
                f"AppendToTimeline failed placing the anchor for "
                f"templated text '{request.text}' at "
                f"{request.start_seconds}s on track '{request.track_name}'."
            )
        timeline_item = appended[0]

        comp = timeline_item.ImportFusionComp(request.template_path)
        if comp is None:
            raise GraphicPlacementError(
                f"ImportFusionComp('{request.template_path}') returned "
                f"nothing -- confirm the template file exists and is a "
                f"valid exported Fusion composition."
            )

        text_tool = self._find_tool_by_id(comp, "TextPlus")
        if text_tool is None:
            raise GraphicPlacementError(
                f"Could not find a TextPlus tool in the imported "
                f"template '{request.template_path}' -- confirm it was "
                f"built with a Text+ node, not a plain Text generator."
            )
        text_tool.SetInput("StyledText", request.text, 0)

        return timeline_item

    def _find_tool_by_id(self, comp, tool_id: str):
        tools = comp.GetToolList(False)
        for tool_name in tools:
            tool = tools[tool_name]
            if tool.ID == tool_id:
                return tool
        return None

    def _insert_native_text(self, request: GraphicRequest, track_index: Optional[int] = None):
        """Inserts a blank Fusion composition at the requested timecode,
        then builds a Text+ node graph inside it and connects it to
        MediaOut1 -- this is the confirmed-working sequence for
        scripted Fusion titles. (Text+ is a Fusion tool, not a simple
        generator: InsertGeneratorIntoTimeline("Text+") does not work --
        that call only supports Resolve's basic non-Fusion generators.
        This was wrong in an earlier version of this method and is why
        it failed during testing.)

        CONFIRMED (via testing, not just documented): track_index is
        NOT used here and can't be -- InsertFusionCompositionIntoTimeline()
        always places the clip on whatever track is currently
        active/selected in the Resolve UI, with no scriptable override.
        Callers MUST call prepare_text_track() first and have the user
        manually click that track in Resolve before calling insert()
        for a text request -- otherwise this silently lands on whatever
        track was already active (confirmed: landed on the real main
        Video 1 track when this step was skipped).
        """
        timecode_str = self._seconds_to_timecode(request.start_seconds)
        if not self._timeline.SetCurrentTimecode(timecode_str):
            raise GraphicPlacementError(
                f"Could not move playhead to {timecode_str} before "
                f"inserting the Fusion composition."
            )

        timeline_item = self._timeline.InsertFusionCompositionIntoTimeline()
        if timeline_item is None:
            raise GraphicPlacementError(
                "InsertFusionCompositionIntoTimeline() returned nothing. "
                "Confirm the current track/timeline accepts a Fusion "
                "composition at this position."
            )

        self._try_set_duration(timeline_item, request.duration_seconds)

        self._build_and_style_text_comp(timeline_item, request.text)
        return timeline_item

    def _try_set_duration(self, timeline_item, duration_seconds: float) -> None:
        """Attempts to resize the just-inserted clip to duration_seconds.

        UNVERIFIED: TimelineItem.SetEnd() is not confirmed as a real API
        method (a first test run raised 'NoneType object is not
        callable', meaning it doesn't exist as callable on this object).
        This tries a couple of plausible approaches and warns rather than
        crashing if none work -- if the clip ends up at Resolve's
        default generator duration instead of the requested length, that
        is expected until this is resolved properly. Report the actual
        on-screen duration back so this can be fixed with a confirmed
        API call rather than another guess.
        """
        duration_frames = self._seconds_to_frames(duration_seconds)
        new_end = timeline_item.GetStart() + duration_frames

        for attempt_name, attempt in (
            ("SetEnd", lambda: timeline_item.SetEnd(new_end)),
            ("SetProperty Duration", lambda: timeline_item.SetProperty("Duration", duration_frames)),
        ):
            try:
                result = attempt()
                if result:
                    return
            except Exception:
                continue

        print(
            f"WARNING: could not resize the inserted clip to "
            f"{duration_seconds}s -- no known API call succeeded. It "
            f"will likely be at Resolve's default generator duration "
            f"instead. Report the actual on-screen duration back."
        )

    def _build_and_style_text_comp(self, timeline_item, text: str) -> None:
        """Builds a single Text+ tool inside the Fusion composition just
        inserted and connects it directly to MediaOut1 -- confirmed
        working sequence, matching the simplest known-good reference
        script. No background box: Gary chose plain white text only,
        after testing showed the Background+Merge approach produced a
        full-frame tint rather than a bounded box (Fusion's Background
        tool fills the whole frame by default; constraining it to a
        text-sized box would need more work than the plain-text look is
        worth).

        CONFIRMED input IDs (from Gary's actual on-screen results, not
        just documentation): StyledText, Font (family) + Style (weight,
        separate inputs -- setting only one produced a visible "Font Not
        Found" error), Size, Red1/Green1/Blue1. All SetInput calls need
        a third argument (0) for a static, non-animated value.
        """
        from sba_resolve.graphics_config import (
            TITLE_TEXT_FONT,
            TITLE_TEXT_STYLE,
            TITLE_TEXT_COLOR,
            TITLE_TEXT_SIZE,
        )

        comp = timeline_item.AddFusionComp()
        if comp is None:
            raise GraphicPlacementError(
                "AddFusionComp() returned nothing on the inserted clip; "
                "cannot build the text node graph."
            )

        text_tool = comp.AddTool("TextPlus")
        if text_tool is None:
            raise GraphicPlacementError(
                "AddTool('TextPlus') returned nothing -- could not "
                "create the text tool."
            )

        media_out_tool = comp.FindTool("MediaOut1")
        if media_out_tool is None:
            raise GraphicPlacementError(
                "Could not find MediaOut1 in the new Fusion composition "
                "-- expected on every freshly inserted Fusion clip."
            )
        media_out_tool.ConnectInput("Input", text_tool)

        # Confirmed-correct calls, verified against Gary's actual
        # on-screen result.
        text_tool.SetInput("StyledText", text, 0)
        text_tool.SetInput("Font", TITLE_TEXT_FONT, 0)
        text_tool.SetInput("Style", TITLE_TEXT_STYLE, 0)
        text_tool.SetInput("Size", TITLE_TEXT_SIZE, 0)
        r, g, b, a = TITLE_TEXT_COLOR
        text_tool.SetInput("Red1", r, 0)
        text_tool.SetInput("Green1", g, 0)
        text_tool.SetInput("Blue1", b, 0)

    def _seconds_to_timecode(self, seconds: float) -> str:
        total_frames = self._seconds_to_frames(seconds)
        fps = int(round(self._fps))
        frames = total_frames % fps
        total_seconds = total_frames // fps
        secs = total_seconds % 60
        total_minutes = total_seconds // 60
        mins = total_minutes % 60
        hours = total_minutes // 60
        return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"

    def _build_clip_name(self, request: GraphicRequest) -> str:
        """Builds the final clip name, always as clip_name_prefix +
        a sanitized label -- this guarantees the name actually starts
        with clip_name_prefix (including its trailing underscore),
        which is what remove_by_prefix() relies on for rollback.

        BUG FIX: an earlier version returned bare
        clip_name_prefix.rstrip("_") for non-text (asset) requests --
        e.g. both the logo and intro smoke tests produced the exact
        same name "AI_SmokeTest" (no distinguishing label, and missing
        the trailing underscore), which meant rollback's startswith()
        check against "AI_SmokeTest_" never matched either of them.
        Every re-run silently stacked duplicate, indistinguishable
        clips instead of being cleaned up. Report back immediately if
        rollback still doesn't remove everything after this fix.
        """
        if request.text:
            raw_label = request.text
        else:
            raw_label = request.media_pool_name or os.path.basename(
                request.image_path or "asset"
            )
        safe_label = "".join(
            ch if ch.isalnum() else "_" for ch in raw_label
        )[:40]
        return f"{request.clip_name_prefix}{safe_label}"

    def _apply_transform(
        self, timeline_item, scale: float, position: str, opacity: float
    ) -> None:
        """Applies scale/position/opacity via the timeline item's Fusion
        composition Transform/Merge tools where present. Falls back to
        Resolve's native clip properties (Zoom, Pan, Tilt, Opacity) if no
        Fusion transform tool is found, so this still works for simpler
        (non-Fusion) assets like the channel bug PNG.
        """
        comp = timeline_item.GetFusionCompByIndex(1)
        transform_tool = None
        if comp is not None:
            for tool_name in comp.GetToolList(False):
                tool = comp.GetToolList(False)[tool_name]
                if tool.ID in ("Transform", "Merge"):
                    transform_tool = tool
                    break

        if transform_tool is not None:
            transform_tool.Size = scale
            transform_tool.Center = self._position_to_center(position)
            if hasattr(transform_tool, "Blend"):
                transform_tool.Blend = opacity
            return

        # Fallback: native clip property panel controls
        timeline_item.SetProperty("ZoomX", scale)
        timeline_item.SetProperty("ZoomY", scale)
        timeline_item.SetProperty("Opacity", opacity * 100.0)
        pan_x, pan_y = self._position_to_pan(position)
        timeline_item.SetProperty("Pan", pan_x)
        timeline_item.SetProperty("Tilt", pan_y)

    @staticmethod
    def _position_to_center(position: str):
        # Fusion coordinate space is 0-1, origin bottom-left.
        presets = {
            "bottom_left": [0.18, 0.15],
            "bottom_right": [0.82, 0.15],
            "bottom_center": [0.5, 0.15],
            "default": [0.5, 0.5],
        }
        return presets.get(position, presets["default"])

    @staticmethod
    def _position_to_pan(position: str):
        # Resolve native Pan/Tilt are pixel offsets from center; these are
        # conservative defaults for a 1920x1080 timeline and may need
        # adjusting for other resolutions.
        presets = {
            "bottom_left": (-600, -400),
            "bottom_right": (600, -400),
            "bottom_center": (0, -400),
            "default": (0, 0),
        }
        return presets.get(position, presets["default"])

    def list_all_media_pool_clips(self):
        """Diagnostic helper: returns a list of (folder_path, clip_name)
        for every clip visible in the Media Pool, including Power Bins
        if they're merged into the visible tree. Use this when an
        AssetNotFoundError happens, to see the exact name/casing Resolve
        actually has for a clip, and to confirm whether Power Bin
        contents are visible via the scripting API at all.
        """
        self._require_connection()
        results = []
        self._collect_folder_clips(self._media_pool.GetRootFolder(), "", results)
        return results

    def _collect_folder_clips(self, folder, path_so_far, results):
        folder_name = folder.GetName()
        current_path = f"{path_so_far}/{folder_name}" if path_so_far else folder_name
        for clip in folder.GetClipList():
            results.append((current_path, clip.GetName()))
        for sub_folder in folder.GetSubFolderList():
            self._collect_folder_clips(sub_folder, current_path, results)

    # ------------------------------------------------------------------
    # Rollback support
    # ------------------------------------------------------------------

    def remove_by_prefix(self, prefix: str) -> int:
        """Deletes every timeline item whose name starts with prefix,
        then deletes any video track that is now completely empty AND
        whose name contains " - " (the naming pattern prepare_text_track
        always uses: "{base_track_name} - {label}"). This second step
        cleans up the per-clip dedicated tracks that NATIVE text/Fusion
        inserts create, so rollback doesn't leave a growing pile of
        empty tracks behind every run.

        The " - " check is deliberately conservative: image/video asset
        tracks (logo, intro) AND ML-055's shared chapter title card
        track use plain names with no " - " separator, so this never
        touches those even if they end up empty too -- only tracks
        created by prepare_text_track match.

        This is the rollback mechanism for any single feature (e.g. pass
        graphics_config.TRACK_PREFIX_TITLE_CARD to remove only title
        cards, or TRACK_PREFIX_CHAPTER_TITLE_CARD to remove only
        ML-055's chapter cards, leaving everything else untouched).

        Returns the number of clips removed (track cleanup is separate
        and not counted).
        """
        self._require_connection()

        removed = 0
        track_count = self._timeline.GetTrackCount("video")
        for track_index in range(1, track_count + 1):
            items = self._timeline.GetItemListInTrack("video", track_index)
            for item in items:
                if item.GetName().startswith(prefix):
                    if self._timeline.DeleteClips([item]):
                        removed += 1

        # Second pass: delete now-empty per-clip tracks. Iterate in
        # reverse so deleting a track doesn't shift the indices of
        # tracks we haven't checked yet.
        track_count = self._timeline.GetTrackCount("video")
        for track_index in range(track_count, 0, -1):
            track_name = self._timeline.GetTrackName("video", track_index)
            if " - " not in track_name:
                continue
            items = self._timeline.GetItemListInTrack("video", track_index)
            if not items:
                self._timeline.DeleteTrack("video", track_index)

        return removed