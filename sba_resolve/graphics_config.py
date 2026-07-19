"""
graphics_config.py

Shared configuration for all AI-driven graphics features (ML-044 Title Cards,
ML-045 Channel Bug, ML-046 Lower-Thirds).

Centralising this here means every feature reads/writes the same settings
object instead of hardcoding durations, template names, or track-naming
conventions independently. If Gary changes a default (e.g. title card
duration) in the GUI settings panel, every feature picks it up from one place.

NOTE: Update TEMPLATE_BIN_PATH and the *_TEMPLATE_NAME values below to match
the exact names/locations of Gary's saved Fusion Title templates in his
Media Pool before this is used for real. Placeholder values are marked TODO.
"""

from dataclasses import dataclass, field
from typing import Dict


# ---------------------------------------------------------------------------
# Track naming convention
# ---------------------------------------------------------------------------
# Every clip an AI graphics feature creates gets a name prefixed with one of
# these. This is the mechanism that makes rollback unambiguous: deleting all
# clips whose name starts with a given prefix removes exactly what that
# feature added, and nothing else.

TRACK_PREFIX_TITLE_CARD = "AI_TitleCard_"
TRACK_PREFIX_LOWER_THIRD = "AI_LowerThird_"
TRACK_PREFIX_CHANNEL_BUG = "AI_ChannelBug"
TRACK_PREFIX_INTRO = "AI_Intro"

# Dedicated video track names (created if they don't already exist).
# Each feature gets its own track so rollback of one feature never touches
# clips belonging to another.
TRACK_NAME_TITLE_CARDS = "AI Title Cards"
TRACK_NAME_LOWER_THIRDS = "AI Lower Thirds"
TRACK_NAME_CHANNEL_BUG = "AI Channel Bug"
TRACK_NAME_INTRO = "AI Intro"


# ---------------------------------------------------------------------------
# Channel bug: a real image file, not a Resolve template
# ---------------------------------------------------------------------------
# Gary has the circular logo badge as a PNG on disk, not a saved Fusion
# Title template inside Resolve. This gets imported into the Media Pool
# directly and placed as-is (see GraphicInserter.insert_image_asset()).

# The logo already exists in Gary's persistent Power Bin (named "logo"),
# as a clip called "logo.png" -- this is checked first before ever
# falling back to importing from disk (see GraphicInserter._get_or_import_image).
# CHANNEL_BUG_IMAGE_PATH stays as a fallback only, in case the Power Bin
# clip is ever missing/renamed and a fresh import is needed.
CHANNEL_BUG_IMAGE_PATH = r"D:\Download\logo\logo.png"
CHANNEL_BUG_MEDIA_POOL_NAME = "logo.png"

# The intro clip lives locally alongside the logo (Power Bin lookup can't
# work -- Power Bins aren't reachable via Resolve's scripting API at all,
# confirmed via testing). Uses the same disk-fallback pattern as the logo.
INTRO_CLIP_MEDIA_POOL_NAME = "Intro 2026"
INTRO_CLIP_IMAGE_PATH = r"D:\Download\logo\Intro 2026.mp4"


# ---------------------------------------------------------------------------
# Title cards / lower-thirds: no saved template exists, so these are built
# from Resolve's native Text+ generator and styled in code to match the
# channel branding (navy background, white Impact-style text, gold accent).
# ---------------------------------------------------------------------------

TITLE_TEXT_FONT = "Impact"
TITLE_TEXT_STYLE = "Regular"    # Fusion TextPlus weight/variant, separate from family
TITLE_TEXT_SIZE = 0.08  # Fusion TextPlus "Size" input, confirmed 0.0-1.0 range
TITLE_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)        # white, RGBA 0-1
TITLE_ACCENT_COLOR = (0.83, 0.68, 0.21, 1.0)   # gold, RGBA 0-1
TITLE_BACKGROUND_COLOR = (0.04, 0.09, 0.22, 0.85)  # navy, semi-opaque


# ---------------------------------------------------------------------------
# Default timing settings (all configurable via the GUI settings panel;
# these are just the fallback defaults, not hardcoded behaviour)
# ---------------------------------------------------------------------------

@dataclass
class GraphicsSettings:
    # ML-044 Title Cards
    title_card_duration_seconds: float = 4.0

    # ML-046 Lower-Thirds
    lower_third_duration_seconds: float = 5.0
    lower_third_scale: float = 0.55          # relative to full title card size
    lower_third_position: str = "bottom_left"  # bottom_left | bottom_right | bottom_center

    # ML-045 Channel Bug
    channel_bug_opacity: float = 0.35
    channel_bug_scale: float = 0.12          # relative to frame size
    channel_bug_position: str = "bottom_right"
    channel_bug_full_duration: bool = True   # False = intro/outro only

    # Shared
    fade_in_out_seconds: float = 0.3

    def as_dict(self) -> Dict:
        return {
            "title_card_duration_seconds": self.title_card_duration_seconds,
            "lower_third_duration_seconds": self.lower_third_duration_seconds,
            "lower_third_scale": self.lower_third_scale,
            "lower_third_position": self.lower_third_position,
            "channel_bug_opacity": self.channel_bug_opacity,
            "channel_bug_scale": self.channel_bug_scale,
            "channel_bug_position": self.channel_bug_position,
            "channel_bug_full_duration": self.channel_bug_full_duration,
            "fade_in_out_seconds": self.fade_in_out_seconds,
        }


DEFAULT_SETTINGS = GraphicsSettings()
