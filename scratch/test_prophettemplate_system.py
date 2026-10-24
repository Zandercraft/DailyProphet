import os
import sys
import zipfile
import shutil

sys.path.insert(0, os.path.abspath("."))

from daily_prophet.template_package import (
    load_template_package,
    load_all_installed_templates,
    save_installed_template,
    delete_installed_template,
    SHIPPED_TEMPLATES_DIR,
)
from daily_prophet.models import NewspaperEdition, Story
from daily_prophet.native_renderer import NativeBroadsheetRenderer


def test_prophettemplate_system():
    print("--- 1. Testing Shipped .prophettemplate Files ---")
    for i in range(1, 10):
        tpath = os.path.join(SHIPPED_TEMPLATES_DIR, f"layout_{i}.prophettemplate")
        assert os.path.isfile(tpath), f"Missing shipped template: {tpath}"
        with zipfile.ZipFile(tpath, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names, f"manifest.json missing from {tpath}"
            assert "template.json" in names, f"template.json missing from {tpath}"
            assert "page.png" in names, f"page.png missing from {tpath}"
            assert "wireframe.png" in names, f"wireframe.png missing from {tpath}"
    print("[OK] All 9 shipped .prophettemplate packages verified.")

    print("\n--- 2. Testing Loading All Installed Templates ---")
    all_templates = load_all_installed_templates(base_dir=".")
    for i in range(1, 10):
        assert f"layout_{i}" in all_templates, f"layout_{i} failed to load from installed templates"
        tdata = all_templates[f"layout_{i}"]
        assert os.path.isfile(tdata["page_file"]), f"page_file does not exist on disk: {tdata['page_file']}"
        assert len(tdata["slots"]) > 0, f"Slots empty in {tdata['label']}"
    print(
        f"[OK] Successfully loaded {len([k for k in all_templates if not k.startswith('additional_')])} templates from .prophettemplate archives."
    )

    print("\n--- 3. Testing Single Template Modification & .bak Auto-Backup ---")
    test_id = "test_custom_template"
    test_inst_dir = "output/test_installed"
    os.makedirs(test_inst_dir, exist_ok=True)

    dummy_layout = {
        "page_file": "assets/templates/pages/additional_layout_1.png",
        "width": 1122,
        "height": 1402,
        "label": "Original Test Template",
        "slots": [{"id": "head", "type": "headline", "rect": [10, 10, 500, 50], "label": "Head"}],
    }

    # Initial save
    pkg_file = save_installed_template(test_id, dummy_layout, installed_dir=test_inst_dir, base_dir=".")
    assert os.path.isfile(pkg_file), "Initial package not created"
    bak_file = pkg_file + ".bak"
    assert not os.path.isfile(bak_file), ".bak should not exist prior to modification"

    # Modify
    dummy_layout["label"] = "Modified Test Template"
    save_installed_template(test_id, dummy_layout, installed_dir=test_inst_dir, base_dir=".")
    assert os.path.isfile(bak_file), ".bak backup was not created upon first modification!"

    # Verify backup contains original label
    orig_backed_up = load_template_package(bak_file, base_dir=".")
    assert orig_backed_up["label"] == "Original Test Template", "Backup does not have original label"
    print(f"[OK] First-modification backup verified: {bak_file}")

    print("\n--- 4. Testing Native Rendering from .prophettemplate ---")
    edition = NewspaperEdition(paper_title="The Daily Prophet", selected_layout="layout_1")
    edition.stories.append(Story(headline="Hogwarts Express On Time", body="Platform 9 3/4 was peaceful."))
    renderer = NativeBroadsheetRenderer(".")
    img = renderer.render_slot_layout(edition, template_id="layout_1", scale=0.5)
    assert img is not None
    print(f"[OK] Rendered image from template cache: {img.size}")

    print("\n--- 5. Testing Delete Installed Template ---")
    deleted = delete_installed_template(test_id, installed_dir=test_inst_dir, base_dir=".")
    assert deleted, "Failed to delete test template"
    assert not os.path.isfile(pkg_file), "Package file still exists after deletion"
    assert not os.path.isfile(bak_file), "Backup file still exists after deletion"
    print("[OK] Delete installed template successfully cleaned package, backup, and cache.")

    # Cleanup test dir
    shutil.rmtree(test_inst_dir, ignore_errors=True)

    print("\nAll .prophettemplate system verification checks passed successfully!")


if __name__ == "__main__":
    test_prophettemplate_system()
