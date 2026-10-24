"""Native Broadsheet Renderer for The Daily Prophet.

Renders authentic, high-resolution Harry Potter broadsheet newspapers directly onto vintage wizarding parchment templates.
Supports borderless PDF and high-res PNG/JPEG exports.
"""

import os
from typing import List, Tuple, Optional
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


def _wrap_text_to_width(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> List[str]:
    """Wraps text so each line fits within max_width pixels."""
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _draw_justified_line(
    draw: ImageDraw.ImageDraw,
    line: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
    fill: Tuple[int, int, int],
):
    """Draws a single line of text with inter-word justification."""
    words = line.split()
    if len(words) <= 1:
        draw.text((x, y), line, font=font, fill=fill)
        return

    # Total width of all words without spaces
    total_words_w = sum(draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0] for w in words)
    space_to_distribute = max_width - total_words_w
    if space_to_distribute <= 0:
        draw.text((x, y), line, font=font, fill=fill)
        return

    space_per_gap = space_to_distribute / (len(words) - 1)
    cur_x = float(x)
    for word in words:
        draw.text((round(cur_x), y), word, font=font, fill=fill)
        w_w = draw.textbbox((0, 0), word, font=font)[2] - draw.textbbox((0, 0), word, font=font)[0]
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
) -> int:
    """Draws justified paragraphs, wrapping around an avoid_rect (inline photo or cutout)."""
    cur_y = y
    first_para = True

    for p_idx, para in enumerate(paragraphs):
        clean = para.strip()
        if not clean:
            continue

        words = clean.split()
        if not words:
            continue

        indent = 0 if (first_para and has_drop_cap) else (14 if not first_para else 0)

        # Handle drop-cap on first paragraph
        if first_para and has_drop_cap and len(words[0]) > 0:
            drop_char = words[0][0]
            words[0] = words[0][1:]
            drop_bbox = draw.textbbox((0, 0), drop_char, font=drop_font)
            drop_w = drop_bbox[2] - drop_bbox[0] + 6
            draw.text((x, cur_y - 2), drop_char, font=drop_font, fill=fill)
            indent = drop_w

        current_line_words = []
        is_first_line_of_para = True

        for word in words:
            test_words = current_line_words + [word]
            test_line = " ".join(test_words)

            # Determine position and available width based on avoid_rect
            base_x = x + (indent if is_first_line_of_para else 0)
            avail_x = base_x
            avail_w = max_w - (indent if is_first_line_of_para else 0)

            if avoid_rect:
                ax, ay, aw, ah = avoid_rect
                if ay <= cur_y < ay + ah:
                    if ax <= x + 20:
                        # Image is on the left
                        avail_x = ax + aw + 10
                        avail_w = (x + max_w) - avail_x
                    else:
                        # Image is on the right
                        avail_w = max(40, ax - avail_x - 10)

            line_bbox = draw.textbbox((0, 0), test_line, font=font)
            line_w = line_bbox[2] - line_bbox[0]

            if line_w <= avail_w or not current_line_words:
                current_line_words.append(word)
            else:
                if cur_y + line_h > y + max_h:
                    return cur_y
                line_str = " ".join(current_line_words)
                _draw_justified_line(draw, line_str, font, avail_x, cur_y, avail_w, fill)
                cur_y += line_h
                current_line_words = [word]
                is_first_line_of_para = False
                if first_para and has_drop_cap:
                    indent = 0

        if current_line_words:
            if cur_y + line_h > y + max_h:
                return cur_y
            base_x = x + (indent if is_first_line_of_para else 0)
            avail_x = base_x
            avail_w = max_w - (indent if is_first_line_of_para else 0)
            if avoid_rect:
                ax, ay, aw, ah = avoid_rect
                if ay <= cur_y < ay + ah:
                    if ax <= x + 20:
                        avail_x = ax + aw + 10
                        avail_w = (x + max_w) - avail_x
                    else:
                        avail_w = max(40, ax - avail_x - 10)

            draw.text((avail_x, cur_y), " ".join(current_line_words), font=font, fill=fill)
            cur_y += line_h + 4

        first_para = False

    return cur_y


