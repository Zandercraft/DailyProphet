"""Interactive Live Broadsheet Preview Canvas for The Daily Prophet.

Renders real-time broadsheet previews with bi-directional slot highlighting,
smooth zooming, panning, and support for dual-monitor detachment.
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional, Callable, Dict, List, Tuple
import customtkinter as ctk
from PIL import Image, ImageTk

from ..models import NewspaperEdition
from ..native_renderer import NativeBroadsheetRenderer, map_slots_to_stories
from .theme import Theme, IconManager
from .tooltip import add_tooltip


PREVIEW_BASE_SCALE = 1.0


class BroadsheetPreviewCanvas(ctk.CTkFrame):
    """Interactive canvas widget displaying a live-updating newspaper page."""

    def __init__(
        self,
        master,
        edition: NewspaperEdition,
        on_slot_clicked: Optional[Callable[[str, Optional[str]], None]] = None,
        on_page_changed: Optional[Callable[[int], None]] = None,
        on_detach_requested: Optional[Callable[[], None]] = None,
        is_detached: bool = False,
        **kwargs,
    ):
        super().__init__(master, fg_color=Theme.CANVAS_BG, corner_radius=6, **kwargs)
        self.edition = edition
        self.on_slot_clicked = on_slot_clicked
        self.on_page_changed = on_page_changed
        self.on_detach_requested = on_detach_requested
        self.is_detached = is_detached

        self.current_page_idx = 0
        self.is_fit_mode = True
        self.zoom_level: float = 1.0
        self._resize_timer_id: Optional[str] = None
        self._last_canvas_size: Optional[Tuple[int, int]] = None

        self.selected_slot_id: Optional[str] = None
        self.selected_story_id: Optional[str] = None
        self.highlight_slot_ids: List[str] = []
        self.slot_to_story: Dict[str, str] = {}
        self.story_to_slots: Dict[str, List[str]] = {}

        self.renderer = NativeBroadsheetRenderer()
        self._rendered_pil: Optional[Image.Image] = None
        self._displayed_photo: Optional[ImageTk.PhotoImage] = None
        self._current_layout_slots: List[Dict[str, object]] = []
        self._current_canvas_scale = 1.0

        self._img_x = 8
        self._img_y = 8
        self._disp_w = 0
        self._disp_h = 0

        self._setup_ui()

    def _setup_ui(self):
        # 1. Top Preview Toolbar
        toolbar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, height=38, corner_radius=4)
        toolbar.pack(fill="x", padx=4, pady=(4, 2))

        # Title / status
        self.title_lbl = ctk.CTkLabel(
            toolbar,
            text=" Live Broadsheet",
            image=IconManager.get_icon("eye", size=14),
            compound="left",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PARCHMENT,
        )
        self.title_lbl.pack(side="left", padx=8)

        # Detach / Dock button
        if self.on_detach_requested:
            detach_icon = "minimize-2" if self.is_detached else "maximize-2"
            self.detach_btn = ctk.CTkButton(
                toolbar,
                text="",
                image=IconManager.get_icon(detach_icon, size=15),
                width=36,
                height=30,
                corner_radius=4,
                fg_color=Theme.BTN_NEUTRAL[0],
                hover_color=Theme.BTN_NEUTRAL[1],
                command=self.on_detach_requested,
            )
            self.detach_btn.pack(side="right", padx=6)
            add_tooltip(
                self.detach_btn,
                "Dock Live Broadsheet into Main Window"
                if self.is_detached
                else "Pop Out Live Broadsheet into Dual-Monitor Window",
            )

        # Zoom controls (matching slot editor zoom strip)
        zoom_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        zoom_frame.pack(side="right", padx=6)

        z_out_btn = ctk.CTkButton(
            zoom_frame,
            text="-",
            width=26,
            height=28,
            corner_radius=4,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._zoom_out,
        )
        z_out_btn.pack(side="left", padx=1)
        add_tooltip(z_out_btn, "Zoom Out (or Ctrl+Scroll Down)")

        self.zoom_menu = ctk.CTkOptionMenu(
            zoom_frame,
            values=["Fit Page", "50%", "75%", "100%", "125%", "150%", "200%"],
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BTN_SECONDARY[0],
            button_color=Theme.BTN_SECONDARY[1],
            command=self._on_zoom_option_selected,
        )
        self.zoom_menu.pack(side="left", padx=1)
        self.zoom_menu.set("Fit Page")
        add_tooltip(self.zoom_menu, "Zoom Preset / Current Scale")

        z_in_btn = ctk.CTkButton(
            zoom_frame,
            text="+",
            width=26,
            height=28,
            corner_radius=4,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._zoom_in,
        )
        z_in_btn.pack(side="left", padx=1)
        add_tooltip(z_in_btn, "Zoom In (or Ctrl+Scroll Up)")

        fit_btn = ctk.CTkButton(
            zoom_frame,
            text="Fit",
            width=36,
            height=28,
            corner_radius=4,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._zoom_fit,
        )
        fit_btn.pack(side="left", padx=1)
        add_tooltip(fit_btn, "Fit Page to Viewport")

        # 2. Main Scrollable Canvas Area
        canvas_container = ctk.CTkFrame(self, fg_color=Theme.CANVAS_BG)
        canvas_container.pack(fill="both", expand=True, padx=4, pady=2)

        self.canvas = tk.Canvas(canvas_container, bg=Theme.CANVAS_BG, highlightthickness=0, cursor="hand2")
        self.v_scroll = ctk.CTkScrollbar(canvas_container, orientation="vertical", command=self.canvas.yview)
        self.h_scroll = ctk.CTkScrollbar(canvas_container, orientation="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Pan bindings (Right-click and Middle-click drag)
        self.canvas.bind("<ButtonPress-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._do_pan)
        self.canvas.bind("<ButtonRelease-3>", self._end_pan)
        self.canvas.bind("<ButtonPress-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._do_pan)
        self.canvas.bind("<ButtonRelease-2>", self._end_pan)

        # Scroll & Zoom bindings
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_wheel_button(e, -1))
        self.canvas.bind("<Button-5>", lambda e: self._on_wheel_button(e, 1))

        # 3. Bottom Page Flip Bar
        flip_bar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, height=38, corner_radius=4)
        flip_bar.pack(fill="x", padx=4, pady=(2, 4))

        self.prev_btn = ctk.CTkButton(
            flip_bar,
            text="",
            image=IconManager.get_icon("chevron-left", size=15),
            width=32,
            height=28,
            corner_radius=4,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._prev_page,
        )
        self.prev_btn.pack(side="left", padx=6, pady=4)
        add_tooltip(self.prev_btn, "Previous Broadsheet Page")

        self.page_status_lbl = ctk.CTkLabel(
            flip_bar, text="Page 1 of 1", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_PARCHMENT
        )
        self.page_status_lbl.pack(side="left", padx=6)

        self.next_btn = ctk.CTkButton(
            flip_bar,
            text="",
            image=IconManager.get_icon("chevron-right", size=15),
            width=32,
            height=28,
            corner_radius=4,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._next_page,
        )
        self.next_btn.pack(side="left", padx=6, pady=4)
        add_tooltip(self.next_btn, "Next Broadsheet Page")

        self.page_title_lbl = ctk.CTkLabel(
            flip_bar, text="Front Page", font=ctk.CTkFont(size=13, slant="italic"), text_color=Theme.TEXT_MUTED
        )
        self.page_title_lbl.pack(side="right", padx=10)

    def set_edition(self, edition: NewspaperEdition):
        self.edition = edition
        self.selected_story_id = None
        self.selected_slot_id = None
        self.highlight_slot_ids = []
        self.refresh_preview()

    def set_current_page(self, page_idx: int):
        num_pages = len(self.edition.pages) if (hasattr(self.edition, "pages") and self.edition.pages) else 1
        self.current_page_idx = max(0, min(page_idx, num_pages - 1))
        self._update_page_controls()
        self.refresh_preview()

    def set_highlight(
        self,
        story_id: Optional[str] = None,
        slot_id: Optional[str] = None,
        slot_ids: Optional[List[str]] = None,
    ):
        """Highlights a specific story's slot(s) on the live sheet preview."""
        self.selected_story_id = story_id
        if slot_ids is not None:
            self.highlight_slot_ids = list(slot_ids)
            self.selected_slot_id = slot_id or (slot_ids[0] if slot_ids else None)
        elif slot_id:
            self.selected_slot_id = slot_id
            self.highlight_slot_ids = [slot_id]
        elif story_id:
            self.highlight_slot_ids = self.story_to_slots.get(story_id, [])
            self.selected_slot_id = self.highlight_slot_ids[0] if self.highlight_slot_ids else None
        else:
            self.selected_slot_id = None
            self.highlight_slot_ids = []
        self._draw_highlights()

    def refresh_preview(self):
        """Re-renders the active page of the newspaper and updates the canvas."""
        if not self.edition:
            return

        page = self.edition.get_page(self.current_page_idx) if hasattr(self.edition, "get_page") else None
        layout_id = page.layout_id if page else getattr(self.edition, "selected_layout", "layout_1")

        # Load layout definition to know slot locations
        from ..template_package import load_all_installed_templates

        all_defs = load_all_installed_templates(base_dir=self.renderer.base_dir)
        layout_def = {}
        if hasattr(self.edition, "custom_layouts") and layout_id in self.edition.custom_layouts:
            layout_def = self.edition.custom_layouts[layout_id]
        elif layout_id in all_defs:
            layout_def = all_defs[layout_id]
        self._current_layout_slots = layout_def.get("slots", [])

        # Compute slot <-> story mapping for interactive bidirectional highlighting
        page_stories = page.stories if (page and hasattr(page, "stories") and page.stories) else self.edition.stories
        self.slot_to_story, self.story_to_slots = map_slots_to_stories(page_stories, self._current_layout_slots)

        # Render native broadsheet image at preview scale
        try:
            self._rendered_pil = self.renderer.render_slot_layout(
                self.edition, template_id=layout_id, scale=PREVIEW_BASE_SCALE, page=page
            )
        except Exception:
            self._rendered_pil = None

        self._update_page_controls()
        self._redraw_canvas()

    def _update_page_controls(self):
        num_pages = len(self.edition.pages) if (hasattr(self.edition, "pages") and self.edition.pages) else 1
        page_num = self.current_page_idx + 1
        self.page_status_lbl.configure(text=f"Page {page_num} of {num_pages}")
        page = self.edition.get_page(self.current_page_idx) if hasattr(self.edition, "get_page") else None
        title = page.title if page else "Broadsheet"
        self.page_title_lbl.configure(text=title)

        self.prev_btn.configure(state="normal" if self.current_page_idx > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page_idx < num_pages - 1 else "disabled")

    def _prev_page(self):
        if self.current_page_idx > 0:
            self.set_current_page(self.current_page_idx - 1)
            if self.on_page_changed:
                self.on_page_changed(self.current_page_idx)

    def _next_page(self):
        num_pages = len(self.edition.pages) if (hasattr(self.edition, "pages") and self.edition.pages) else 1
        if self.current_page_idx < num_pages - 1:
            self.set_current_page(self.current_page_idx + 1)
            if self.on_page_changed:
                self.on_page_changed(self.current_page_idx)

    # -----------------------------------------------------------------------
    # Pan & Scroll Navigation
    # -----------------------------------------------------------------------
    def _start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.configure(cursor="fleur")

    def _do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _end_pan(self, event=None):
        self.canvas.configure(cursor="hand2")

    def _on_mousewheel(self, event):
        if event.state & 4:  # Ctrl held down -> zoom
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        elif event.state & 1:  # Shift held down -> horizontal scroll
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:  # Vertical scroll
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_wheel_button(self, event, direction: int):
        if event.state & 4:  # Ctrl held down -> zoom
            if direction < 0:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            self.canvas.yview_scroll(direction, "units")

    # -----------------------------------------------------------------------
    # Zoom Controls
    # -----------------------------------------------------------------------
    def _zoom_in(self):
        self.is_fit_mode = False
        self.zoom_level = min(3.0, round(self.zoom_level + 0.1, 2))
        self._update_zoom_label()
        self._redraw_canvas()

    def _zoom_out(self):
        self.is_fit_mode = False
        self.zoom_level = max(0.15, round(self.zoom_level - 0.1, 2))
        self._update_zoom_label()
        self._redraw_canvas()

    def _zoom_fit(self):
        self.is_fit_mode = True
        self._redraw_canvas()

    def _on_zoom_option_selected(self, choice: str):
        if choice in ("Fit Page", "Fit to Screen"):
            self._zoom_fit()
        else:
            try:
                pct = int(choice.replace("%", "").strip())
                self.is_fit_mode = False
                self.zoom_level = round(pct / 100.0, 2)
                self._update_zoom_label()
                self._redraw_canvas()
            except ValueError:
                pass

    def _on_zoom_changed(self, choice: str):
        """Backward-compatibility alias for _on_zoom_option_selected."""
        self._on_zoom_option_selected(choice)

    def _update_zoom_label(self):
        pct = int(round(self.zoom_level * 100))
        label_text = f"Fit ({pct}%)" if self.is_fit_mode else f"{pct}%"
        self.zoom_menu.set(label_text if not self.is_fit_mode else "Fit Page")

    # -----------------------------------------------------------------------
    # Responsive Resizing & Canvas Redraw
    # -----------------------------------------------------------------------
    def _on_canvas_resize(self, event):
        new_w = event.width
        new_h = event.height
        if new_w <= 10 or new_h <= 10:
            return
        if getattr(self, "_last_canvas_size", None) == (new_w, new_h):
            return
        self._last_canvas_size = (new_w, new_h)

        if self._resize_timer_id is not None:
            self.after_cancel(self._resize_timer_id)
        # 35ms debounce guarantees butter-smooth responsive resizing without frame stutter
        self._resize_timer_id = self.after(35, self._handle_delayed_resize)

    def _handle_delayed_resize(self):
        self._resize_timer_id = None
        if self.is_fit_mode:
            self._redraw_canvas()
        else:
            self._update_canvas_viewport()

    def _update_canvas_viewport(self):
        if not self._displayed_photo:
            return
        c_w = max(50, self.canvas.winfo_width())
        c_h = max(50, self.canvas.winfo_height())
        disp_w = getattr(self, "_disp_w", self._displayed_photo.width())
        disp_h = getattr(self, "_disp_h", self._displayed_photo.height())

        offset_x = max(8, (c_w - disp_w) // 2)
        offset_y = max(8, (c_h - disp_h) // 2)
        self._img_x = offset_x
        self._img_y = offset_y

        self.canvas.coords("sheet_img", offset_x, offset_y)
        scroll_w = max(c_w, offset_x + disp_w + 12)
        scroll_h = max(c_h, offset_y + disp_h + 12)
        self.canvas.config(scrollregion=(0, 0, scroll_w, scroll_h))
        self._draw_highlights()

    def _redraw_canvas(self):
        if self._rendered_pil is None:
            self.canvas.delete("all")
            return

        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 10 or c_h <= 10:
            if getattr(self, "_last_canvas_size", None):
                c_w, c_h = self._last_canvas_size
            else:
                c_w = 500
                c_h = 700

        c_w = max(50, c_w)
        c_h = max(50, c_h)
        orig_w, orig_h = self._rendered_pil.size
        if orig_w <= 0 or orig_h <= 0:
            return

        if self.is_fit_mode:
            pad = 16
            scale_w = (c_w - pad) / orig_w
            scale_h = (c_h - pad) / orig_h
            scale = max(0.15, min(scale_w, scale_h))
            self.zoom_level = scale
            self._update_zoom_label()
        else:
            scale = self.zoom_level

        disp_w = max(10, int(orig_w * scale))
        disp_h = max(10, int(orig_h * scale))
        self._current_canvas_scale = scale * PREVIEW_BASE_SCALE  # Relative to base template coordinates

        resized = self._rendered_pil.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self._displayed_photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        # Center the image on the canvas
        offset_x = max(8, (c_w - disp_w) // 2)
        offset_y = max(8, (c_h - disp_h) // 2)

        self._img_x = offset_x
        self._img_y = offset_y
        self._disp_w = disp_w
        self._disp_h = disp_h

        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self._displayed_photo, tags="sheet_img")
        scroll_w = max(c_w, offset_x + disp_w + 12)
        scroll_h = max(c_h, offset_y + disp_h + 12)
        self.canvas.config(scrollregion=(0, 0, scroll_w, scroll_h))

        self._draw_highlights()

    def _draw_highlights(self):
        self.canvas.delete("highlight")
        slots_to_draw = (
            self.highlight_slot_ids
            if self.highlight_slot_ids
            else ([self.selected_slot_id] if self.selected_slot_id else [])
        )
        if not slots_to_draw:
            return

        for slot in self._current_layout_slots:
            sid = slot.get("id", "")
            if sid in slots_to_draw:
                rx, ry, rw, rh = slot.get("rect", [0, 0, 0, 0])
                sx1 = self._img_x + int(rx * self._current_canvas_scale)
                sy1 = self._img_y + int(ry * self._current_canvas_scale)
                sx2 = sx1 + int(rw * self._current_canvas_scale)
                sy2 = sy1 + int(rh * self._current_canvas_scale)

                is_primary = sid == self.selected_slot_id
                outline_color = "#e5c158" if is_primary else "#c49a3c"
                border_w = 3 if is_primary else 2
                dash_pattern = None if is_primary else (5, 3)

                # Draw glowing parchment gold highlight rectangle
                self.canvas.create_rectangle(
                    sx1,
                    sy1,
                    sx2,
                    sy2,
                    outline=outline_color,
                    width=border_w,
                    dash=dash_pattern,
                    tags="highlight",
                )

    def _on_canvas_click(self, event):
        """Translates click coordinate to slot space and selects corresponding article."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        rel_x = cx - getattr(self, "_img_x", 0)
        rel_y = cy - getattr(self, "_img_y", 0)

        if rel_x < 0 or rel_y < 0 or self._current_canvas_scale <= 0:
            return

        slot_x = rel_x / self._current_canvas_scale
        slot_y = rel_y / self._current_canvas_scale

        for slot in self._current_layout_slots:
            rx, ry, rw, rh = slot.get("rect", [0, 0, 0, 0])
            if rx <= slot_x <= rx + rw and ry <= slot_y <= ry + rh:
                slot_id = slot.get("id", "")
                self.selected_slot_id = slot_id
                matched_story_id = self.slot_to_story.get(slot_id)
                if matched_story_id and matched_story_id in self.story_to_slots:
                    self.highlight_slot_ids = self.story_to_slots[matched_story_id]
                else:
                    self.highlight_slot_ids = [slot_id]
                self._draw_highlights()
                if self.on_slot_clicked:
                    self.on_slot_clicked(slot_id, matched_story_id)
                return


class PreviewToplevelWindow(ctk.CTkToplevel):
    """Independent floating window hosting the live broadsheet preview for dual-monitor setups."""

    def __init__(self, parent, edition: NewspaperEdition, on_slot_clicked=None, on_page_changed=None, on_dock=None):
        super().__init__(parent)
        self.on_dock = on_dock
        self.title("The Daily Prophet - Live Broadsheet Display")
        self.geometry("900x1100")
        self.minsize(550, 700)

        self.preview_canvas = BroadsheetPreviewCanvas(
            self,
            edition=edition,
            on_slot_clicked=on_slot_clicked,
            on_page_changed=on_page_changed,
            on_detach_requested=self._on_dock_pressed,
            is_detached=True,
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=6, pady=6)

        self.protocol("WM_DELETE_WINDOW", self._on_dock_pressed)

    def _on_dock_pressed(self):
        if self.on_dock:
            self.on_dock()
        self.destroy()
