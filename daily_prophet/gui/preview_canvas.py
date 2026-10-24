"""Interactive Live Broadsheet Preview Canvas for The Daily Prophet.

Renders real-time broadsheet previews with bi-directional slot highlighting,
smooth zooming, panning, and support for dual-monitor detachment.
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional, Callable, Dict, List
import customtkinter as ctk
from PIL import Image, ImageTk

from ..models import NewspaperEdition
from ..native_renderer import NativeBroadsheetRenderer
from .theme import Theme, IconManager


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
        self.zoom_mode = "fit"  # "fit", "50%", "75%", "100%", "150%"
        self.custom_scale = 0.5
        self.selected_slot_id: Optional[str] = None
        self.selected_story_id: Optional[str] = None

        self.renderer = NativeBroadsheetRenderer()
        self._rendered_pil: Optional[Image.Image] = None
        self._displayed_photo: Optional[ImageTk.PhotoImage] = None
        self._current_layout_slots: List[Dict[str, object]] = []
        self._current_canvas_scale = 1.0

        self._setup_ui()

    def _setup_ui(self):
        # 1. Top Preview Toolbar
        toolbar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, height=36, corner_radius=4)
        toolbar.pack(fill="x", padx=4, pady=(4, 2))

        # Title / status
        self.title_lbl = ctk.CTkLabel(
            toolbar,
            text=" Live Broadsheet",
            image=IconManager.get_icon("eye", size=13),
            compound="left",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Theme.TEXT_PARCHMENT,
        )
        self.title_lbl.pack(side="left", padx=8)

        # Detach / Dock button
        if self.on_detach_requested:
            detach_text = " Dock" if self.is_detached else " Pop Out"
            detach_icon = "minimize-2" if self.is_detached else "maximize-2"
            self.detach_btn = ctk.CTkButton(
                toolbar,
                text=detach_text,
                image=IconManager.get_icon(detach_icon, size=12),
                compound="left",
                width=80,
                height=24,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=Theme.BTN_NEUTRAL[0],
                hover_color=Theme.BTN_NEUTRAL[1],
                command=self.on_detach_requested,
            )
            self.detach_btn.pack(side="right", padx=6)

        # Zoom buttons
        zoom_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        zoom_frame.pack(side="right", padx=6)

        self.zoom_menu = ctk.CTkOptionMenu(
            zoom_frame,
            values=["Fit to Screen", "50%", "75%", "100%", "150%"],
            width=105,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=Theme.BTN_SECONDARY[0],
            button_color=Theme.BTN_SECONDARY[1],
            command=self._on_zoom_changed,
        )
        self.zoom_menu.pack(side="right", padx=2)
        self.zoom_menu.set("Fit to Screen")

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

        # 3. Bottom Page Flip Bar
        flip_bar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, height=32, corner_radius=4)
        flip_bar.pack(fill="x", padx=4, pady=(2, 4))

        self.prev_btn = ctk.CTkButton(
            flip_bar,
            text="",
            image=IconManager.get_icon("chevron-left", size=14),
            width=28,
            height=22,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._prev_page,
        )
        self.prev_btn.pack(side="left", padx=6, pady=4)

        self.page_status_lbl = ctk.CTkLabel(
            flip_bar, text="Page 1 of 1", font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_PARCHMENT
        )
        self.page_status_lbl.pack(side="left", padx=6)

        self.next_btn = ctk.CTkButton(
            flip_bar,
            text="",
            image=IconManager.get_icon("chevron-right", size=14),
            width=28,
            height=22,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._next_page,
        )
        self.next_btn.pack(side="left", padx=6, pady=4)

        self.page_title_lbl = ctk.CTkLabel(
            flip_bar, text="Front Page", font=ctk.CTkFont(size=11, slant="italic"), text_color=Theme.TEXT_MUTED
        )
        self.page_title_lbl.pack(side="right", padx=10)

    def set_edition(self, edition: NewspaperEdition):
        self.edition = edition
        self.refresh_preview()

    def set_current_page(self, page_idx: int):
        num_pages = len(self.edition.pages) if (hasattr(self.edition, "pages") and self.edition.pages) else 1
        self.current_page_idx = max(0, min(page_idx, num_pages - 1))
        self._update_page_controls()
        self.refresh_preview()

    def set_highlight(self, story_id: Optional[str] = None, slot_id: Optional[str] = None):
        """Highlights a specific story's slot on the live sheet preview."""
        self.selected_story_id = story_id
        self.selected_slot_id = slot_id
        self._draw_highlights()

    def refresh_preview(self):
        """Re-renders the active page of the newspaper and updates the canvas."""
        if not self.edition:
            return

        page = self.edition.get_page(self.current_page_idx) if hasattr(self.edition, "get_page") else None
        layout_id = page.layout_id if page else getattr(self.edition, "selected_layout", "layout_1")

        # Load layout definition to know slot locations
        from ..template_package import load_all_installed_templates

        all_defs = load_all_installed_templates(self.renderer.base_dir)
        layout_def = {}
        if hasattr(self.edition, "custom_layouts") and layout_id in self.edition.custom_layouts:
            layout_def = self.edition.custom_layouts[layout_id]
        elif layout_id in all_defs:
            layout_def = all_defs[layout_id]
        self._current_layout_slots = layout_def.get("slots", [])

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

    def _on_zoom_changed(self, choice: str):
        self.zoom_mode = choice
        self._redraw_canvas()

    def _on_canvas_resize(self, event):
        if self.zoom_mode == "Fit to Screen":
            self._redraw_canvas()

    def _redraw_canvas(self):
        if self._rendered_pil is None:
            self.canvas.delete("all")
            return

        c_w = max(50, self.canvas.winfo_width())
        c_h = max(50, self.canvas.winfo_height())
        orig_w, orig_h = self._rendered_pil.size

        if self.zoom_mode == "Fit to Screen":
            pad = 20
            scale_w = (c_w - pad) / orig_w
            scale_h = (c_h - pad) / orig_h
            scale = max(0.15, min(scale_w, scale_h))
        elif self.zoom_mode == "50%":
            scale = 0.5 / PREVIEW_BASE_SCALE
        elif self.zoom_mode == "75%":
            scale = 0.75 / PREVIEW_BASE_SCALE
        elif self.zoom_mode == "100%":
            scale = 1.0 / PREVIEW_BASE_SCALE
        elif self.zoom_mode == "150%":
            scale = 1.5 / PREVIEW_BASE_SCALE
        else:
            scale = 0.4

        disp_w = int(orig_w * scale)
        disp_h = int(orig_h * scale)
        self._current_canvas_scale = scale * PREVIEW_BASE_SCALE  # Relative to base template coordinates

        resized = self._rendered_pil.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self._displayed_photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        # Center the image on the canvas
        offset_x = max(10, (c_w - disp_w) // 2)
        offset_y = max(10, (c_h - disp_h) // 2)

        self._img_x = offset_x
        self._img_y = offset_y
        self._disp_w = disp_w
        self._disp_h = disp_h

        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self._displayed_photo, tags="sheet_img")
        self.canvas.config(scrollregion=(0, 0, offset_x + disp_w + 20, offset_y + disp_h + 20))

        self._draw_highlights()

    def _draw_highlights(self):
        self.canvas.delete("highlight")
        if not self.selected_slot_id:
            return

        for slot in self._current_layout_slots:
            if slot.get("id") == self.selected_slot_id:
                rx, ry, rw, rh = slot.get("rect", [0, 0, 0, 0])
                sx1 = self._img_x + int(rx * self._current_canvas_scale)
                sy1 = self._img_y + int(ry * self._current_canvas_scale)
                sx2 = sx1 + int(rw * self._current_canvas_scale)
                sy2 = sy1 + int(rh * self._current_canvas_scale)

                # Draw glowing parchment gold highlight rectangle
                self.canvas.create_rectangle(
                    sx1, sy1, sx2, sy2, outline="#e5c158", width=3, dash=(6, 3), tags="highlight"
                )
                break

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
                slot_id = slot.get("id")
                self.selected_slot_id = slot_id
                self._draw_highlights()
                if self.on_slot_clicked:
                    self.on_slot_clicked(slot_id, None)
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
