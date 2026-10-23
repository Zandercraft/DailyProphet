"""Defines layout slot schemas, persistence, and visual wireframe mask generation.
Exclusively supports authentic Vintage Wizarding Newspaper Layouts.
"""
import os
import shutil
import json
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from .template_package import (
    load_all_installed_templates,
    save_installed_template,
    restore_template_from_shipped_or_backup,
    delete_installed_template,
    INSTALLED_TEMPLATES_DIR,
    SHIPPED_TEMPLATES_DIR
)

SHIPPED_DEFAULTS_FILE = os.path.join(os.path.dirname(__file__), "default_templates", "layout_definitions.json")
GLOBAL_LAYOUTS_FILE = os.path.join("assets", "templates", "layout_definitions.json")
GLOBAL_BACKUP_FILE = os.path.join("assets", "templates", "layout_definitions.json.bak")
MASKS_DIR = os.path.join("assets", "templates", "masks")

SLOT_COLORS = {
    'title': (74, 35, 90, 160),         # Royal Purple
    'banner': (40, 40, 60, 140),       # Dark Slate
    'ear_box': (100, 40, 40, 140),     # Dark Maroon
    'slogan': (50, 50, 50, 120),       # Charcoal
    'ticker': (90, 70, 30, 130),       # Bronze
    'headline': (139, 30, 30, 170),     # Crimson Red
    'subheadline': (160, 60, 40, 130),  # Amber
    'photo': (30, 86, 49, 180),        # Forest Green
    'body': (27, 54, 93, 140),         # Ink Navy
    'column': (27, 54, 93, 130),       # Column Blue
    'quote': (153, 101, 21, 160),      # Amber Gold
    'lore': (92, 53, 102, 140),        # Plum
    'divider': (80, 80, 80, 140),      # Divider
    'footer': (40, 40, 40, 150)        # Footer
}

OUTLINE_COLORS = {
    'title': (120, 60, 150),
    'banner': (80, 80, 120),
    'ear_box': (160, 60, 60),
    'slogan': (100, 100, 100),
    'ticker': (140, 110, 50),
    'headline': (190, 40, 40),
    'subheadline': (210, 90, 60),
    'photo': (40, 140, 80),
    'body': (45, 90, 155),
    'column': (45, 90, 155),
    'quote': (210, 145, 30),
    'lore': (140, 80, 160),
    'divider': (120, 120, 120),
    'footer': (90, 90, 90)
}


