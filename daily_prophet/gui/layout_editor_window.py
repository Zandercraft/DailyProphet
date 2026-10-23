"""Interactive Visual Layout Editor for The Daily Prophet templates.

Allows users to visually inspect, draw, move, resize, edit, and configure
the content slot bounding boxes across all newspaper layouts, and save
directly back to layout_definitions.json and wireframe masks.
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from ..generate_masks import build_all_layouts

# Type colors
SLOT_COLORS = {
    'headline': ('#8B1E1E', '#FF4D4D'),       # Deep Crimson
    'subheadline': ('#B85D19', '#FFA059'),    # Rust Amber
    'photo': ('#1E5631', '#4DFF88'),          # Forest Emerald Green
    'body': ('#1B365D', '#66A3FF'),           # Ink Navy
    'column': ('#2B4C7E', '#7DB4FF'),         # Column Blue
    'title': ('#4A235A', '#D980FA'),          # Royal Purple
    'ear_box': ('#641E1E', '#FF7070'),        # Dark Maroon
    'quote': ('#996515', '#FFD159'),          # Amber Gold
    'lore': ('#5C3566', '#E284F7'),           # Plum Lore
    'ticker': ('#5A461E', '#E6C687'),         # Bronze
    'banner': ('#28283C', '#A8A8D0'),         # Dark Slate
    'footer': ('#282828', '#B0B0B0')          # Charcoal
}

SLOT_TYPES = list(SLOT_COLORS.keys())


class LayoutEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent=None, initial_layout="layout_1", base_dir="."):
        super().__init__(parent)
        self.base_dir = os.path.abspath(base_dir)
        self.title("The Daily Prophet — Interactive Layout Slot Editor")
        self.geometry("1400x900")
        self.minsize(1100, 700)

        self.defs_path = os.path.join(self.base_dir, "assets", "templates", "layout_definitions.json")
        self.layouts_data = self._load_layouts()

        self.current_layout_key = initial_layout if initial_layout in self.layouts_data else "layout_1"
        self.zoom_level = 0.75  # Start at comfortable view scale

        # State for canvas interaction
        self.raw_bg_image = None
        self.scaled_bg_photo = None
        self.selected_slot_index = None

        # Interaction mode: 'select', 'move', 'resize', 'draw'
        self.drag_mode = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.orig_rect = None
        self.resize_handle = None
        self.drawing_rect = None

        self._setup_ui()
        self._load_layout_into_editor(self.current_layout_key)

    def _load_layouts(self):
        if os.path.isfile(self.defs_path):
            try:
                with open(self.defs_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load layout definitions: {e}")
        return {}

    def _save_layouts(self):
        try:
            with open(self.defs_path, "w", encoding="utf-8") as f:
                json.dump(self.layouts_data, f, indent=2)

            # Automatically rebuild wireframe masks
            build_all_layouts()

            messagebox.showinfo("Saved", "Layout definitions and wireframe masks updated successfully!", parent=self)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save layouts: {e}", parent=self)

    def _setup_ui(self):
        # 1. TOP TOOLBAR
        top_bar = ctk.CTkFrame(self, fg_color=("#2e261f", "#1c1713"), corner_radius=0, height=52)
        top_bar.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            top_bar,
            text="🛠️ LAYOUT SLOT EDITOR",
            font=ctk.CTkFont(family="Georgia", size=16, weight="bold"),
            text_color="#f5ede0"
        ).pack(side="left", padx=16, pady=8)

        # Layout selector
        ctk.CTkLabel(top_bar, text="Active Layout:").pack(side="left", padx=(12, 4))
        layout_keys = [k for k in self.layouts_data.keys() if not k.startswith("additional_")]
        if not layout_keys:
            layout_keys = list(self.layouts_data.keys())

        self.layout_menu = ctk.CTkOptionMenu(
            top_bar,
            values=layout_keys,
            width=170,
            command=self._on_layout_selected
        )
        self.layout_menu.set(self.current_layout_key)
        self.layout_menu.pack(side="left", padx=4)

        # Zoom controls
        zoom_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        zoom_frame.pack(side="left", padx=20)

        ctk.CTkButton(zoom_frame, text="🔍 -", width=42, command=self._zoom_out).pack(side="left", padx=2)
        self.zoom_lbl = ctk.CTkLabel(zoom_frame, text="75%", width=50)
        self.zoom_lbl.pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="🔍 +", width=42, command=self._zoom_in).pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="100%", width=48, command=self._zoom_reset).pack(side="left", padx=4)
        ctk.CTkButton(zoom_frame, text="Fit Width", width=70, command=self._zoom_fit_width).pack(side="left", padx=2)

        # Actions on right
        action_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        action_box.pack(side="right", padx=16)

        ctk.CTkButton(
            action_box,
            text="➕ New Slot (Drag)",
            width=130,
            fg_color="#3d5a45",
            hover_color="#2b4736",
            command=self._activate_draw_mode
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            action_box,
            text="💾 Save & Rebuild Masks",
            width=175,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#8f2d2d",
            hover_color="#6e2020",
            command=self._save_layouts
        ).pack(side="left", padx=4)

        # 2. MAIN SPLIT (Canvas on left, Inspector on right)
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=8, pady=8)

        # LEFT: Scrollable Canvas Frame
        canvas_container = ctk.CTkFrame(main_split)
        canvas_container.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=0)

        # Interactive Canvas with scrollbars
        self.v_scroll = tk.Scrollbar(canvas_container, orient="vertical")
        self.h_scroll = tk.Scrollbar(canvas_container, orient="horizontal")

        self.canvas = tk.Canvas(
            canvas_container,
            bg="#16120e",
            highlightthickness=0,
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set
        )

        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Canvas Mouse Bindings
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        # Pan via Right Click / Middle Click
        self.canvas.bind("<ButtonPress-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._do_pan)
        self.canvas.bind("<ButtonPress-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._do_pan)

        # Mouse wheel zoom / scroll
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        # Keyboard shortcuts
        self.bind("<Delete>", lambda e: self._delete_selected_slot())
        self.bind("<BackSpace>", lambda e: self._delete_selected_slot())
        self.bind("<Up>", lambda e: self._nudge_selected(0, -1 if not e.state & 1 else -10))
        self.bind("<Down>", lambda e: self._nudge_selected(0, 1 if not e.state & 1 else 10))
        self.bind("<Left>", lambda e: self._nudge_selected(-1 if not e.state & 1 else -10, 0))
        self.bind("<Right>", lambda e: self._nudge_selected(1 if not e.state & 1 else 10, 0))

        # RIGHT: Inspector & Slots List
        self.inspector_panel = ctk.CTkFrame(main_split, width=380)
        self.inspector_panel.pack(side="right", fill="both", expand=False, padx=(6, 0), pady=0)
        self.inspector_panel.pack_propagate(False)

        self._setup_inspector()

    def _setup_inspector(self):
        parent = self.inspector_panel

        ctk.CTkLabel(
            parent,
            text="Slot Inspector",
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        # Selected Slot Editor Box
        self.edit_frame = ctk.CTkFrame(parent, fg_color=("#221c16", "#14100c"), corner_radius=6)
        self.edit_frame.pack(fill="x", padx=10, pady=4)

        # Slot ID
        ctk.CTkLabel(self.edit_frame, text="Slot Identifier (ID):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.slot_id_entry = ctk.CTkEntry(self.edit_frame, height=28)
        self.slot_id_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.slot_id_entry.bind("<KeyRelease>", self._on_slot_prop_changed)

        # Slot Label
        ctk.CTkLabel(self.edit_frame, text="Human Label / Name:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.slot_label_entry = ctk.CTkEntry(self.edit_frame, height=28)
        self.slot_label_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.slot_label_entry.bind("<KeyRelease>", self._on_slot_prop_changed)

        # Slot Type
        ctk.CTkLabel(self.edit_frame, text="Slot Content Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.slot_type_menu = ctk.CTkOptionMenu(
            self.edit_frame,
            values=SLOT_TYPES,
            height=28,
            command=self._on_slot_type_selected
        )
        self.slot_type_menu.pack(fill="x", padx=10, pady=(0, 8))

        # Coordinates Frame (X, Y, W, H)
        coord_grid = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        coord_grid.pack(fill="x", padx=10, pady=(0, 10))

        # Row 1: X & Y
        r1 = ctk.CTkFrame(coord_grid, fg_color="transparent")
        r1.pack(fill="x", pady=2)

        c_x = ctk.CTkFrame(r1, fg_color="transparent")
        c_x.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(c_x, text="X (px):", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.x_entry = ctk.CTkEntry(c_x, height=26)
        self.x_entry.pack(fill="x")
        self.x_entry.bind("<KeyRelease>", self._on_coord_typed)

        c_y = ctk.CTkFrame(r1, fg_color="transparent")
        c_y.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(c_y, text="Y (px):", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.y_entry = ctk.CTkEntry(c_y, height=26)
        self.y_entry.pack(fill="x")
        self.y_entry.bind("<KeyRelease>", self._on_coord_typed)

        # Row 2: W & H
        r2 = ctk.CTkFrame(coord_grid, fg_color="transparent")
        r2.pack(fill="x", pady=(4, 2))

        c_w = ctk.CTkFrame(r2, fg_color="transparent")
        c_w.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(c_w, text="Width (px):", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.w_entry = ctk.CTkEntry(c_w, height=26)
        self.w_entry.pack(fill="x")
        self.w_entry.bind("<KeyRelease>", self._on_coord_typed)

        c_h = ctk.CTkFrame(r2, fg_color="transparent")
        c_h.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(c_h, text="Height (px):", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.h_entry = ctk.CTkEntry(c_h, height=26)
        self.h_entry.pack(fill="x")
        self.h_entry.bind("<KeyRelease>", self._on_coord_typed)

        # Delete Button
        ctk.CTkButton(
            self.edit_frame,
            text="🗑️ Delete Selected Slot",
            fg_color="#542525",
            hover_color="#732525",
            height=28,
            command=self._delete_selected_slot
        ).pack(fill="x", padx=10, pady=(2, 10))

        # SLOTS LIST IN ACTIVE LAYOUT
        list_header = ctk.CTkFrame(parent, fg_color="transparent")
        list_header.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            list_header,
            text="All Slots in this Layout:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        self.slots_count_lbl = ctk.CTkLabel(
            list_header,
            text="0 slots",
            font=ctk.CTkFont(size=11),
            text_color="gray70"
        )
        self.slots_count_lbl.pack(side="right")

        self.slots_scroll = ctk.CTkScrollableFrame(parent)
        self.slots_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.slot_btn_items = []

    def _load_layout_into_editor(self, layout_key):
        self.current_layout_key = layout_key
        layout_def = self.layouts_data.get(layout_key, {})
        page_file = layout_def.get("page_file", "")
        full_page_path = os.path.join(self.base_dir, page_file)

        if not os.path.isfile(full_page_path):
            full_page_path = os.path.abspath(page_file)

        if os.path.isfile(full_page_path):
            self.raw_bg_image = Image.open(full_page_path).convert("RGBA")
        else:
            w = layout_def.get("width", 1122)
            h = layout_def.get("height", 1402)
            self.raw_bg_image = Image.new("RGBA", (w, h), (226, 212, 178, 255))

        self.selected_slot_index = None
        self._refresh_canvas()
        self._refresh_slots_list()
        self._clear_inspector()

    def _refresh_canvas(self):
        if not self.raw_bg_image:
            return

        w, h = self.raw_bg_image.size
        sw = int(w * self.zoom_level)
        sh = int(h * self.zoom_level)

        scaled_bg = self.raw_bg_image.resize((sw, sh), Image.Resampling.BILINEAR)
        self.scaled_bg_photo = ImageTk.PhotoImage(scaled_bg)

        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, sw + 80, sh + 80))
        self.canvas.create_image(20, 20, anchor="nw", image=self.scaled_bg_photo, tags="bg")

        # Draw all slots
        slots = self.layouts_data.get(self.current_layout_key, {}).get("slots", [])
        for idx, slot in enumerate(slots):
            self._draw_slot_box(idx, slot)

        # If slot selected, draw selection handles
        if self.selected_slot_index is not None and 0 <= self.selected_slot_index < len(slots):
            self._draw_selection_handles(slots[self.selected_slot_index])

    def _canvas_to_orig(self, cx, cy):
        """Converts canvas pixel coordinates to original image coordinates."""
        ox = (cx - 20) / self.zoom_level
        oy = (cy - 20) / self.zoom_level
        return int(ox), int(oy)

    def _orig_to_canvas(self, ox, oy):
        """Converts original image coordinates to canvas coordinates."""
        cx = 20 + ox * self.zoom_level
        cy = 20 + oy * self.zoom_level
        return cx, cy

    def _draw_slot_box(self, idx, slot):
        rx, ry, rw, rh = slot["rect"]
        stype = slot.get("type", "body")
        slabel = slot.get("label", slot.get("id", f"slot_{idx}"))

        x1, y1 = self._orig_to_canvas(rx, ry)
        x2, y2 = self._orig_to_canvas(rx + rw, ry + rh)

        border_color, light_color = SLOT_COLORS.get(stype, ("#505050", "#FFFFFF"))
        is_selected = (idx == self.selected_slot_index)

        line_width = 3 if is_selected else 2
        line_color = "#FFD700" if is_selected else border_color

        # Box outline
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=line_color,
            width=line_width,
            tags=("slot", f"slot_{idx}")
        )

        # Label tag at top-left
        tag_text = f"[{stype.upper()}] {slabel}"
        tag_bg = self.canvas.create_rectangle(
            x1 + 1, y1 + 1, x1 + min(rw * self.zoom_level - 2, len(tag_text) * 7.5 + 8), y1 + 16,
            fill="#111111",
            outline=line_color,
            tags=("slot", f"slot_{idx}")
        )
        self.canvas.create_text(
            x1 + 4, y1 + 8,
            text=tag_text,
            anchor="w",
            fill="#FFFFFF" if not is_selected else "#FFD700",
            font=("Arial", max(8, int(9 * min(1.2, self.zoom_level)))),
            tags=("slot", f"slot_{idx}")
        )

    def _draw_selection_handles(self, slot):
        rx, ry, rw, rh = slot["rect"]
        x1, y1 = self._orig_to_canvas(rx, ry)
        x2, y2 = self._orig_to_canvas(rx + rw, ry + rh)
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        hs = 6  # Handle size
        handles = [
            ("nw", x1, y1),
            ("n",  mx, y1),
            ("ne", x2, y1),
            ("e",  x2, my),
            ("se", x2, y2),
            ("s",  mx, y2),
            ("sw", x1, y2),
            ("w",  x1, my),
        ]

        for h_id, hx, hy in handles:
            self.canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill="#FFD700",
                outline="#000000",
                width=1,
                tags=("handle", f"handle_{h_id}")
            )

    def _find_handle_at(self, cx, cy):
        """Returns handle name if mouse is over a handle of the selected box."""
        if self.selected_slot_index is None:
            return None
        slots = self.layouts_data.get(self.current_layout_key, {}).get("slots", [])
        if self.selected_slot_index >= len(slots):
            return None

        slot = slots[self.selected_slot_index]
        rx, ry, rw, rh = slot["rect"]
        x1, y1 = self._orig_to_canvas(rx, ry)
        x2, y2 = self._orig_to_canvas(rx + rw, ry + rh)
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        hs = 8
        handles = [
            ("nw", x1, y1),
            ("n",  mx, y1),
            ("ne", x2, y1),
            ("e",  x2, my),
            ("se", x2, y2),
            ("s",  mx, y2),
            ("sw", x1, y2),
            ("w",  x1, my),
        ]

        for h_name, hx, hy in handles:
            if abs(cx - hx) <= hs and abs(cy - hy) <= hs:
                return h_name
        return None

    def _find_slot_at(self, cx, cy):
        """Returns the index of the slot at canvas coordinates, prioritizing smaller slots."""
        ox, oy = self._canvas_to_orig(cx, cy)
        slots = self.layouts_data.get(self.current_layout_key, {}).get("slots", [])

        matching = []
        for idx, s in enumerate(slots):
            rx, ry, rw, rh = s["rect"]
            if rx <= ox <= rx + rw and ry <= oy <= ry + rh:
                matching.append((idx, rw * rh))

        if matching:
            # Sort by area ascending so smaller child slots are picked before giant enclosing containers
            matching = sorted(matching, key=lambda m: m[1])
            return matching[0][0]
        return None

    def _on_canvas_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        # Check if clicking on resize handle of currently selected box
        handle = self._find_handle_at(cx, cy)
        if handle:
            self.drag_mode = "resize"
            self.resize_handle = handle
            self.drag_start_x = cx
            self.drag_start_y = cy
            slots = self.layouts_data[self.current_layout_key]["slots"]
            self.orig_rect = list(slots[self.selected_slot_index]["rect"])
            return

        # Check if clicking inside an existing slot box
        slot_idx = self._find_slot_at(cx, cy)
        if slot_idx is not None:
            self.selected_slot_index = slot_idx
            self.drag_mode = "move"
            self.drag_start_x = cx
            self.drag_start_y = cy
            slots = self.layouts_data[self.current_layout_key]["slots"]
            self.orig_rect = list(slots[self.selected_slot_index]["rect"])
            self._update_inspector_with_slot(slots[slot_idx])
            self._highlight_active_slot_button(slot_idx)
            self._refresh_canvas()
            return

        # If clicking in empty space, start drawing a new slot
        self.selected_slot_index = None
        self._clear_inspector()
        self.drag_mode = "draw"
        self.drag_start_x = cx
        self.drag_start_y = cy
        self._refresh_canvas()

    def _on_canvas_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if self.drag_mode == "move" and self.selected_slot_index is not None:
            dx = int((cx - self.drag_start_x) / self.zoom_level)
            dy = int((cy - self.drag_start_y) / self.zoom_level)

            new_x = max(0, self.orig_rect[0] + dx)
            new_y = max(0, self.orig_rect[1] + dy)

            slots = self.layouts_data[self.current_layout_key]["slots"]
            slots[self.selected_slot_index]["rect"][0] = new_x
            slots[self.selected_slot_index]["rect"][1] = new_y

            self._update_coords_display(slots[self.selected_slot_index]["rect"])
            self._refresh_canvas()

        elif self.drag_mode == "resize" and self.selected_slot_index is not None:
            dx = int((cx - self.drag_start_x) / self.zoom_level)
            dy = int((cy - self.drag_start_y) / self.zoom_level)

            ox, oy, ow, oh = self.orig_rect
            nx, ny, nw, nh = ox, oy, ow, oh

            if "w" in self.resize_handle:
                nx = min(ox + dx, ox + ow - 10)
                nw = ow - (nx - ox)
            if "e" in self.resize_handle:
                nw = max(10, ow + dx)
            if "n" in self.resize_handle:
                ny = min(oy + dy, oy + oh - 10)
                nh = oh - (ny - oy)
            if "s" in self.resize_handle:
                nh = max(10, oh + dy)

            slots = self.layouts_data[self.current_layout_key]["slots"]
            slots[self.selected_slot_index]["rect"] = [int(nx), int(ny), int(nw), int(nh)]

            self._update_coords_display(slots[self.selected_slot_index]["rect"])
            self._refresh_canvas()

        elif self.drag_mode == "draw":
            # Live rubber-band preview
            self.canvas.delete("rubber_band")
            self.canvas.create_rectangle(
                self.drag_start_x, self.drag_start_y, cx, cy,
                outline="#FFD700",
                dash=(4, 4),
                width=2,
                tags="rubber_band"
            )

    def _on_canvas_release(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if self.drag_mode == "draw":
            self.canvas.delete("rubber_band")
            ox1, oy1 = self._canvas_to_orig(self.drag_start_x, self.drag_start_y)
            ox2, oy2 = self._canvas_to_orig(cx, cy)

            rx = min(ox1, ox2)
            ry = min(oy1, oy2)
            rw = abs(ox2 - ox1)
            rh = abs(oy2 - oy1)

            if rw > 15 and rh > 15:
                # Create a new slot
                slots = self.layouts_data[self.current_layout_key]["slots"]
                new_idx = len(slots) + 1
                new_slot = {
                    "id": f"slot_{new_idx}",
                    "type": "body",
                    "rect": [rx, ry, rw, rh],
                    "label": f"Custom Slot {new_idx}"
                }
                slots.append(new_slot)
                self.selected_slot_index = len(slots) - 1
                self._update_inspector_with_slot(new_slot)
                self._refresh_slots_list()
                self._highlight_active_slot_button(self.selected_slot_index)

        self.drag_mode = None
        self.resize_handle = None
        self.orig_rect = None
        self._refresh_canvas()

    def _on_canvas_motion(self, event):
        """Changes cursor when hovering over resize handles."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        h = self._find_handle_at(cx, cy)
        cursor_map = {
            "nw": "size_nw_se", "se": "size_nw_se",
            "ne": "size_ne_sw", "sw": "size_ne_sw",
            "n": "size_ns", "s": "size_ns",
            "w": "size_we", "e": "size_we"
        }
        self.canvas.config(cursor=cursor_map.get(h, "arrow"))

    def _start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_mousewheel(self, event):
        if event.state & 4:  # Ctrl key pressed -> zoom
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _zoom_in(self):
        self.zoom_level = min(2.5, self.zoom_level + 0.15)
        self.zoom_lbl.configure(text=f"{int(self.zoom_level * 100)}%")
        self._refresh_canvas()

    def _zoom_out(self):
        self.zoom_level = max(0.25, self.zoom_level - 0.15)
        self.zoom_lbl.configure(text=f"{int(self.zoom_level * 100)}%")
        self._refresh_canvas()

    def _zoom_reset(self):
        self.zoom_level = 1.0
        self.zoom_lbl.configure(text="100%")
        self._refresh_canvas()

    def _zoom_fit_width(self):
        c_w = self.canvas.winfo_width() - 60
        if c_w > 100 and self.raw_bg_image:
            self.zoom_level = max(0.25, min(2.0, c_w / self.raw_bg_image.width))
            self.zoom_lbl.configure(text=f"{int(self.zoom_level * 100)}%")
            self._refresh_canvas()

    def _on_layout_selected(self, choice):
        self._load_layout_into_editor(choice)

    def _update_inspector_with_slot(self, slot):
        self.slot_id_entry.delete(0, "end")
        self.slot_id_entry.insert(0, slot.get("id", ""))

        self.slot_label_entry.delete(0, "end")
        self.slot_label_entry.insert(0, slot.get("label", ""))

        stype = slot.get("type", "body")
        if stype in SLOT_TYPES:
            self.slot_type_menu.set(stype)

        self._update_coords_display(slot["rect"])

    def _update_coords_display(self, rect):
        rx, ry, rw, rh = rect
        for entry, val in [(self.x_entry, rx), (self.y_entry, ry), (self.w_entry, rw), (self.h_entry, rh)]:
            entry.delete(0, "end")
            entry.insert(0, str(int(val)))

    def _clear_inspector(self):
        self.slot_id_entry.delete(0, "end")
        self.slot_label_entry.delete(0, "end")
        self.x_entry.delete(0, "end")
        self.y_entry.delete(0, "end")
        self.w_entry.delete(0, "end")
        self.h_entry.delete(0, "end")
        self._highlight_active_slot_button(None)

    def _on_slot_prop_changed(self, event=None):
        if self.selected_slot_index is None:
            return
        slots = self.layouts_data[self.current_layout_key]["slots"]
        slot = slots[self.selected_slot_index]

        slot["id"] = self.slot_id_entry.get().strip()
        slot["label"] = self.slot_label_entry.get().strip()

        self._refresh_slots_list()
        self._refresh_canvas()

    def _on_slot_type_selected(self, choice):
        if self.selected_slot_index is None:
            return
        slots = self.layouts_data[self.current_layout_key]["slots"]
        slots[self.selected_slot_index]["type"] = choice
        self._refresh_slots_list()
        self._refresh_canvas()

    def _on_coord_typed(self, event=None):
        if self.selected_slot_index is None:
            return
        try:
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())
            w = max(10, int(self.w_entry.get()))
            h = max(10, int(self.h_entry.get()))
            slots = self.layouts_data[self.current_layout_key]["slots"]
            slots[self.selected_slot_index]["rect"] = [x, y, w, h]
            self._refresh_canvas()
        except ValueError:
            pass

    def _nudge_selected(self, dx, dy):
        if self.selected_slot_index is None:
            return
        slots = self.layouts_data[self.current_layout_key]["slots"]
        rect = slots[self.selected_slot_index]["rect"]
        rect[0] = max(0, rect[0] + dx)
        rect[1] = max(0, rect[1] + dy)
        self._update_coords_display(rect)
        self._refresh_canvas()

    def _delete_selected_slot(self):
        if self.selected_slot_index is None:
            return
        slots = self.layouts_data[self.current_layout_key]["slots"]
        del slots[self.selected_slot_index]
        self.selected_slot_index = None
        self._clear_inspector()
        self._refresh_slots_list()
        self._refresh_canvas()

    def _activate_draw_mode(self):
        self.selected_slot_index = None
        self._clear_inspector()
        self._refresh_canvas()
        messagebox.showinfo("Draw Slot", "Click and drag anywhere on the parchment canvas to draw a new bounding box.", parent=self)

    def _refresh_slots_list(self):
        for widget in self.slots_scroll.winfo_children():
            widget.destroy()

        slots = self.layouts_data.get(self.current_layout_key, {}).get("slots", [])
        self.slots_count_lbl.configure(text=f"{len(slots)} slots")
        self.slot_btn_items = []

        for idx, s in enumerate(slots):
            stype = s.get("type", "body")
            slabel = s.get("label", s.get("id", f"slot_{idx}"))
            rx, ry, rw, rh = s["rect"]

            bg_c = "#33261d" if idx == self.selected_slot_index else "#1c1713"
            item_frame = ctk.CTkFrame(self.slots_scroll, fg_color=bg_c, corner_radius=4)
            item_frame.pack(fill="x", pady=2)

            color_badge, _ = SLOT_COLORS.get(stype, ("#555555", "#FFFFFF"))
            badge = ctk.CTkLabel(item_frame, text=f" {stype.upper()[:4]} ", fg_color=color_badge, text_color="#FFFFFF", font=ctk.CTkFont(size=9, weight="bold"), corner_radius=3)
            badge.pack(side="left", padx=4, pady=4)

            btn = ctk.CTkButton(
                item_frame,
                text=f"{slabel} ({rw}x{rh})",
                font=ctk.CTkFont(size=11),
                anchor="w",
                fg_color="transparent",
                hover_color="#3d342a",
                command=lambda i=idx: self._select_slot_by_index(i)
            )
            btn.pack(side="left", fill="x", expand=True, padx=4)
            self.slot_btn_items.append(item_frame)

    def _highlight_active_slot_button(self, active_idx):
        for i, frame in enumerate(self.slot_btn_items):
            frame.configure(fg_color="#3d2a1c" if i == active_idx else "#1c1713")

    def _select_slot_by_index(self, idx):
        self.selected_slot_index = idx
        slots = self.layouts_data[self.current_layout_key]["slots"]
        self._update_inspector_with_slot(slots[idx])
        self._highlight_active_slot_button(idx)
        self._refresh_canvas()


def open_layout_editor(initial_layout="layout_1", base_dir="."):
    """Convenience launcher for the Layout Slot Editor window."""
    editor = LayoutEditorWindow(initial_layout=initial_layout, base_dir=base_dir)
    return editor
