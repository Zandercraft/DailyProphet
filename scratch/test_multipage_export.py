"""Test rendering all 9 Additional Layouts into a single 9-page PDF and individual PNGs."""

import os
import json
from typing import Dict, Any
from PIL import Image, ImageDraw
from daily_prophet.models import NewspaperEdition, Story, StoryPriority
from daily_prophet.sample_data import get_original_hogwarts_edition
from daily_prophet.native_renderer import BroadsheetFontManager, _wrap_text_to_width, _draw_story_paragraphs


def render_layout_slots(
    edition: NewspaperEdition,
    layout_id: str,
    layout_def: Dict[str, Any],
    font_mgr: BroadsheetFontManager,
    scale: float = 1.0,
) -> Image.Image:
    page_file = layout_def["page_file"]
    assert os.path.exists(page_file), f"Template page file not found: {page_file}"

    base_w = layout_def.get("width", 1024)
    base_h = layout_def.get("height", 1400)
    target_w = int(base_w * scale)
    target_h = int(base_h * scale)

    with Image.open(page_file) as p_img:
        canvas = p_img.resize((target_w, target_h), Image.Resampling.LANCZOS).convert("RGBA")

    draw = ImageDraw.Draw(canvas)

    ink_black = (18, 14, 10)
    ink_dark = (42, 34, 26)
    ink_muted = (92, 78, 64)
    border_ink = (32, 24, 18)
    accent_red = (110, 24, 24)

    def S(v: int) -> int:
        return int(v * scale)

    # Pool of stories to assign across slots
    cover_stories = [s for s in edition.stories if s.priority == StoryPriority.COVER.value]
    major_stories = [s for s in edition.stories if s.priority == StoryPriority.MAJOR.value]

    cover = (
        cover_stories[0]
        if cover_stories
        else (edition.stories[0] if edition.stories else Story(headline="HOGWARTS NEWS"))
    )
    major = major_stories[0] if major_stories else (edition.stories[1] if len(edition.stories) > 1 else cover)
    other_stories = [s for s in edition.stories if s != cover and s != major]
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
            # "The DAILY PROPHET"
            t_font_sz = min(S(48), int(rh * 0.7))
            t_font = font_mgr.get_font("title", t_font_sz)
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
                # Date / Day
                draw.text(
                    (rx + S(6), ry + S(4)),
                    edition.edition_day.upper(),
                    font=font_mgr.get_font("headline", S(9)),
                    fill=ink_black,
                )
                draw.text(
                    (rx + S(6), ry + S(18)),
                    edition.edition_date.upper(),
                    font=font_mgr.get_font("subhead", S(10)),
                    fill=ink_black,
                )
                draw.line([rx + S(6), ry + S(34), rx + rw - S(6), ry + S(34)], fill=border_ink, width=S(1))
                draw.text(
                    (rx + S(6), ry + S(38)),
                    edition.issue_number.upper(),
                    font=font_mgr.get_font("headline", S(8)),
                    fill=ink_muted,
                )
            else:
                # Price / Weather
                draw.text(
                    (rx + S(6), ry + S(4)),
                    "PRICE: " + edition.price.upper(),
                    font=font_mgr.get_font("headline", S(9)),
                    fill=accent_red,
                )
                draw.text(
                    (rx + S(6), ry + S(18)), "CASTLE WEATHER", font=font_mgr.get_font("headline", S(8)), fill=ink_black
                )
                draw.line([rx + S(6), ry + S(30), rx + rw - S(6), ry + S(30)], fill=border_ink, width=S(1))
                draw.text(
                    (rx + S(6), ry + S(35)),
                    edition.weather[:24],
                    font=font_mgr.get_font("body_italic", S(8)),
                    fill=ink_dark,
                )

        elif stype == "slogan":
            s_font = font_mgr.get_font("headline", min(S(10), int(rh * 0.45)))
            s_text = f"✦ {edition.tagline} ✦"
            sb = draw.textbbox((0, 0), s_text, font=s_font)
            sw = sb[2] - sb[0]
            draw.text((rx + (rw - sw) // 2, ry + S(3)), s_text, font=s_font, fill=ink_dark)

        elif stype in ["ticker", "banner"]:
            draw.line([rx, ry, rx + rw, ry], fill=border_ink, width=S(1))
            draw.line([rx, ry + rh, rx + rw, ry + rh], fill=border_ink, width=S(1))
            tk_font = font_mgr.get_font("headline", min(S(9), int(rh * 0.4)))
            tk_text = edition.topic_bar if stype == "ticker" else f"❖ {edition.tagline.upper()} ❖"
            tk_bbox = draw.textbbox((0, 0), tk_text, font=tk_font)
            tkw = tk_bbox[2] - tk_bbox[0]
            draw.text((rx + max(0, (rw - tkw) // 2), ry + S(4)), tk_text, font=tk_font, fill=ink_black)

        elif stype in ["headline", "subheadline"]:
            # Pick matching story
            target_story = (
                cover
                if "lead" in sid or "main" in sid or "hero" in sid
                else (major if "feature" in sid or "top" in sid else other_stories[story_cursor % len(other_stories)])
            )
            text_str = (
                target_story.headline.upper()
                if stype == "headline"
                else (target_story.subheadline or target_story.headline)
            )
            font_type = "headline" if stype == "headline" else "subhead_italic"
            font_size = min(S(20), max(S(10), int(rh * 0.45)))
            h_font = font_mgr.get_font(font_type, font_size)
            lines = _wrap_text_to_width(draw, text_str, h_font, rw)
            cy = ry
            for line in lines[:3]:
                draw.text((rx, cy), line, font=h_font, fill=ink_black)
                cy += font_size + S(4)

        elif stype == "photo":
            # Assign appropriate image
            target_story = (
                cover
                if "lead" in sid or "hero" in sid or "top" in sid
                else (major if "feature" in sid else other_stories[story_cursor % len(other_stories)])
            )
            img_path = (
                target_story.image_path if target_story.image_path and os.path.exists(target_story.image_path) else None
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
            target_story = cover if "lead" in sid or "hero" in sid else other_stories[story_cursor % len(other_stories)]
            if stype == "column":
                story_cursor += 1
            paras = [p.strip() for p in target_story.body.split("\n\n") if p.strip()]
            b_font = font_mgr.get_font("body", S(9.5))
            b_bold = font_mgr.get_font("headline", S(9.5))
            d_font = font_mgr.get_font("headline", S(28))
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
            q_font = font_mgr.get_font("body_italic", S(10))
            draw.rectangle([rx, ry, rx + rw, ry + rh], fill=(238, 226, 202, 160), outline=border_ink, width=S(1))
            qlines = _wrap_text_to_width(draw, q_text, q_font, rw - S(16))
            qy = ry + S(8)
            for ql in qlines:
                draw.text((rx + S(8), qy), ql, font=q_font, fill=accent_red)
                qy += S(14)
            draw.text(
                (rx + S(8), qy + S(4)),
                f"— {edition.quote_author.upper()}",
                font=font_mgr.get_font("headline", S(8.5)),
                fill=ink_dark,
            )

        elif stype == "lore":
            ltitle, lbody = lore_items[lore_cursor % len(lore_items)]
            lore_cursor += 1
            draw.text((rx, ry), ltitle.upper(), font=font_mgr.get_font("headline", S(10)), fill=ink_black)
            draw.line([rx, ry + S(14), rx + rw, ry + S(14)], fill=border_ink, width=S(1))
            _draw_story_paragraphs(
                draw=draw,
                paragraphs=[lbody],
                font=font_mgr.get_font("body", S(9)),
                font_bold=font_mgr.get_font("headline", S(9)),
                drop_font=font_mgr.get_font("headline", S(24)),
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
            f_font = font_mgr.get_font("headline", S(8.5))
            f_text = f"❖ ─── ✦ {edition.footer_slogan} ✦ ─── ❖"
            fb = draw.textbbox((0, 0), f_text, font=f_font)
            fw = fb[2] - fb[0]
            draw.text((rx + (rw - fw) // 2, ry + S(4)), f_text, font=f_font, fill=ink_dark)

    return canvas


def main():
    edition = get_original_hogwarts_edition(".")
    font_mgr = BroadsheetFontManager(".")
    with open("assets/templates/layout_definitions.json") as f:
        layouts = json.load(f)

    rendered_pages = []
    os.makedirs("output/additional_layouts", exist_ok=True)

    for i in range(1, 10):
        layout_key = f"additional_layout_{i}"
        if layout_key in layouts:
            print(f"Rendering {layout_key}...")
            img = render_layout_slots(edition, layout_key, layouts[layout_key], font_mgr, scale=1.5)
            png_out = f"output/additional_layouts/{layout_key}.png"
            img.save(png_out, "PNG", optimize=True)
            print(f"  -> Saved PNG: {png_out}")
            rendered_pages.append(img.convert("RGB"))

    # Also export all 9 pages into a single multi-page PDF!
    multi_pdf_path = "output/additional_layouts/Vintage_Wizarding_Gazette_9Pages.pdf"
    rendered_pages[0].save(
        multi_pdf_path, "PDF", resolution=150.0 * 1.5, save_all=True, append_images=rendered_pages[1:]
    )
    print(f"\nSuccessfully generated 9-page PDF: {multi_pdf_path} (Pages: {len(rendered_pages)})")


if __name__ == "__main__":
    main()
