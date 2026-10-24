"""Native Broadsheet Renderer for The Daily Prophet.

Renders authentic, high-resolution Harry Potter broadsheet newspapers directly onto vintage wizarding parchment templates.
Supports borderless PDF and high-res PNG/JPEG exports.
"""

import math
import os
from typing import List, Tuple, Optional, Dict
from PIL import Image, ImageDraw, ImageFont

from .models import NewspaperEdition, NewspaperPage, Story, StoryPriority
from .template_package import load_all_installed_templates


class BroadsheetFontManager:
    """Loads and caches authentic wizarding fonts."""

    def __init__(self, base_dir: str):
        self.fonts_dir = os.path.join(base_dir, "assets", "fonts")
        self.cache = {}

    def get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (font_name, size)
        if key in self.cache:
            return self.cache[key]

        font_file_map = {
            "title": "UnifrakturMaguntia-Regular.ttf",
            "headline": "Cinzel.ttf",
            "subhead": "PlayfairDisplay.ttf",
            "subhead_italic": "PlayfairDisplay-Italic.ttf",
            "body": "IMFellEnglish-Regular.ttf",
            "body_italic": "IMFellEnglish-Italic.ttf",
            "script": "PlayfairDisplay-Italic.ttf",
        }

        filename = font_file_map.get(font_name, font_name)
        font_path = os.path.join(self.fonts_dir, filename)

        font = None
        if os.path.isfile(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
            except Exception:
                font = None

        if font is None:
            # Fallback to system Georgia / Times
            system_fallbacks = [
                r"C:\Windows\Fonts\georgia.ttf",
                r"C:\Windows\Fonts\times.ttf",
                r"C:\Windows\Fonts\arial.ttf",
            ]
            for sys_p in system_fallbacks:
                if os.path.isfile(sys_p):
                    try:
                        font = ImageFont.truetype(sys_p, size)
                        break
                    except Exception:
                        pass

        if font is None:
            font = ImageFont.load_default()

        self.cache[key] = font
        return font


_GLYPH_WIDTH_CACHE: Dict[Tuple[int, str], float] = {}


def _get_word_width(font: ImageFont.FreeTypeFont, word: str) -> float:
    key = (id(font), word)
    w = _GLYPH_WIDTH_CACHE.get(key)
    if w is None:
        if "★" in word or "\u2605" in word:
            parts = word.replace("\u2605", "★").split("★")
            try:
                tb = font.getbbox("Hg")
                line_h = float(tb[3] - tb[1])
            except Exception:
                line_h = 14.0
            star_w = max(4.0, line_h * 0.9)
            text_w = sum(font.getlength(p) if hasattr(font, "getlength") else len(p) * 8.0 for p in parts if p)
            w = float(text_w + (len(parts) - 1) * star_w)
        else:
            try:
                w = float(font.getlength(word))
            except Exception:
                w = float(len(word) * 8)
        if len(_GLYPH_WIDTH_CACHE) > 10000:
            _GLYPH_WIDTH_CACHE.clear()
        _GLYPH_WIDTH_CACHE[key] = w
    return w


def _draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: Tuple[int, int, int]) -> None:
    """Draws a crisp geometric 5-pointed star."""
    points = []
    inner_r = r * 0.40
    for i in range(10):
        angle = i * (math.pi / 5.0) - (math.pi / 2.0)
        radius = r if i % 2 == 0 else inner_r
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        points.append((px, py))
    draw.polygon(points, fill=fill)


def _draw_text_with_symbols(
    draw: ImageDraw.ImageDraw,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
) -> None:
    """Draws text with geometric vector rendering for symbols not present in vintage fonts (e.g. ★)."""
    if "★" not in text and "\u2605" not in text:
        draw.text(pos, text, font=font, fill=fill)
        return

    cur_x = float(pos[0])
    cur_y = float(pos[1])
    try:
        tb = font.getbbox("Hg")
        line_h = float(tb[3] - tb[1])
    except Exception:
        line_h = 14.0
    star_r = max(2.5, line_h * 0.38)
    star_w = max(4.0, line_h * 0.9)

    parts = text.replace("\u2605", "★").split("★")
    for idx, part in enumerate(parts):
        if part:
            draw.text((int(round(cur_x)), int(round(cur_y))), part, font=font, fill=fill)
            try:
                cur_x += float(font.getlength(part))
            except Exception:
                cur_x += float(len(part) * 8)
        if idx < len(parts) - 1:
            cx = cur_x + star_w / 2.0
            cy = cur_y + line_h / 2.0
            _draw_star(draw, cx, cy, star_r, fill)
            cur_x += star_w


