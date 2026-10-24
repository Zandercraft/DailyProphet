"""Test rendering an edition onto Additional Layout 1 and generating a sample PDF and PNG."""
import os
import json
from PIL import Image, ImageDraw, ImageFont
from daily_prophet.sample_data import get_original_hogwarts_edition

def test_slot_render():
    edition = get_original_hogwarts_edition(".")
    with open("assets/templates/layout_definitions.json") as f:
        layouts = json.load(f)

    layout = layouts.get("additional_layout_1")
    assert layout is not None, "additional_layout_1 not found"

    page_file = layout["page_file"]
    base_img = Image.open(page_file).convert("RGBA")
    w, h = base_img.size
    print(f"Loaded {page_file} ({w}x{h})")

    # Render on 1.0 scale
    draw = ImageDraw.Draw(base_img)

    # Ink colors
    ink_black = (18, 14, 10)
    ink_dark = (42, 34, 26)
    ink_muted = (92, 78, 64)
    accent_red = (110, 24, 24)

    # Font helper
    def get_font(name, sz):
        fmap = {
            "title": "assets/fonts/UnifrakturMaguntia-Regular.ttf",
            "headline": "assets/fonts/Cinzel.ttf",
            "subhead": "assets/fonts/PlayfairDisplay.ttf",
            "body": "assets/fonts/IMFellEnglish-Regular.ttf",
            "italic": "assets/fonts/PlayfairDisplay-Italic.ttf"
        }
        fp = fmap.get(name, fmap["body"])
        if os.path.exists(fp):
            return ImageFont.truetype(fp, sz)
        return ImageFont.load_default()

    # Draw Title
    title_font = get_font("title", 52)
    draw.text((w // 2 - 200, 42), "DAILY PROPHET", font=title_font, fill=ink_black)

    # Draw Lead Headline
    lead_story = edition.stories[0]
    head_font = get_font("headline", 24)
    draw.text((45, 230), lead_story.headline.upper()[:55], font=head_font, fill=ink_black)

    # Draw Lead Image
    if lead_story.image_path and os.path.exists(lead_story.image_path):
        with Image.open(lead_story.image_path) as limg:
            l_resized = limg.resize((455, 275), Image.Resampling.LANCZOS).convert("RGBA")
            base_img.paste(l_resized, (290, 285))
            draw.rectangle([290, 285, 290 + 455, 285 + 275], outline=(30, 20, 15), width=2)

    os.makedirs("output/test", exist_ok=True)
    out_png = "output/test/additional_layout_1_test.png"
    base_img.convert("RGB").save(out_png)
    print(f"Saved test render to: {out_png}")

if __name__ == "__main__":
    test_slot_render()
