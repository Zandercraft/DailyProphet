"""Test saving and loading the new .prophet custom project format."""
import os
import zipfile
from daily_prophet.models import NewspaperEdition
from daily_prophet.sample_data import get_original_hogwarts_edition

def test_prophet_package():
    edition = get_original_hogwarts_edition(".")
    edition.selected_layout = "layout_3"

    test_pkg_path = "output/test_sample_issue.prophet"
    os.makedirs("output", exist_ok=True)
    if os.path.exists(test_pkg_path):
        os.remove(test_pkg_path)

    # 1. Save to .prophet package
    edition.save_project_package(test_pkg_path)
    assert os.path.exists(test_pkg_path), "Package file was not created!"
    print(f"Package created: {test_pkg_path} ({os.path.getsize(test_pkg_path)} bytes)")

    # 2. Inspect ZIP structure
    with zipfile.ZipFile(test_pkg_path, "r") as zf:
        namelist = zf.namelist()
        print("Archive contents:")
        for name in namelist:
            print("  -", name)
        assert "manifest.json" in namelist, "manifest.json missing"
        assert "edition.json" in namelist, "edition.json missing"
        media_count = sum(1 for n in namelist if n.startswith("media/"))
        print(f"Bundled {media_count} media files inside the package.")

    # 3. Load from .prophet package
    loaded_edition = NewspaperEdition.load_project_package(test_pkg_path, cache_base_dir="output/projects_cache")
    assert loaded_edition.paper_title == edition.paper_title, "Title mismatch"
    assert loaded_edition.selected_layout == "layout_3", f"Layout mismatch: {loaded_edition.selected_layout}"
    assert len(loaded_edition.stories) == len(edition.stories), "Stories count mismatch"

    # Verify that extracted media paths exist on disk
    for s in loaded_edition.stories:
        if s.image_path:
            assert os.path.isfile(s.image_path), f"Extracted image missing: {s.image_path}"

    print("Successfully verified .prophet project package loading, media extraction, and layout restoration!")

if __name__ == "__main__":
    test_prophet_package()