def _wrap_text_to_width(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> List[str]:
    """Wraps text so each line fits within max_width pixels with O(N) word caching."""
    if not text:
        return []
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current_line: List[str] = []
    current_w = 0.0
    space_w = _get_word_width(font, " ")

    for word in words:
        w_w = _get_word_width(font, word)
        added_w = w_w if not current_line else (space_w + w_w)
        if (current_w + added_w <= max_width) or not current_line:
            current_line.append(word)
            current_w += added_w
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_w = w_w

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _draw_justified_line(
    draw: ImageDraw.ImageDraw,
    words: List[str],
    word_widths: List[float],
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
    fill: Tuple[int, int, int],
):
    """Draws a single line of text with inter-word justification without redundant measurements."""
    if len(words) <= 1:
        _draw_text_with_symbols(draw, (x, y), " ".join(words), font=font, fill=fill)
        return

    total_words_w = sum(word_widths)
    space_to_distribute = max_width - total_words_w
    if space_to_distribute <= 0:
        _draw_text_with_symbols(draw, (x, y), " ".join(words), font=font, fill=fill)
        return

    space_per_gap = space_to_distribute / (len(words) - 1)
    cur_x = float(x)
    for word, w_w in zip(words, word_widths):
        _draw_text_with_symbols(draw, (round(cur_x), y), word, font=font, fill=fill)
        cur_x += w_w + space_per_gap


def _draw_story_paragraphs(
    draw: ImageDraw.ImageDraw,
    paragraphs: List[str],
    font: ImageFont.FreeTypeFont,
    font_bold: ImageFont.FreeTypeFont,
    drop_font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_w: int,
    max_h: int,
    line_h: int,
    fill: Tuple[int, int, int],
    has_drop_cap: bool = False,
    avoid_rect: Optional[Tuple[int, int, int, int]] = None,  # (ax, ay, aw, ah)
    align: str = "justify",
) -> int:
    """Draws paragraphs with configurable justification ('justify', 'left', 'center', 'right'),

    wrapping around an avoid_rect with high-performance word caching.
    """
    cur_y = y
    first_para = True
    space_w = _get_word_width(font, " ")

    for para in paragraphs:
        clean = para.strip()
        if not clean:
            continue

        words = clean.split()
        if not words:
            continue

        indent = 0.0
        if first_para and has_drop_cap and len(words[0]) > 0:
            first_char = words[0][0]
            if first_char.isalpha():
                drop_char = first_char
                words[0] = words[0][1:]
                drop_w = _get_word_width(drop_font, drop_char) + 6.0
                draw.text((x, cur_y - 2), drop_char, font=drop_font, fill=fill)
                indent = drop_w
        elif not first_para:
            indent = 14.0

        current_words: List[str] = []
        current_widths: List[float] = []
        current_line_w = 0.0
        is_first_line_of_para = True

        for word in words:
            w_w = _get_word_width(font, word)

            base_x = x + (indent if is_first_line_of_para else 0.0)
            avail_x = base_x
            avail_w = max_w - (indent if is_first_line_of_para else 0.0)

            if avoid_rect:
                ax, ay, aw, ah = avoid_rect
                if ay <= cur_y < ay + ah:
                    if ax <= x + 20:
                        avail_x = ax + aw + 10
                        avail_w = (x + max_w) - avail_x
                    else:
                        avail_w = max(40.0, ax - avail_x - 10)

            added_w = w_w if not current_words else (space_w + w_w)
            if (current_line_w + added_w <= avail_w) or not current_words:
                current_words.append(word)
                current_widths.append(w_w)
                current_line_w += added_w
            else:
                if cur_y + line_h > y + max_h:
                    return cur_y
                if align == "center":
                    lw = sum(current_widths) + (len(current_words) - 1) * space_w
                    cx = int(avail_x + max(0.0, (avail_w - lw) / 2))
                    _draw_text_with_symbols(draw, (cx, cur_y), " ".join(current_words), font=font, fill=fill)
                elif align == "right":
                    lw = sum(current_widths) + (len(current_words) - 1) * space_w
                    rx_pos = int(avail_x + max(0.0, avail_w - lw))
                    _draw_text_with_symbols(draw, (rx_pos, cur_y), " ".join(current_words), font=font, fill=fill)
                elif align == "left":
                    _draw_text_with_symbols(draw, (int(avail_x), cur_y), " ".join(current_words), font=font, fill=fill)
                else:  # "justify"
                    _draw_justified_line(
                        draw, current_words, current_widths, font, int(avail_x), cur_y, int(avail_w), fill
                    )
                cur_y += line_h
                current_words = [word]
                current_widths = [w_w]
                current_line_w = w_w
                is_first_line_of_para = False
                if first_para and has_drop_cap:
                    indent = 0.0

        if current_words:
            if cur_y + line_h > y + max_h:
                return cur_y
            base_x = x + (indent if is_first_line_of_para else 0.0)
            avail_x = base_x
            avail_w = max_w - (indent if is_first_line_of_para else 0.0)
            if avoid_rect:
                ax, ay, aw, ah = avoid_rect
                if ay <= cur_y < ay + ah:
                    if ax <= x + 20:
                        avail_x = ax + aw + 10
                        avail_w = (x + max_w) - avail_x
                    else:
                        avail_w = max(40.0, ax - avail_x - 10)

            if align == "center":
                lw = sum(current_widths) + (len(current_words) - 1) * space_w
                cx = int(avail_x + max(0.0, (avail_w - lw) / 2))
                _draw_text_with_symbols(draw, (cx, cur_y), " ".join(current_words), font=font, fill=fill)
            elif align == "right":
                lw = sum(current_widths) + (len(current_words) - 1) * space_w
                rx_pos = int(avail_x + max(0.0, avail_w - lw))
                _draw_text_with_symbols(draw, (rx_pos, cur_y), " ".join(current_words), font=font, fill=fill)
            else:
                _draw_text_with_symbols(draw, (int(avail_x), cur_y), " ".join(current_words), font=font, fill=fill)
            cur_y += line_h + 4

        first_para = False

    return cur_y


def _parse_slot_color(color_val: object, default_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Parses a hex color string (e.g. #6e1818 or #120e0a) into an RGB integer tuple."""
    if not color_val or not isinstance(color_val, str):
        return default_rgb
    c = color_val.strip().split()[0]  # strip any label like '#6e1818 (Crimson)'
    if c.startswith("#") and len(c) in (7, 4):
        try:
            if len(c) == 7:
                return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16))
            elif len(c) == 4:
                return (int(c[1] * 2, 16), int(c[2] * 2, 16), int(c[3] * 2, 16))
        except ValueError:
            pass
    return default_rgb


FONT_FAMILY_MAP = {
    "cinzel": "headline",
    "cinzel (headline)": "headline",
    "cinzel (classic headline)": "headline",
    "unifraktur": "title",
    "unifraktur (gothic)": "title",
    "unifraktur (gothic masthead)": "title",
    "playfair": "subhead",
    "playfair (subhead)": "subhead",
    "playfair display": "subhead",
    "playfair display (subhead)": "subhead",
    "playfair italic": "subhead_italic",
    "playfair display italic": "subhead_italic",
    "im fell english": "body",
    "im fell english (body)": "body",
    "im fell english (vintage body)": "body",
    "im fell english italic": "body_italic",
    "script": "script",
}


def _resolve_slot_font(slot_family: object, fallback_type: str) -> str:
    """Maps slot font family name to font manager key."""
    if not slot_family or not isinstance(slot_family, str) or "default" in slot_family.lower():
        return fallback_type
    key = slot_family.strip().lower()
    return FONT_FAMILY_MAP.get(key, fallback_type)


def _resolve_slot_font_size(slot_size: object, fallback_size: int, scale: float) -> int:
    """Parses slot font size in pt or px, applying renderer scale."""
    if slot_size is not None:
        try:
            val_str = str(slot_size).lower().replace("pt", "").replace("px", "").strip()
            val = float(val_str)
            if val > 0:
                return max(int(6 * scale), int(val * scale))
        except (ValueError, TypeError):
            pass
    return fallback_size


def _resolve_slot_align(slot_align: object, fallback_align: str = "left") -> str:
    """Resolves slot text alignment / justification: 'justify', 'left', 'center', or 'right'."""
    if not slot_align or not isinstance(slot_align, str) or "default" in slot_align.lower():
        return fallback_align
    val = slot_align.strip().lower()
    if "justif" in val:
        return "justify"
    if "center" in val:
        return "center"
    if "right" in val:
        return "right"
    if "left" in val:
        return "left"
    return fallback_align


def map_slots_to_stories(
    page_stories: List[Story], slots: List[Dict[str, object]]
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Deterministically maps template slots to stories and vice-versa based on layout geometry and priorities.

    Returns:
        (slot_to_story, story_to_slots)
        slot_to_story: dict mapping slot_id -> story_id
        story_to_slots: dict mapping story_id -> list of slot_ids assigned to that story
    """
    if not page_stories or not slots:
        return {}, {}

    cover_stories = [s for s in page_stories if s.priority == StoryPriority.COVER.value]
    major_stories = [s for s in page_stories if s.priority == StoryPriority.MAJOR.value]

    cover = cover_stories[0] if cover_stories else page_stories[0]
    major = major_stories[0] if major_stories else (page_stories[1] if len(page_stories) > 1 else cover)

    has_major_slot = any(
        ("feature" in s.get("id", "") or "sidebar" in s.get("id", "") or "story_2" in s.get("id", ""))
        for s in slots
        if s.get("type") in ["headline", "subheadline", "body", "column", "photo"]
    )

    if has_major_slot:
        other_stories = [s for s in page_stories if s.id != cover.id and s.id != major.id]
    else:
        other_stories = [s for s in page_stories if s.id != cover.id]

    if not other_stories:
        other_stories = [cover]

    story_cursor = 0
    slot_to_story: Dict[str, str] = {}
    story_to_slots: Dict[str, List[str]] = {s.id: [] for s in page_stories}

    for slot in slots:
        sid = slot.get("id", "")
        stype = slot.get("type", "")
        if stype in ["headline", "subheadline"]:
            target = (
                cover
                if ("lead" in sid or "main" in sid or "hero" in sid)
                else (
                    major
                    if ("feature" in sid or "top" in sid or "story_2" in sid)
                    else other_stories[story_cursor % len(other_stories)]
                )
            )
            slot_to_story[sid] = target.id
            if sid not in story_to_slots[target.id]:
                story_to_slots[target.id].append(sid)
        elif stype == "photo":
            target = (
                cover
                if ("lead" in sid or "hero" in sid or "top" in sid)
                else (
                    major
                    if ("feature" in sid or "story_2" in sid)
                    else other_stories[story_cursor % len(other_stories)]
                )
            )
            slot_to_story[sid] = target.id
            if sid not in story_to_slots[target.id]:
                story_to_slots[target.id].append(sid)
        elif stype in ["body", "column"]:
            target = cover if ("lead" in sid or "hero" in sid) else other_stories[story_cursor % len(other_stories)]
            if stype == "column":
                story_cursor += 1
            slot_to_story[sid] = target.id
            if sid not in story_to_slots[target.id]:
                story_to_slots[target.id].append(sid)

    return slot_to_story, story_to_slots


class NativeBroadsheetRenderer:
    """Composites an authentic, print-ready Harry Potter broadsheet newspaper."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        self.fonts = BroadsheetFontManager(self.base_dir)
        self._bg_cache: Dict[Tuple[str, int, int], Image.Image] = {}
        self._photo_cache: Dict[Tuple[str, int, int, float], Image.Image] = {}

    def clear_caches(self) -> None:
        """Clears pre-rendered background canvases and resized photo caches."""
        self._bg_cache.clear()
        self._photo_cache.clear()

    def render(
        self,
        edition: NewspaperEdition,
        template_id: str = "layout_1",
        scale: float = 1.0,
        page: Optional[NewspaperPage] = None,
    ) -> Image.Image:
        """Renders content directly into the authentic vintage newspaper layout template."""
        return self.render_slot_layout(edition, template_id=template_id, scale=scale, page=page)

    def render_template(
        self,
        edition: NewspaperEdition,
        template_id: str = "layout_1",
        scale: float = 1.0,
        page: Optional[NewspaperPage] = None,
    ) -> Image.Image:
        """Alias for render_slot_layout."""
        return self.render_slot_layout(edition, template_id=template_id, scale=scale, page=page)

    def render_page(self, edition: NewspaperEdition, page_idx: int = 0, scale: float = 1.0) -> Image.Image:
        """Renders a specific page of the publication using that page's assigned layout and stories."""
        if hasattr(edition, "get_page"):
            page = edition.get_page(page_idx)
            return self.render_slot_layout(edition, template_id=page.layout_id, scale=scale, page=page)
        return self.render_slot_layout(edition, template_id=edition.selected_layout, scale=scale)

    def render_all_pages(self, edition: NewspaperEdition, scale: float = 1.0) -> List[Image.Image]:
        """Renders every page of the publication in order into a list of PIL Images."""
        if hasattr(edition, "pages") and edition.pages:
            return [
                self.render_slot_layout(edition, template_id=p.layout_id, scale=scale, page=p) for p in edition.pages
            ]
        return [self.render_slot_layout(edition, template_id=edition.selected_layout, scale=scale)]

    def render_slot_layout(
        self,
        edition: NewspaperEdition,
        template_id: str = "layout_1",
        scale: float = 1.0,
        page: Optional[NewspaperPage] = None,
    ) -> Image.Image:
        """Renders content dynamically into any installed .prophettemplate layout."""
        all_layouts = load_all_installed_templates(base_dir=self.base_dir)

        # Resolve page and layout id
        if page is not None and hasattr(page, "layout_id") and page.layout_id:
            template_id = page.layout_id

        # Normalize template id
        if not template_id or template_id in ["default", "broadsheet_single_page"]:
            template_id = "layout_1"

        # Check project-level customized layout slots first
        layout_def = None
        if hasattr(edition, "custom_layouts") and edition.custom_layouts:
            layout_def = edition.custom_layouts.get(template_id)
            if not layout_def and template_id.startswith("additional_"):
                layout_def = edition.custom_layouts.get(template_id.replace("additional_", ""))

        if not layout_def:
            layout_def = all_layouts.get(template_id)
            if not layout_def and template_id.startswith("additional_"):
                alt_id = template_id.replace("additional_", "")
                layout_def = all_layouts.get(alt_id)
        if not layout_def:
            layout_def = all_layouts.get("layout_1", {})

        page_rel = layout_def["page_file"]
        page_abs = os.path.join(self.base_dir, page_rel)
        if not os.path.exists(page_abs):
            page_abs = os.path.abspath(page_rel)

        base_w = layout_def.get("width", 1024)
        base_h = layout_def.get("height", 1400)
        target_w = int(base_w * scale)
        target_h = int(base_h * scale)

        bg_key = (page_abs, target_w, target_h)
        if bg_key not in self._bg_cache:
            if os.path.exists(page_abs):
                with Image.open(page_abs) as p_img:
                    self._bg_cache[bg_key] = p_img.resize((target_w, target_h), Image.Resampling.LANCZOS).convert(
                        "RGBA"
                    )
            else:
                self._bg_cache[bg_key] = Image.new("RGBA", (target_w, target_h), (226, 212, 178, 255))
        canvas = self._bg_cache[bg_key].copy()

        draw = ImageDraw.Draw(canvas)

        ink_black = (18, 14, 10)
        ink_dark = (42, 34, 26)
        ink_muted = (92, 78, 64)
        border_ink = (32, 24, 18)
        accent_red = (110, 24, 24)

        def S(v: int) -> int:
            return int(v * scale)

        # Pool of stories to assign across slots for this page
        if page is not None and hasattr(page, "stories") and page.stories:
            page_stories = page.stories
        else:
            page_stories = edition.stories

        slots = layout_def.get("slots", [])
        slot_to_story, _ = map_slots_to_stories(page_stories, slots)
        story_by_id = {s.id: s for s in page_stories}
        default_story = page_stories[0] if page_stories else None

        lore_cursor = 0
        lore_items = [
            (edition.lore_title_1, edition.lore_body_1),
            (edition.lore_title_2, edition.lore_body_2),
            ("WORDS OF WISDOM", f'"{edition.quote_text}" — {edition.quote_author}'),
        ]

        for slot in slots:
            sid = slot.get("id", "")
            stype = slot.get("type", "body")
            rx, ry, rw, rh = [S(v) for v in slot["rect"]]
            target_story = story_by_id.get(slot_to_story.get(sid, ""), default_story)

            if stype == "title":
                t_font_type = _resolve_slot_font(slot.get("font_family"), "title")
                t_font_sz = _resolve_slot_font_size(slot.get("font_size"), min(S(48), max(S(18), int(rh * 0.7))), scale)
                t_font = self.fonts.get_font(t_font_type, t_font_sz)
                t_color = _parse_slot_color(slot.get("text_color"), ink_black)
                txt = (edition.paper_title.strip() or "DAILY PROPHET").upper()
                t_bbox = draw.textbbox((0, 0), txt, font=t_font)
                tw = t_bbox[2] - t_bbox[0]
                th = t_bbox[3] - t_bbox[1]
                t_align = _resolve_slot_align(slot.get("align", slot.get("justification")), "center")
                if t_align == "left":
                    tx = rx
                elif t_align == "right":
                    tx = rx + max(0, rw - tw)
                else:
                    tx = rx + max(0, (rw - tw) // 2)
                ty = ry + max(0, (rh - th) // 2)
                _draw_text_with_symbols(draw, (tx, ty), txt, font=t_font, fill=t_color)

            elif stype == "ear_box":
                draw.rectangle([rx, ry, rx + rw, ry + rh], outline=border_ink, width=S(1))
                if "left" in sid:
                    draw.text(
                        (rx + S(6), ry + S(4)),
                        edition.edition_day.upper(),
                        font=self.fonts.get_font("headline", S(9)),
                        fill=ink_black,
                    )
                    draw.text(
                        (rx + S(6), ry + S(18)),
                        edition.edition_date.upper(),
                        font=self.fonts.get_font("subhead", S(10)),
                        fill=ink_black,
                    )
                    draw.line([rx + S(6), ry + S(34), rx + rw - S(6), ry + S(34)], fill=border_ink, width=S(1))
                    draw.text(
                        (rx + S(6), ry + S(38)),
                        edition.issue_number.upper(),
                        font=self.fonts.get_font("headline", S(8)),
                        fill=ink_muted,
                    )
                else:
                    draw.text(
                        (rx + S(6), ry + S(4)),
                        "PRICE: " + edition.price.upper(),
                        font=self.fonts.get_font("headline", S(9)),
                        fill=accent_red,
                    )
                    draw.text(
                        (rx + S(6), ry + S(18)),
                        "CASTLE WEATHER",
                        font=self.fonts.get_font("headline", S(8)),
                        fill=ink_black,
                    )
                    draw.line([rx + S(6), ry + S(30), rx + rw - S(6), ry + S(30)], fill=border_ink, width=S(1))
                    draw.text(
                        (rx + S(6), ry + S(35)),
                        edition.weather[:24],
                        font=self.fonts.get_font("body_italic", S(8)),
                        fill=ink_dark,
                    )

            elif stype == "slogan":
                s_font_type = _resolve_slot_font(slot.get("font_family"), "headline")
                s_font_sz = _resolve_slot_font_size(slot.get("font_size"), min(S(10), max(S(7), int(rh * 0.45))), scale)
                s_font = self.fonts.get_font(s_font_type, s_font_sz)
                s_color = _parse_slot_color(slot.get("text_color"), ink_dark)
                s_text = f"✦ {edition.tagline} ✦" if edition.tagline else ""
                sb = draw.textbbox((0, 0), s_text, font=s_font)
                sw = sb[2] - sb[0]
                s_align = _resolve_slot_align(slot.get("align", slot.get("justification")), "center")
                if s_align == "left":
                    sx = rx
                elif s_align == "right":
                    sx = rx + max(0, rw - sw)
                else:
                    sx = rx + (rw - sw) // 2
                _draw_text_with_symbols(draw, (sx, ry + S(3)), s_text, font=s_font, fill=s_color)

            elif stype in ["ticker", "banner"]:
                draw.line([rx, ry, rx + rw, ry], fill=border_ink, width=S(1))
                draw.line([rx, ry + rh, rx + rw, ry + rh], fill=border_ink, width=S(1))
                tk_font_type = _resolve_slot_font(slot.get("font_family"), "headline")
                tk_font_sz = _resolve_slot_font_size(slot.get("font_size"), min(S(9), max(S(7), int(rh * 0.4))), scale)
                tk_font = self.fonts.get_font(tk_font_type, tk_font_sz)
                tk_color = _parse_slot_color(slot.get("text_color"), ink_black)
                if stype == "ticker":
                    tk_text = edition.topic_bar
                else:
                    tk_text = edition.breaking_banner or f"❖ {edition.tagline.upper()} ❖"
                tk_bbox = draw.textbbox((0, 0), tk_text, font=tk_font)
                tkw = tk_bbox[2] - tk_bbox[0]
                tk_align = _resolve_slot_align(slot.get("align", slot.get("justification")), "center")
                if tk_align == "left":
                    tkx = rx + S(4)
                elif tk_align == "right":
                    tkx = rx + max(0, rw - tkw - S(4))
                else:
                    tkx = rx + max(0, (rw - tkw) // 2)
                _draw_text_with_symbols(draw, (tkx, ry + S(4)), tk_text, font=tk_font, fill=tk_color)

            elif stype in ["headline", "subheadline"]:
                if not target_story:
                    continue
                text_str = (
                    target_story.headline.upper()
                    if stype == "headline"
                    else (target_story.subheadline or target_story.headline)
                )
                if not text_str.strip():
                    continue
                font_type = _resolve_slot_font(
                    slot.get("font_family"), "headline" if stype == "headline" else "subhead_italic"
                )
                font_size = _resolve_slot_font_size(
                    slot.get("font_size"), min(S(20), max(S(10), int(rh * 0.42))), scale
                )
                h_font = self.fonts.get_font(font_type, font_size)
                h_color = _parse_slot_color(slot.get("text_color"), ink_black)
                h_align = _resolve_slot_align(slot.get("align", slot.get("justification")), "left")
                lines = _wrap_text_to_width(draw, text_str, h_font, rw)
                cy = ry
                for line in lines[:3]:
                    if h_align == "center":
                        lb = draw.textbbox((0, 0), line, font=h_font)
                        lw = lb[2] - lb[0]
                        lx = rx + max(0, (rw - lw) // 2)
                    elif h_align == "right":
                        lb = draw.textbbox((0, 0), line, font=h_font)
                        lw = lb[2] - lb[0]
                        lx = rx + max(0, rw - lw)
                    else:
                        lx = rx
                    _draw_text_with_symbols(draw, (lx, cy), line, font=h_font, fill=h_color)
                    cy += font_size + S(4)

            elif stype == "photo":
                img_path = (
                    target_story.image_path
                    if target_story.image_path and os.path.exists(target_story.image_path)
                    else None
                )
                if img_path:
                    try:
                        mtime = os.path.getmtime(img_path)
                        pkey = (img_path, rw, rh, mtime)
                        if pkey not in self._photo_cache:
                            with Image.open(img_path) as p_img:
                                self._photo_cache[pkey] = p_img.resize((rw, rh), Image.Resampling.LANCZOS).convert(
                                    "RGBA"
                                )
                        p_resized = self._photo_cache[pkey]
                        canvas.paste(p_resized, (rx, ry), p_resized)
                        draw.rectangle([rx, ry, rx + rw, ry + rh], outline=border_ink, width=S(2))
                    except Exception:
                        draw.rectangle([rx, ry, rx + rw, ry + rh], outline=border_ink, width=S(1))
                else:
                    draw.rectangle([rx, ry, rx + rw, ry + rh], outline=border_ink, width=S(1))

            elif stype in ["body", "column"]:
                if not target_story or not target_story.body.strip():
                    continue
                paras = [p.strip() for p in target_story.body.split("\n\n") if p.strip()]
                b_font_type = _resolve_slot_font(slot.get("font_family"), "body")
                b_size = _resolve_slot_font_size(slot.get("font_size"), S(9.5), scale)
                b_font = self.fonts.get_font(b_font_type, b_size)
                b_bold = self.fonts.get_font("headline", b_size)
                d_font = self.fonts.get_font("headline", max(S(18), int(b_size * 2.8)))
                b_color = _parse_slot_color(slot.get("text_color"), ink_black)
                line_height = int(b_size * 1.35)
                b_align = _resolve_slot_align(slot.get("align", slot.get("justification")), "justify")
                _draw_story_paragraphs(
                    draw=draw,
                    paragraphs=paras,
                    font=b_font,
                    font_bold=b_bold,
                    drop_font=d_font,
                    x=rx,
                    y=ry,
                    max_w=rw,
                    max_h=rh,
                    line_h=line_height,
                    fill=b_color,
                    has_drop_cap=True,
                    align=b_align,
                )

            elif stype == "quote":
                q_text = f'"{edition.quote_text}"'
                q_font_type = _resolve_slot_font(slot.get("font_family"), "body_italic")
                q_size = _resolve_slot_font_size(slot.get("font_size"), S(10), scale)
                q_font = self.fonts.get_font(q_font_type, q_size)
                q_color = _parse_slot_color(slot.get("text_color"), ink_dark)
                q_align = _resolve_slot_align(slot.get("align", slot.get("justification")), "left")
                draw.rectangle([rx, ry, rx + rw, ry + rh], fill=(238, 226, 202, 160), outline=border_ink, width=S(1))
                qlines = _wrap_text_to_width(draw, q_text, q_font, rw - S(16))
                qy = ry + max(0, (rh - len(qlines) * (q_size + S(4))) // 2)
                for ql in qlines[:4]:
                    if q_align == "center":
                        qb = draw.textbbox((0, 0), ql, font=q_font)
                        qw = qb[2] - qb[0]
                        qx = rx + max(S(8), (rw - qw) // 2)
                    elif q_align == "right":
                        qb = draw.textbbox((0, 0), ql, font=q_font)
                        qw = qb[2] - qb[0]
                        qx = rx + max(S(8), rw - qw - S(8))
                    else:
                        qx = rx + S(8)
                    _draw_text_with_symbols(draw, (qx, qy), ql, font=q_font, fill=q_color)
                    qy += q_size + S(4)
                if edition.quote_author:
                    _draw_text_with_symbols(
                        draw,
                        (rx + S(8), qy + S(4)),
                        f"— {edition.quote_author.upper()}",
                        font=self.fonts.get_font("headline", S(8.5)),
                        fill=ink_dark,
                    )

            elif stype == "lore":
                ltitle, lbody = lore_items[lore_cursor % len(lore_items)]
                lore_cursor += 1
                draw.text((rx, ry), ltitle.upper(), font=self.fonts.get_font("headline", S(10)), fill=ink_black)
                draw.line([rx, ry + S(14), rx + rw, ry + S(14)], fill=border_ink, width=S(1))
                _draw_story_paragraphs(
                    draw=draw,
                    paragraphs=[lbody],
                    font=self.fonts.get_font("body", S(9)),
                    font_bold=self.fonts.get_font("headline", S(9)),
                    drop_font=self.fonts.get_font("headline", S(24)),
                    x=rx,
                    y=ry + S(18),
                    max_w=rw,
                    max_h=rh - S(20),
                    line_h=S(12),
                    fill=ink_black,
                    has_drop_cap=False,
                )

            elif stype == "footer":
                draw.line([rx, ry, rx + rw, ry], fill=border_ink, width=S(1))
                f_font = self.fonts.get_font("headline", S(8.5))
                f_text = f"❖ ─── ✦ {edition.footer_slogan} ✦ ─── ❖"
                fb = draw.textbbox((0, 0), f_text, font=f_font)
                fw = fb[2] - fb[0]
                draw.text((rx + (rw - fw) // 2, ry + S(4)), f_text, font=f_font, fill=ink_dark)

        return canvas

    def render_multipage(
        self, edition: NewspaperEdition, template_ids: List[str], scale: float = 1.0
    ) -> List[Image.Image]:
        """Renders a sequence of layout templates as a multi-page publication."""
        pages = []
        for tid in template_ids:
            pages.append(self.render_template(edition, template_id=tid, scale=scale))
        return pages


def export_native_image(
    edition: NewspaperEdition, output_path: str, template_id: str = "layout_1", scale: float = 2.0
) -> Tuple[bool, str]:
    """Renders and exports the newspaper layout to high-resolution PNG or JPG."""
    try:
        renderer = NativeBroadsheetRenderer()
        img = renderer.render_template(edition, template_id=template_id, scale=scale)
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        ext = os.path.splitext(abs_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            rgb = img.convert("RGB")
            rgb.save(abs_path, "JPEG", quality=95)
        else:
            img.save(abs_path, "PNG", optimize=True)

        return True, f"Successfully exported publication to: {abs_path}"
    except Exception as e:
        return False, f"Image export failed: {str(e)}"


def export_native_pdf(
    edition: NewspaperEdition, output_path: str, template_ids: str | List[str] = "layout_1", scale: float = 2.0
) -> Tuple[bool, str]:
    """Renders and exports the newspaper layout directly to a high-resolution borderless PDF."""
    try:
        renderer = NativeBroadsheetRenderer()
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        if isinstance(template_ids, str):
            template_ids = [template_ids]

        rendered_pages = [renderer.render_template(edition, tid, scale=scale).convert("RGB") for tid in template_ids]

        if not rendered_pages:
            return False, "No pages to export."

        if len(rendered_pages) == 1:
            rendered_pages[0].save(abs_path, "PDF", resolution=150.0 * scale)
        else:
            rendered_pages[0].save(
                abs_path, "PDF", resolution=150.0 * scale, save_all=True, append_images=rendered_pages[1:]
            )

        return True, f"Successfully exported {len(rendered_pages)}-page publication to: {abs_path}"
    except Exception as e:
        return False, f"PDF export failed: {str(e)}"
