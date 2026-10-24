import sys

sys.path.insert(0, ".")
from daily_prophet.gui.main_window import MainWindow
from daily_prophet.gui.layout_editor_window import LayoutEditorWindow

app = MainWindow()
app.update()

# 1. Test adding a page
app._add_new_page()
app.update()
assert len(app.edition.pages) == 2, f"Expected 2 pages, got {len(app.edition.pages)}"
print("Page addition ok. Pages:", len(app.edition.pages))

# 2. Test switching page
app._on_page_tab_clicked(1)
app.update()
assert app.current_page_idx == 1, f"Expected page 1, got {app.current_page_idx}"
print("Page tab switch ok. Current page:", app.current_page_idx)

# 3. Test adding story to page 2
app._add_story()
app.update()
assert len(app.edition.get_page(1).stories) >= 1, "Story addition to page 2 failed"
print("Story added to page 2 ok.")

# 4. Test composer typing / update
story = app.edition.get_page(1).stories[0]
app.center_composer.headline_entry.delete(0, "end")
app.center_composer.headline_entry.insert(0, "TEST PROPHET HEADLINE")
app.center_composer._sync_to_story()
app.update()
assert story.headline == "TEST PROPHET HEADLINE", f"Expected 'TEST PROPHET HEADLINE', got {story.headline}"
print("Composer sync ok.")

# 5. Test detach preview to floating window and dock back
app._toggle_preview_detachment()
app.update()
assert app.floating_preview_win is not None, "Preview detach failed"
print("Preview detach ok.")

app._toggle_preview_detachment()
app.update()
assert app.floating_preview_win is None, "Preview re-dock failed"
print("Preview dock back ok.")

# 6. Test preview canvas zoom, pan, and responsive resize
pc = app.preview_canvas
assert pc.is_fit_mode is True, "Preview should start in auto-fit mode"
pc._zoom_in()
assert pc.is_fit_mode is False, "Zoom in should switch to custom zoom"
pc._zoom_fit()
assert pc.is_fit_mode is True, "Fit button should restore fit mode"

# Simulate screen resize event
ev = type("ResizeEvent", (), {"width": 800, "height": 1000})()
pc._on_canvas_resize(ev)
pc._handle_delayed_resize()
assert pc.is_fit_mode is True
print("Preview canvas zoom, pan, and responsive resize ok.")

# 7. Test slot alignment / justification
le = LayoutEditorWindow(app)
le._select_slot_by_index(0)
slot = le.layouts_data[le.current_layout_key]["slots"][0]
le._on_slot_align_selected("Center")
assert slot.get("align") == "center"
le._on_slot_align_selected("Justify (Full)")
assert slot.get("align") == "justify"
le.destroy()
print("Slot alignment / justification inspector ok.")

# 8. Test live settings field updates
app.title_entry.delete(0, "end")
app.title_entry.insert(0, "THE EVENING PROPHET")
app._on_settings_field_changed()
assert app.edition.paper_title == "THE EVENING PROPHET"
print("Live settings field updates and preview sync ok.")

# 9. Test native renderer with symbols / stars
from daily_prophet.native_renderer import NativeBroadsheetRenderer  # noqa: E402
from daily_prophet.models import NewspaperEdition  # noqa: E402

renderer = NativeBroadsheetRenderer()
app.edition.breaking_banner = "BREAKING ★ STAR ALERT ★ TEST"
img = renderer.render_page(app.edition, 0)
assert img is not None
print("Native broadsheet symbol/star rendering ok.")

# 10. Test blank project resets composer and selection state
app.edition = NewspaperEdition()
app.current_page_idx = 0
app.current_project_path = None
app._load_edition_into_ui()
assert app.center_composer.headline_entry.get() == ""
assert app.center_composer.body_text.get("1.0", "end-1c") == ""
assert app.selected_story_id is None
assert app.preview_canvas.selected_story_id is None
assert app.preview_canvas.highlight_slot_ids == []
print("Blank project composer reset and selection clearing ok.")

app.destroy()
print("All functional GUI smoke tests PASSED!")
