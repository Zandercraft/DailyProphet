"""Manages individual .prophettemplate package files.

Each .prophettemplate is a self-contained archive (ZIP) containing:
- manifest.json: Metadata about the template (ID, name, dimensions, version)
- template.json: Slot bounding boxes, labels, and content types
- page.png: High-resolution authentic background parchment artwork
- wireframe.png: Visual wireframe mask of all content slots
"""

import os
import shutil
import json
import zipfile
from typing import Dict, Optional
from .versioning import FormatVersion, CURRENT_TEMPLATE_VERSION, template_migration_pipeline
from .layout_models import LayoutDefinition

SHIPPED_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "default_templates")
INSTALLED_TEMPLATES_DIR = os.path.join("assets", "templates", "installed")
TEMPLATES_CACHE_DIR = os.path.join("assets", "templates", "cache")

BUILTIN_SHIPPED_LAYOUTS = [f"layout_{i}" for i in range(1, 10)]


def is_layout_modified(edition_layout: Optional[Dict[str, object]], local_layout: Optional[Dict[str, object]]) -> bool:
    """Compares an issue-bundled layout against an installed local template.
    Returns True if the issue layout has slot, rectangle, or property modifications.
    """
    if not edition_layout or not local_layout:
        return False
    e_def = LayoutDefinition.from_dict(edition_layout) if isinstance(edition_layout, dict) else edition_layout
    l_def = LayoutDefinition.from_dict(local_layout) if isinstance(local_layout, dict) else local_layout
    return e_def.is_modified_from(l_def)


def create_template_package(
    layout_id: str,
    layout_data: Dict[str, object],
    output_path: str,
    target_version: str = CURRENT_TEMPLATE_VERSION,
    is_bundled: Optional[bool] = None,
    base_dir: str = ".",
) -> str:
    """Packages a single layout, its background artwork, and wireframe mask into a .prophettemplate file."""
    if not output_path.endswith(".prophettemplate"):
        output_path += ".prophettemplate"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Determine bundled status (factory pre-included vs user custom)
    if is_bundled is None:
        is_bundled = layout_data.get("bundled", layout_id in BUILTIN_SHIPPED_LAYOUTS)

    # Locate background page artwork
    page_rel = layout_data.get("page_file", "")
    page_abs = os.path.join(base_dir, page_rel) if not os.path.isabs(page_rel) else page_rel
    if not os.path.isfile(page_abs):
        page_abs = os.path.abspath(page_rel)

    clean_data = dict(layout_data)
    clean_data["id"] = layout_id
    clean_data["page_file"] = "page.png"
    clean_data["wireframe_file"] = "wireframe.png"
    clean_data["bundled"] = bool(is_bundled)

    manifest = {
        "application": "The Daily Prophet",
        "format": "prophet_template",
        "format_version": str(CURRENT_TEMPLATE_VERSION),
        "layout_id": layout_id,
        "label": layout_data.get("label", layout_id),
        "bundled": bool(is_bundled),
        "width": layout_data.get("width", 1122),
        "height": layout_data.get("height", 1402),
    }

    # Locate or generate wireframe mask
    mask_rel = os.path.join("assets", "templates", "masks", f"{layout_id}_wireframe.png")
    mask_abs = os.path.join(base_dir, mask_rel) if not os.path.isabs(mask_rel) else mask_rel
    if not os.path.isfile(mask_abs):
        from .generate_masks import generate_wireframe_mask_for_layout

        mask_abs = generate_wireframe_mask_for_layout(layout_id, layout_data, base_dir=base_dir)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("template.json", json.dumps(clean_data, indent=2, ensure_ascii=False))

        if page_abs and os.path.isfile(page_abs):
            zf.write(page_abs, "page.png")
        if mask_abs and os.path.isfile(mask_abs):
            zf.write(mask_abs, "wireframe.png")

    return output_path


