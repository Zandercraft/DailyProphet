import os
import sys
import json
import zipfile
import shutil

sys.path.insert(0, os.path.abspath("."))

from daily_prophet.models import NewspaperEdition, Story
from daily_prophet.versioning import (
    ProjectMigrator,
    TemplateMigrator,
    CURRENT_PROJECT_VERSION,
    CURRENT_TEMPLATE_VERSION
)

def test_versioning_and_compatibility():
    print("--- 1. Testing Creation of Legacy v1.0 Package ---")
    os.makedirs("output/test_versioning", exist_ok=True)
    v1_pkg_path = "output/test_versioning/legacy_issue_v10.prophet"

    # Construct pure v1.0 raw edition data without modern fields
    v1_manifest = {
        "application": "The Daily Prophet",
        "format": "prophet_package",
        "version": "1.0",
        "edition_title": "Daily Prophet 1993 Edition"
    }
    v1_edition_data = {
        "paper_title": "Daily Prophet 1993 Edition",
        "edition_date": "1 September 1993",
        "stories": [
            {
                "id": "story1",
                "headline": "Black Still At Large",
                "body": "Sirius Black remains uncaptured by the Ministry."
            }
        ]
    }

    with zipfile.ZipFile(v1_pkg_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(v1_manifest, indent=2))
        zf.writestr("edition.json", json.dumps(v1_edition_data, indent=2))

    assert os.path.isfile(v1_pkg_path)
    print(f"[OK] Created legacy v1.0 test package: {v1_pkg_path}")

    print("\n--- 2. Testing Forward Migration Pipeline (v1.0 -> v2.0 in Memory) ---")
    loaded = NewspaperEdition.load_project_package(v1_pkg_path)

    # In-memory upgrade assertions
    assert loaded.is_upgraded_in_memory is True, "is_upgraded_in_memory should be True for v1.0 file"
    assert loaded.original_loaded_version == "1.0", f"Expected original version '1.0', got '{loaded.original_loaded_version}'"
    assert loaded.file_format_version == CURRENT_PROJECT_VERSION, f"Expected format version '{CURRENT_PROJECT_VERSION}'"

    # Verify modern fields initialized cleanly
    assert hasattr(loaded, "custom_layouts") and isinstance(loaded.custom_layouts, dict)
    assert hasattr(loaded.stories[0], "box_style") and loaded.stories[0].box_style == "standard"
    assert hasattr(loaded.stories[0], "inline_image_align") and loaded.stories[0].inline_image_align == "right"
    print("[OK] Legacy v1.0 project cleanly migrated to v2.0 in memory.")

    print("\n--- 3. Testing Upgrade on Save ---")
    upgraded_pkg_path = "output/test_versioning/upgraded_issue_v20.prophet"
    loaded.save_project_package(upgraded_pkg_path)

    assert loaded.is_upgraded_in_memory is False, "is_upgraded_in_memory should be cleared after saving as latest"
    with zipfile.ZipFile(upgraded_pkg_path, "r") as zf:
        saved_manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert saved_manifest["version"] == "2.0", f"Manifest version should be '2.0', got {saved_manifest['version']}"
    print("[OK] Upgraded project saved with format v2.0 manifest.")

    print("\n--- 4. Testing Word-Style Compatibility Checker & Destructive Downgrade ---")
    # Modern v2.0 edition with advanced features
    modern_edition = NewspaperEdition(paper_title="Modern Edition")
    modern_edition.custom_layouts["layout_1"] = {"slots": [{"id": "custom1", "rect": [0,0,10,10]}]}
    modern_edition.stories.append(Story(
        headline="Advanced Alchemical Discovery",
        inline_image_path="test_cutout.png",
        box_style="ornate_box",
        pull_quote="Gold can be synthesized!"
    ))

    # Compatibility check against v1.0
    warnings = ProjectMigrator.analyze_downgrade(modern_edition.to_dict(), target_version="1.0")
    assert len(warnings) >= 3, f"Expected at least 3 compatibility warnings, got {len(warnings)}: {warnings}"
    for w in warnings:
        print(f"  Warning: {w}")

    # Perform destructive downgrade export
    compat_v10_path = "output/test_versioning/exported_compat_v10.prophet"
    modern_edition.save_project_package(compat_v10_path, target_version="1.0")

    with zipfile.ZipFile(compat_v10_path, "r") as zf:
        compat_manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        compat_edition = json.loads(zf.read("edition.json").decode("utf-8"))
        assert compat_manifest["version"] == "1.0", f"Expected v1.0 manifest, got {compat_manifest['version']}"
        assert "custom_layouts" not in compat_edition, "custom_layouts should be stripped in v1.0"
        s0 = compat_edition["stories"][0]
        assert s0["inline_image_path"] == "", "inline_image_path should be empty in v1.0"
        assert s0["box_style"] == "standard", "box_style should be reverted to standard in v1.0"
        assert s0["pull_quote"] == "", "pull_quote should be stripped in v1.0"
    print("[OK] Compatibility Mode export successfully generated valid v1.0 package.")

    print("\n--- 5. Testing Template Migrator Compatibility ---")
    v1_template = {
        "label": "Old Style Template",
        "slots": [
            {"id": "slot1", "rect": [10, 10, 200, 100]}
        ]
    }
    v1_t_ver = TemplateMigrator.detect_version(None, v1_template)
    migrated_t, was_t_up, orig_t_ver = TemplateMigrator.migrate_to_latest(v1_template, v1_t_ver)
    assert was_t_up is True
    assert migrated_t["slots"][0]["type"] == "body"
    assert migrated_t["slots"][0]["label"] == "Slot1"
    print("[OK] Template Migrator cleanly upgraded legacy template in memory.")

    # Cleanup test dir
    shutil.rmtree("output/test_versioning", ignore_errors=True)

    print("\nAll versioning and compatibility mode checks passed successfully!")

if __name__ == "__main__":
    test_versioning_and_compatibility()