def load_layout_definitions(defs_path: Optional[str] = None, base_dir: str = ".") -> Dict[str, Any]:
    """Loads layout definitions from individual .prophettemplate files or legacy fallback."""
    # First priority: Load individual .prophettemplate files from installed / shipped directories
    pkg_templates = load_all_installed_templates(base_dir=base_dir)
    if pkg_templates:
        # Also ensure layout_definitions.json is synchronized for compatibility
        target_path = defs_path or os.path.join(base_dir, GLOBAL_LAYOUTS_FILE)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(pkg_templates, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return pkg_templates

    target_path = defs_path or os.path.join(base_dir, GLOBAL_LAYOUTS_FILE)

    if os.path.isfile(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {target_path} ({e}). Falling back to shipped defaults.")

    # Try shipped defaults bundled in source code
    if os.path.isfile(SHIPPED_DEFAULTS_FILE):
        try:
            with open(SHIPPED_DEFAULTS_FILE, "r", encoding="utf-8") as f:
                defaults = json.load(f)
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(defaults, f, indent=2)
            return defaults
        except Exception as e:
            print(f"Error loading shipped defaults from {SHIPPED_DEFAULTS_FILE}: {e}")

    return {}


def save_global_layout_definitions(layouts: Dict[str, Any], defs_path: Optional[str] = None, base_dir: str = ".") -> bool:
    """Saves layout definitions to individual .prophettemplate files (one layout per file).
    Creates a .bak backup file for each modified template upon first edit.
    """
    target_path = defs_path or os.path.join(base_dir, GLOBAL_LAYOUTS_FILE)
    backup_path = target_path + ".bak"

    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    # First-time backup of composite json:
    if os.path.isfile(target_path) and not os.path.isfile(backup_path):
        try:
            shutil.copy2(target_path, backup_path)
            print(f"Created first-modification template backup: {backup_path}")
        except Exception as e:
            print(f"Warning: Could not create template backup: {e}")

    # Save each individual template to its own .prophettemplate file
    for layout_key, layout_data in layouts.items():
        if layout_key.startswith("additional_"):
            continue
        try:
            save_installed_template(layout_key, layout_data, base_dir=base_dir)
        except Exception as e:
            print(f"Error packaging {layout_key}.prophettemplate: {e}")

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(layouts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving global layouts to {target_path}: {e}")
        return False


def restore_factory_templates(defs_path: Optional[str] = None, base_dir: str = ".") -> Dict[str, Any]:
    """Restores global template definitions from bundled source code .prophettemplate files."""
    for i in range(1, 10):
        restore_template_from_shipped_or_backup(f"layout_{i}", base_dir=base_dir)

    return load_all_installed_templates(base_dir=base_dir)


def generate_wireframe_mask_for_layout(
    layout_key: str,
    layout_data: Dict[str, Any],
    masks_dir: Optional[str] = None,
    base_dir: str = "."
) -> Optional[str]:
    """Generates a high-contrast wireframe mask with slot labels for a specific layout."""
    masks_target_dir = masks_dir or os.path.join(base_dir, MASKS_DIR)
    os.makedirs(masks_target_dir, exist_ok=True)

    page_rel = layout_data.get('page_file', '')
    page_file = os.path.join(base_dir, page_rel) if not os.path.isabs(page_rel) else page_rel

    if not os.path.isfile(page_file):
        # Try alternate path
        page_file = os.path.abspath(page_rel)

    if not os.path.isfile(page_file):
        print(f"Skipping wireframe for {layout_key}: Page image '{page_rel}' not found.")
        return None

    try:
        base_img = Image.open(page_file).convert('RGBA')
    except Exception as e:
        print(f"Failed to open page image for {layout_key}: {e}")
        return None

    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_path = r"C:\Windows\Fonts\arialbd.ttf"
    if not os.path.isfile(font_path):
        font_path = r"C:\Windows\Fonts\arial.ttf"

    font_size = max(9, int(base_img.width * 0.016))
    try:
        label_font = ImageFont.truetype(font_path, font_size)
    except Exception:
        label_font = ImageFont.load_default()

    slots = layout_data.get('slots', [])
    for slot in slots:
        rx, ry, rw, rh = slot.get('rect', [0, 0, 100, 100])
        stype = slot.get('type', 'body')
        slabel = slot.get('label', slot.get('id', 'slot'))

        fill_c = SLOT_COLORS.get(stype, (40, 40, 40, 120))
        line_c = OUTLINE_COLORS.get(stype, (100, 100, 100))

        draw.rectangle([rx, ry, rx + rw, ry + rh], fill=fill_c, outline=line_c, width=2)

        tag_text = f"[{stype.upper()}] {slabel}"
        t_bbox = draw.textbbox((0, 0), tag_text, font=label_font)
        t_w = t_bbox[2] - t_bbox[0]
        t_h = t_bbox[3] - t_bbox[1]

        tag_y = min(ry + 3, ry + rh - t_h - 4)
        draw.rectangle([rx + 2, tag_y - 1, rx + t_w + 6, tag_y + t_h + 3], fill=(20, 20, 20, 220))
        draw.text((rx + 4, tag_y), tag_text, font=label_font, fill=(255, 255, 255))

    composite = Image.alpha_composite(base_img, overlay).convert('RGB')
    mask_out = os.path.join(masks_target_dir, f"{layout_key}_wireframe.png")
    composite.save(mask_out)

    # Save alias mask for compatibility if needed
    if not layout_key.startswith("additional_"):
        alias_out = os.path.join(masks_target_dir, f"additional_{layout_key}_wireframe.png")
        try:
            composite.save(alias_out)
        except Exception:
            pass

    return mask_out


def build_all_layouts(defs_path: Optional[str] = None, base_dir: str = "."):
    """Reads layout definitions from disk and generates wireframe masks without overwriting definitions."""
    layouts = load_layout_definitions(defs_path=defs_path, base_dir=base_dir)
    masks_target_dir = os.path.join(base_dir, MASKS_DIR)
    os.makedirs(masks_target_dir, exist_ok=True)

    generated = 0
    for layout_key, layout_data in layouts.items():
        if layout_key.startswith("additional_layout_"):
            continue  # Generated as alias along with primary
        mask_path = generate_wireframe_mask_for_layout(layout_key, layout_data, masks_dir=masks_target_dir, base_dir=base_dir)
        if mask_path:
            generated += 1

    print(f"Generated {generated} wireframe masks in {masks_target_dir}")


if __name__ == '__main__':
    build_all_layouts()