def load_template_package(
    file_path: str, cache_base_dir: Optional[str] = None, base_dir: str = "."
) -> Dict[str, object]:
    """Unpacks a .prophettemplate file into the local template cache and returns the layout definition dict."""
    target_cache = cache_base_dir or os.path.join(base_dir, TEMPLATES_CACHE_DIR)

    with zipfile.ZipFile(file_path, "r") as zf:
        clean_name = os.path.splitext(os.path.basename(file_path))[0]
        # In case filename is layout_1.prophettemplate.bak
        if clean_name.endswith(".prophettemplate"):
            clean_name = os.path.splitext(clean_name)[0]

        extract_dir = os.path.abspath(os.path.join(target_cache, clean_name))
        os.makedirs(extract_dir, exist_ok=True)

        manifest = None
        if "manifest.json" in zf.namelist():
            try:
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            except Exception:
                pass

        template_data = json.loads(zf.read("template.json").decode("utf-8"))

        for member in zf.namelist():
            if member in ["page.png", "wireframe.png"]:
                dest_path = os.path.join(extract_dir, member)
                try:
                    if not os.path.exists(dest_path):
                        zf.extract(member, extract_dir)
                    else:
                        # Avoid file-in-use overwrite conflicts on Windows
                        data_bytes = zf.read(member)
                        if os.path.getsize(dest_path) != len(data_bytes):
                            with open(dest_path, "wb") as f:
                                f.write(data_bytes)
                except Exception:
                    pass

        # Detect version and run through migration pipeline
        raw_ver = "1.0"
        if manifest:
            raw_ver = manifest.get("format_version") or manifest.get("version", "1.0")
        source_ver = FormatVersion.parse(raw_ver)
        migrated_data, _, _ = template_migration_pipeline.migrate(template_data, source_ver)

        # Determine bundled flag
        is_b = False
        if manifest and "bundled" in manifest:
            is_b = bool(manifest["bundled"])
        elif "bundled" in template_data:
            is_b = bool(template_data["bundled"])
        else:
            is_b = clean_name in BUILTIN_SHIPPED_LAYOUTS

        migrated_data["page_file"] = os.path.join(extract_dir, "page.png")
        migrated_data["wireframe_file"] = os.path.join(extract_dir, "wireframe.png")
        if "id" not in migrated_data:
            migrated_data["id"] = clean_name
        migrated_data["format_version"] = str(CURRENT_TEMPLATE_VERSION)
        migrated_data["bundled"] = is_b

        template_data = migrated_data

        # Also copy mask into assets/templates/masks/ for quick system preview
        try:
            masks_dir = os.path.join(base_dir, "assets", "templates", "masks")
            os.makedirs(masks_dir, exist_ok=True)
            cached_mask = os.path.join(extract_dir, "wireframe.png")
            if os.path.isfile(cached_mask):
                shutil.copy2(cached_mask, os.path.join(masks_dir, f"{template_data['id']}_wireframe.png"))
        except Exception:
            pass

        return template_data


def load_all_installed_templates(
    installed_dir: Optional[str] = None, shipped_dir: Optional[str] = None, base_dir: str = "."
) -> Dict[str, Dict[str, object]]:
    """Loads all .prophettemplate files from the installed directory, bootstrapping from shipped source if empty."""
    inst_dir = installed_dir or os.path.join(base_dir, INSTALLED_TEMPLATES_DIR)
    ship_dir = shipped_dir or os.path.join(base_dir, SHIPPED_TEMPLATES_DIR)
    os.makedirs(inst_dir, exist_ok=True)

    # If installed directory has no .prophettemplate files, copy over from shipped source
    installed_files = [f for f in os.listdir(inst_dir) if f.endswith(".prophettemplate")]
    if not installed_files and os.path.isdir(ship_dir):
        for f in os.listdir(ship_dir):
            if f.endswith(".prophettemplate"):
                shutil.copy2(os.path.join(ship_dir, f), os.path.join(inst_dir, f))
        installed_files = [f for f in os.listdir(inst_dir) if f.endswith(".prophettemplate")]

    templates = {}
    for filename in sorted(installed_files):
        full_path = os.path.join(inst_dir, filename)
        try:
            data = load_template_package(full_path, base_dir=base_dir)
            tid = str(data.get("id", os.path.splitext(filename)[0]))
            templates[tid] = data
            # Provide alias without layout_ or with additional_ if needed
            templates[f"additional_{tid}"] = dict(data)
        except Exception as e:
            print(f"Error loading template {filename}: {e}")

    return templates


