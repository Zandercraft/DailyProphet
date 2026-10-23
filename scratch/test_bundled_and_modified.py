import os
import sys
import json
import zipfile
import shutil

sys.path.insert(0, os.path.abspath("."))

from daily_prophet.models import NewspaperEdition, Story
from daily_prophet.template_package import (
    load_all_installed_templates,
    load_template_package,
    delete_installed_template,
    is_layout_modified,
    SHIPPED_TEMPLATES_DIR,
    INSTALLED_TEMPLATES_DIR
)
from daily_prophet.gui.layout_editor_window import LayoutEditorWindow

def test_bundled_and_modified():
    print("--- 1. Testing Bundled Flag on Pre-Included Templates ---")
    installed = load_all_installed_templates(base_dir=".")
    for i in range(1, 10):
        t = installed[f"layout_{i}"]
        assert t.get("bundled") is True, f"layout_{i} is not marked as bundled!"
        # Verify deletion is rejected
        res = delete_installed_template(f"layout_{i}", base_dir=".")
        assert res is False, f"Bundled template layout_{i} was deleted! Should be protected."
    print("[OK] All 9 factory templates have bundled=True and are protected against deletion.")

    print("\n--- 2. Testing Layout Bundled Inside .prophet and Modified Detection ---")
    edition = NewspaperEdition(paper_title="The Daily Prophet", selected_layout="layout_1")
    edition.stories.append(Story(headline="Test Story", body="Body text."))

    test_pkg = "output/test_bundled_issue.prophet"
    os.makedirs("output", exist_ok=True)
    edition.save_project_package(test_pkg)

    # Verify layout_1 is bundled inside the package
    with zipfile.ZipFile(test_pkg, "r") as zf:
        data = json.loads(zf.read("edition.json").decode("utf-8"))
        assert "custom_layouts" in data, "custom_layouts missing from package"
        assert "layout_1" in data["custom_layouts"], "Active layout layout_1 was not bundled in .prophet!"
        bundled_layout = data["custom_layouts"]["layout_1"]

    # Initial state should NOT be modified compared to local template
    local_layout = installed["layout_1"]
    assert is_layout_modified(bundled_layout, local_layout) is False, "Unmodified bundled layout flagged as modified"
    print("[OK] Issue bundles active layout and correctly identifies it as unmodified.")

    # Now modify one slot in the issue
    bundled_layout["slots"][0]["rect"] = [999, 999, 100, 100]
    assert is_layout_modified(bundled_layout, local_layout) is True, "Modified layout not detected!"
    print("[OK] Modified slot bounding box correctly triggers [Modified] status.")

    print("\n--- 3. Testing Layout Editor Checkbox Defaulting to OFF ---")
    # Simulate loading into LayoutEditorWindow
    import customtkinter as ctk
    app = ctk.CTk()
    app.withdraw()

    editor = LayoutEditorWindow(app, initial_layout="layout_1", edition=edition, base_dir=".")
    assert editor.save_to_global_var.get() is False, "save_to_global_var did not default to False!"
    print("[OK] Layout Editor 'Also update global template' checkbox verified to be OFF by default.")
    app.destroy()

    # Clean up test output
    if os.path.exists(test_pkg):
        os.remove(test_pkg)

    print("\nAll bundled template protection and modified detection checks passed successfully!")

if __name__ == "__main__":
    test_bundled_and_modified()
