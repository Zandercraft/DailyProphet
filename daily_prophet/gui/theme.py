"""Unified UI Theme and Icon Management for The Daily Prophet.

Establishes a centralized design system based on the clean, dark-wood,
aged-parchment aesthetic of the Template Editor combined with the classic
masthead typography of the Daily Prophet newspaper.
"""

from __future__ import annotations
import os
import sys
from typing import Optional, Tuple, Dict, List
import customtkinter as ctk
from PIL import Image

_FONTS_REGISTERED = False


def register_custom_fonts(font_dir: Optional[str] = None) -> None:
    """Registers bundled vintage TTF fonts into Windows GDI memory for Tkinter."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    _FONTS_REGISTERED = True

    if sys.platform != "win32":
        return

    try:
        import ctypes

        if not font_dir:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            font_dir = os.path.join(project_root, "assets", "fonts")

        if os.path.isdir(font_dir):
            for fname in os.listdir(font_dir):
                if fname.lower().endswith(".ttf"):
                    fpath = os.path.abspath(os.path.join(font_dir, fname))
                    ctypes.windll.gdi32.AddFontResourceExW(fpath, 0x10, 0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Design Tokens: Color Palette & Surfaces
# ---------------------------------------------------------------------------
class Theme:
    # Surfaces & Layers
    CANVAS_BG = "#14110e"  # Darkest backdrop (canvas / viewer)
    APP_BG = "#1c1713"  # Main window root background
    PANEL_BG = "#251e18"  # Sidebars, inspectors, scroll containers
    HEADER_BG = "#2e261f"  # Top toolbars, banners, nav bars
    CARD_BG = "#2b231c"  # Dialog cards, story items, section blocks
    INPUT_BG = "#1a1511"  # Text entries, spinboxes, textboxes

    # Borders & Dividers
    BORDER_SUBTLE = "#3d3227"  # Soft engraved borders
    BORDER_MEDIUM = "#4a3d31"  # Distinct section dividers
    BORDER_FOCUS = "#6e5945"  # Active focus outline

    # Typography & Foregrounds
    TEXT_PARCHMENT = "#f5ede0"  # High-contrast parchment off-white
    TEXT_LIGHT = "#f0e6d6"  # Standard primary text
    TEXT_MUTED = "#c4b7a5"  # Secondary descriptions and labels
    TEXT_SUBTLE = "#8e8172"  # Inactive placeholders, hints, shortcuts
    TEXT_ACCENT = "#e5c158"  # Warm golden yellow
    TEXT_CRIMSON = "#e05252"  # Red highlight / alert

    # Status Badges
    STATUS_MODIFIED_BG = "#8f4a2d"
    STATUS_MODIFIED_FG = "#ffffff"
    STATUS_BUNDLED_BG = "#3d342a"
    STATUS_BUNDLED_FG = "#c2b6a4"
    STATUS_CUSTOM_BG = "#2b3e50"
    STATUS_CUSTOM_FG = "#c2b6a4"

    # Action Buttons (fg_color, hover_color)
    BTN_PRIMARY = ("#8c2828", "#6e1f1f")  # Rich Crimson (Save, Rebuild, Publish)
    BTN_SUCCESS = ("#3d4f40", "#2f3d32")  # Forest Slate (Export, Generate, Confirm)
    BTN_NEUTRAL = ("#34495e", "#2c3e50")  # Slate Navy (New, Import, Inspect)
    BTN_SECONDARY = ("#4a3e2c", "#382e20")  # Warm Oak (Reset, Browse, Configure)
    BTN_DANGER = ("#542525", "#732525")  # Deep Maroon (Delete, Clear)
    BTN_CONTROL = ("#332921", "#45372c")  # Compact utility (Zoom, Arrows)

    # Standard Button Dimensions
    BTN_HEIGHT_SM = 26
    BTN_HEIGHT_MD = 32
    BTN_HEIGHT_LG = 38

    # -----------------------------------------------------------------------
    # Typography Helpers
    # -----------------------------------------------------------------------
    @classmethod
    def get_preferred_font(
        cls,
        candidates: List[str],
        fallback: str = "Georgia",
    ) -> str:
        register_custom_fonts()
        try:
            from tkinter import font as tkfont
            import tkinter as tk

            if tk._default_root:
                available = {f.lower() for f in tkfont.families()}
                for c in candidates:
                    if c.lower() in available:
                        return c
        except Exception:
            pass
        return fallback

    @classmethod
    def font_masthead(cls, size: int = 20, weight: str = "bold") -> ctk.CTkFont:
        family = cls.get_preferred_font(["Cinzel", "Playfair Display"], fallback="Georgia")
        return ctk.CTkFont(family=family, size=size, weight=weight)

    @classmethod
    def font_masthead_subtitle(cls, size: int = 13, slant: str = "italic") -> ctk.CTkFont:
        family = cls.get_preferred_font(["IM FELL English", "Playfair Display"], fallback="Georgia")
        return ctk.CTkFont(family=family, size=size, slant=slant)

    @classmethod
    def font_title(cls, size: int = 15, weight: str = "bold") -> ctk.CTkFont:
        family = cls.get_preferred_font(["Cinzel", "Playfair Display"], fallback="Georgia")
        return ctk.CTkFont(family=family, size=size, weight=weight)

    @staticmethod
    def font_section() -> ctk.CTkFont:
        return ctk.CTkFont(size=12, weight="bold")

    @staticmethod
    def font_body() -> ctk.CTkFont:
        return ctk.CTkFont(size=12)

    @staticmethod
    def font_body_italic() -> ctk.CTkFont:
        return ctk.CTkFont(family="Georgia", size=11, slant="italic")

    @staticmethod
    def font_caption() -> ctk.CTkFont:
        return ctk.CTkFont(size=11)

    @staticmethod
    def font_button() -> ctk.CTkFont:
        return ctk.CTkFont(size=11, weight="bold")

    # -----------------------------------------------------------------------
    # Component Helpers
    # -----------------------------------------------------------------------
    @classmethod
    def create_header_banner(
        cls, parent: ctk.CTkBaseClass, title: str, subtitle: Optional[str] = None, height: int = 60
    ) -> ctk.CTkFrame:
        """Creates a standardized, clean Daily Prophet header banner."""
        header = ctk.CTkFrame(parent, fg_color=cls.HEADER_BG, corner_radius=0, height=height)
        header.pack(fill="x", padx=0, pady=(0, 8))

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=8)

        title_lbl = ctk.CTkLabel(inner, text=title, font=cls.font_masthead(size=18), text_color=cls.TEXT_PARCHMENT)
        title_lbl.pack(side="left", padx=(0, 10))

        if subtitle:
            sub_lbl = ctk.CTkLabel(
                inner, text=subtitle, font=cls.font_masthead_subtitle(size=12), text_color=cls.TEXT_MUTED
            )
            sub_lbl.pack(side="left", padx=4)

        return header


# ---------------------------------------------------------------------------
# Vector Icon Manager (tkinter-icons with Graceful Fallback)
# ---------------------------------------------------------------------------
class IconManager:
    """Manages vector icon generation from tkinter-icons packs.

    Supports 'lucide', 'material', and 'rpg-awesome'.
    Automatically converts rendered glyphs into ctk.CTkImage objects.
    """

    _cache: Dict[Tuple[str, str, int, str], ctk.CTkImage] = {}
    _checked_modules = False
    _has_lucide = False
    _has_material = False
    _has_rpg = False

    @classmethod
    def _init_modules(cls):
        if cls._checked_modules:
            return
        cls._checked_modules = True
        try:
            from tkinter_icons import LucideIcon

            cls._has_lucide = bool(LucideIcon)
        except ImportError:
            cls._has_lucide = False

        try:
            from tkinter_icons import MaterialIcon

            cls._has_material = bool(MaterialIcon)
        except ImportError:
            cls._has_material = False

        try:
            from tkinter_icons import RpgAwesomeIcon

            cls._has_rpg = bool(RpgAwesomeIcon)
        except ImportError:
            cls._has_rpg = False

    @classmethod
    def get_icon(
        cls, name: str, size: int = 16, color: Optional[str] = None, pack: str = "lucide"
    ) -> Optional[ctk.CTkImage]:
        """Loads a vector icon from tkinter-icons and returns a ctk.CTkImage."""
        cls._init_modules()
        icon_color = color or Theme.TEXT_PARCHMENT
        cache_key = (name, pack, size, icon_color)

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        pil_img = None
        try:
            icon_obj = None
            if pack == "lucide" and cls._has_lucide:
                from tkinter_icons import LucideIcon

                icon_obj = LucideIcon(name, size=size, color=icon_color)
            elif pack == "material" and cls._has_material:
                from tkinter_icons import MaterialIcon

                icon_obj = MaterialIcon(name, size=size, color=icon_color)
            elif pack == "rpg" and cls._has_rpg:
                from tkinter_icons import RpgAwesomeIcon

                icon_obj = RpgAwesomeIcon(name, size=size, color=icon_color)

            if icon_obj is not None:
                if hasattr(icon_obj, "to_pil"):
                    pil_img = icon_obj.to_pil()
                elif hasattr(icon_obj, "render_pil"):
                    pil_img = icon_obj.render_pil()
        except Exception:
            pil_img = None

        if pil_img is not None and isinstance(pil_img, Image.Image):
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
            cls._cache[cache_key] = ctk_img
            return ctk_img

        return None