class NativeBroadsheetRenderer:
    """Composites an authentic, print-ready Harry Potter broadsheet newspaper."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        self.fonts = BroadsheetFontManager(self.base_dir)

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

        if os.path.exists(page_abs):
            with Image.open(page_abs) as p_img:
                canvas = p_img.resize((target_w, target_h), Image.Resampling.LANCZOS).convert("RGBA")
        else:
            canvas = Image.new("RGBA", (target_w, target_h), (226, 212, 178, 255))

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

        cover_stories = [s for s in page_stories if s.priority == StoryPriority.COVER.value]
        major_stories = [s for s in page_stories if s.priority == StoryPriority.MAJOR.value]

        cover = (
            cover_stories[0]
            if cover_stories
            else (page_stories[0] if page_stories else Story(headline="HOGWARTS NEWS"))
        )
        major = major_stories[0] if major_stories else (page_stories[1] if len(page_stories) > 1 else cover)
        other_stories = [s for s in page_stories if s != cover and s != major]
        if not other_stories:
            other_stories = [cover, major]

        story_cursor = 0
        lore_cursor = 0
        lore_items = [
            (edition.lore_title_1, edition.lore_body_1),
            (edition.lore_title_2, edition.lore_body_2),
            ("WORDS OF WISDOM", f'"{edition.quote_text}" — {edition.quote_author}'),
        ]

        for slot in layout_def.get("slots", []):
            sid = slot.get("id", "")
            stype = slot.get("type", "body")
            rx, ry, rw, rh = [S(v) for v in slot["rect"]]

            if stype == "title":
                t_font_sz = min(S(48), max(S(18), int(rh * 0.7)))
                t_font = self.fonts.get_font("title", t_font_sz)
                txt = "DAILY PROPHET"
                t_bbox = draw.textbbox((0, 0), txt, font=t_font)
                tw = t_bbox[2] - t_bbox[0]
                th = t_bbox[3] - t_bbox[1]
                tx = rx + max(0, (rw - tw) // 2)
                ty = ry + max(0, (rh - th) // 2)
                draw.text((tx, ty), txt, font=t_font, fill=ink_black)

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
                s_font = self.fonts.get_font("headline", min(S(10), max(S(7), int(rh * 0.45))))
                s_text = f"✦ {edition.tagline} ✦"
                sb = draw.textbbox((0, 0), s_text, font=s_font)
                sw = sb[2] - sb[0]
                draw.text((rx + (rw - sw) // 2, ry + S(3)), s_text, font=s_font, fill=ink_dark)

            elif stype in ["ticker", "banner"]:
                draw.line([rx, ry, rx + rw, ry], fill=border_ink, width=S(1))
                draw.line([rx, ry + rh, rx + rw, ry + rh], fill=border_ink, width=S(1))
                tk_font = self.fonts.get_font("headline", min(S(9), max(S(7), int(rh * 0.4))))
                tk_text = edition.topic_bar if stype == "ticker" else f"❖ {edition.tagline.upper()} ❖"
                tk_bbox = draw.textbbox((0, 0), tk_text, font=tk_font)
                tkw = tk_bbox[2] - tk_bbox[0]
                draw.text((rx + max(0, (rw - tkw) // 2), ry + S(4)), tk_text, font=tk_font, fill=ink_black)

            elif stype in ["headline", "subheadline"]:
                target_story = (
                    cover
                    if "lead" in sid or "main" in sid or "hero" in sid
                    else (
                        major if "feature" in sid or "top" in sid else other_stories[story_cursor % len(other_stories)]
                    )
                )
                text_str = (
                    target_story.headline.upper()
                    if stype == "headline"
                    else (target_story.subheadline or target_story.headline)
                )
                font_type = "headline" if stype == "headline" else "subhead_italic"
                font_size = min(S(20), max(S(10), int(rh * 0.42)))
                h_font = self.fonts.get_font(font_type, font_size)
                lines = _wrap_text_to_width(draw, text_str, h_font, rw)
                cy = ry
                for line in lines[:3]:
                    draw.text((rx, cy), line, font=h_font, fill=ink_black)
                    cy += font_size + S(4)

            elif stype == "photo":
                target_story = (
                    cover
                    if "lead" in sid or "hero" in sid or "top" in sid
                    else (major if "feature" in sid else other_stories[story_cursor % len(other_stories)])
                )
                img_path = (
                    target_story.image_path
                    if target_story.image_path and os.path.exists(target_story.image_path)
                    else None
                )
                if img_path:
                    try:
                        with Image.open(img_path) as p_img:
                            p_resized = p_img.resize((rw, rh), Image.Resampling.LANCZOS).convert("RGBA")
                            canvas.paste(p_resized, (rx, ry), p_resized)
                            draw.rectangle([rx, ry, rx + rw, ry + rh], outline=border_ink, width=S(2))
                    except Exception:
                        pass
                else:
                    draw.rectangle([rx, ry, rx + rw, ry + rh], outline=border_ink, width=S(1))

            elif stype in ["body", "column"]:
                target_story = (
                    cover if "lead" in sid or "hero" in sid else other_stories[story_cursor % len(other_stories)]
                )
                if stype == "column":
                    story_cursor += 1
                paras = [p.strip() for p in target_story.body.split("\n\n") if p.strip()]
                b_font = self.fonts.get_font("body", S(9.5))
                b_bold = self.fonts.get_font("headline", S(9.5))
                d_font = self.fonts.get_font("headline", S(28))
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
                    line_h=S(13),
                    fill=ink_black,
                    has_drop_cap=True,
                )

            elif stype == "quote":
                q_text = f'"{edition.quote_text}"'
                q_font = self.fonts.get_font("body_italic", S(10))
                draw.rectangle([rx, ry, rx + rw, ry + rh], fill=(238, 226, 202, 160), outline=border_ink, width=S(1))
                qlines = _wrap_text_to_width(draw, q_text, q_font, rw - S(16))
                qy = ry + S(8)
                for ql in qlines:
                    draw.text((rx + S(8), qy), ql, font=q_font, fill=accent_red)
                    qy += S(14)
                draw.text(
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
