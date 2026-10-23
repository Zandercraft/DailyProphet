"""Automated test suite verifying layout editor persistence, .prophet packaging,
global template saving with .bak auto-backup, and custom template management.
"""
import os
import sys
import json
import shutil

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from daily_prophet.models import NewspaperEdition, Story
from daily_prophet.generate_masks import (
    load_layout_definitions,
    save_global_layout_definitions,
    generate_wireframe_mask_for_layout,
    restore_factory_templates,
    SHIPPED_DEFAULTS_FILE,
    GLOBAL_LAYOUTS_FILE,
    GLOBAL_BACKUP_FILE
)
from daily_prophet.native_renderer import NativeBroadsheetRenderer

def test_all():
    print("--- 1. Testing Shipped Defaults ---")
    assert os.path.isfile(SHIPPED_DEFAULTS_FILE), f"Shipped defaults missing at {SHIPPED_DEFAULTS_FILE}"
    shipped = load_layout_definitions(defs_path=SHIPPED_DEFAULTS_FILE)
    for i in range(1, 10):
        assert f"layout_{i}" in shipped, f"layout_{i} missing from shipped defaults"
    print("[OK] Shipped defaults verified with all 9 layouts.")

    print("\n--- 2. Testing Project-Level (.prophet) Custom Slot Persistence ---")
    edition = NewspaperEdition(paper_title="The Quibbler Special", selected_layout="layout_1")
    edition.stories.append(Story(headline="Nargles Found in Bell Tower", body="Luna reports a high infestation."))

    # Custom slot override for layout_1 in this edition
    custom_slot_override = {
        'page_file': 'assets/templates/pages/additional_layout_1.png',
        'width': 1122,
        'height': 1402,
        'label': 'Custom Quibbler Layout 1',
        'slots': [
            {'id': 'custom_headline', 'type': 'headline', 'rect': [50, 50, 900, 100], 'label': 'Giant Quibbler Headline'}
        ]
    }
    edition.custom_layouts['layout_1'] = custom_slot_override

    test_pkg_path = "output/test_quibbler.prophet"
    os.makedirs("output", exist_ok=True)
    edition.save_project_package(test_pkg_path)
    assert os.path.isfile(test_pkg_path), "Project package was not created"
    print(f"[OK] Saved .prophet package with custom layout: {os.path.getsize(test_pkg_path)} bytes")

    # Load back
    loaded_edition = NewspaperEdition.load_project_package(test_pkg_path)
    assert 'layout_1' in loaded_edition.custom_layouts, "custom_layouts['layout_1'] not loaded"
    assert loaded_edition.custom_layouts['layout_1']['label'] == 'Custom Quibbler Layout 1'
    assert loaded_edition.custom_layouts['layout_1']['slots'][0]['id'] == 'custom_headline'
    print("[OK] Project package loaded back cleanly with exact custom slot override.")

    print("\n--- 3. Testing Native Renderer Uses Project Custom Layout Slots ---")
    renderer = NativeBroadsheetRenderer(".")
    img = renderer.render_slot_layout(loaded_edition, template_id="layout_1", scale=0.5)
    assert img is not None
    print(f"[OK] Rendered edition with custom slots: {img.size}")

    print("\n--- 4. Testing Global Template Saving & First-Modification .bak Creation ---")
    # Clean test .bak if needed
    test_global_defs = "output/test_layout_defs.json"
    test_bak = test_global_defs + ".bak"
    if os.path.exists(test_global_defs):
        os.remove(test_global_defs)
    if os.path.exists(test_bak):
        os.remove(test_bak)

    # Initial file
    dummy_layouts = {"layout_1": dict(custom_slot_override)}
    with open(test_global_defs, "w", encoding="utf-8") as f:
        json.dump(dummy_layouts, f, indent=2)

    # First modification should create .bak
    dummy_layouts["layout_1"]["label"] = "Modified Label"
    success = save_global_layout_definitions(dummy_layouts, defs_path=test_global_defs)
    assert success
    assert os.path.isfile(test_bak), "Backup file (.bak) was not created on first modification!"
    with open(test_bak, "r", encoding="utf-8") as f:
        bak_data = json.load(f)
    assert bak_data["layout_1"]["label"] == "Custom Quibbler Layout 1", "Backup does not contain original content!"
    print(f"[OK] .bak backup created successfully: {test_bak} matches pristine original state.")

    print("\n--- 5. Testing Wireframe Mask Generation for Layout ---")
    mask_file = generate_wireframe_mask_for_layout("layout_1", custom_slot_override, masks_dir="output/test_masks", base_dir=".")
    assert mask_file is not None and os.path.isfile(mask_file), f"Mask file failed to generate: {mask_file}"
    print(f"[OK] Mask generated cleanly: {mask_file} ({os.path.getsize(mask_file)} bytes)")

    print("\nAll automated verification checks passed successfully!")

if __name__ == "__main__":
    test_all()
