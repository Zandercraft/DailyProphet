import sys

sys.path.insert(0, ".")
from daily_prophet.gui.main_window import MainWindow

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

app.destroy()
print("All functional GUI smoke tests PASSED!")