def save_installed_template(
    layout_id: str, layout_data: Dict[str, object], installed_dir: Optional[str] = None, base_dir: str = "."
) -> str:
    """Saves a layout into its own .prophettemplate file.
    Creates a .bak copy upon first modification of an existing template.
    """
    inst_dir = installed_dir or os.path.join(base_dir, INSTALLED_TEMPLATES_DIR)
    os.makedirs(inst_dir, exist_ok=True)

    target_file = os.path.join(inst_dir, f"{layout_id}.prophettemplate")
    backup_file = target_file + ".bak"

    # Auto-backup on first modification
    if os.path.isfile(target_file) and not os.path.isfile(backup_file):
        try:
            shutil.copy2(target_file, backup_file)
            print(f"Created first-modification template backup: {backup_file}")
        except Exception as e:
            print(f"Warning: Could not create template backup: {e}")

    create_template_package(layout_id, layout_data, target_file, base_dir=base_dir)
    return target_file


def delete_installed_template(layout_id: str, installed_dir: Optional[str] = None, base_dir: str = ".") -> bool:
    """Deletes a custom .prophettemplate file.
    Refuses to delete factory bundled templates.
    """
    inst_dir = installed_dir or os.path.join(base_dir, INSTALLED_TEMPLATES_DIR)
    target_file = os.path.join(inst_dir, f"{layout_id}.prophettemplate")
    backup_file = target_file + ".bak"

    # Pre-included bundled templates cannot be deleted
    if layout_id in BUILTIN_SHIPPED_LAYOUTS:
        return False

    if os.path.isfile(target_file):
        try:
            with zipfile.ZipFile(target_file, "r") as zf:
                if "manifest.json" in zf.namelist():
                    m = json.loads(zf.read("manifest.json").decode("utf-8"))
                    if m.get("bundled", False):
                        return False
        except Exception:
            pass

    deleted = False
    if os.path.isfile(target_file):
        os.remove(target_file)
        deleted = True
    if os.path.isfile(backup_file):
        os.remove(backup_file)

    # Also remove from cache
    cache_dir = os.path.join(base_dir, TEMPLATES_CACHE_DIR, layout_id)
    if os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)

    # Remove wireframe mask
    mask_path = os.path.join(base_dir, "assets", "templates", "masks", f"{layout_id}_wireframe.png")
    if os.path.isfile(mask_path):
        os.remove(mask_path)

    return deleted


def restore_template_from_shipped_or_backup(
    layout_id: str, installed_dir: Optional[str] = None, shipped_dir: Optional[str] = None, base_dir: str = "."
) -> Optional[Dict[str, object]]:
    """Restores a single template from its .bak backup or from factory shipped defaults."""
    inst_dir = installed_dir or os.path.join(base_dir, INSTALLED_TEMPLATES_DIR)
    ship_dir = shipped_dir or os.path.join(base_dir, SHIPPED_TEMPLATES_DIR)

    backup_file = os.path.join(inst_dir, f"{layout_id}.prophettemplate.bak")
    shipped_file = os.path.join(ship_dir, f"{layout_id}.prophettemplate")
    target_file = os.path.join(inst_dir, f"{layout_id}.prophettemplate")

    source_file = None
    if os.path.isfile(shipped_file):
        source_file = shipped_file
    elif os.path.isfile(backup_file):
        source_file = backup_file

    if not source_file:
        return None

    shutil.copy2(source_file, target_file)
    return load_template_package(target_file, base_dir=base_dir)
