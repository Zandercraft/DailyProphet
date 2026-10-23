"""Interactive Visual Layout Editor for The Daily Prophet templates.

Allows users to visually inspect, draw, move, resize, edit, and configure
the content slot bounding boxes across all newspaper layouts.

Supports:
- Saving directly to the active project issue (.prophet format)
- Saving to global templates (layout_definitions.json with auto .bak backup)
- Adding new custom templates (with custom background pages)
- Removing custom templates
- Restoring factory shipped defaults
"""
import os
import shutil
import json
import copy
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk

from ..generate_masks import (
    load_layout_definitions,
    save_global_layout_definitions,
    generate_wireframe_mask_for_layout,
    restore_factory_templates,
    build_all_layouts,
    GLOBAL_LAYOUTS_FILE,
    GLOBAL_BACKUP_FILE,
    SHIPPED_DEFAULTS_FILE
)
from ..template_package import (
    create_template_package,
    load_template_package,
    load_all_installed_templates,
    save_installed_template,
    delete_installed_template,
    restore_template_from_shipped_or_backup,
    is_layout_modified,
    INSTALLED_TEMPLATES_DIR,
    SHIPPED_TEMPLATES_DIR
)

# Color palettes for slot types
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
BUILTIN_SHIPPED_LAYOUTS = [f"layout_{i}" for i in range(1, 10)]


class LayoutEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent=None, initial_layout="layout_1", edition=None, on_project_save=None, on_global_change=None, base_dir="."):
        super().__init__(parent)
        self.parent = parent
        self.base_dir = os.path.abspath(base_dir)
        self.edition = edition
        self.on_project_save = on_project_save
        self.on_global_change = on_global_change

        self.title("The Daily Prophet — Interactive Layout Slot Editor")
        self.geometry("1420x920")
        self.minsize(1100, 700)

        # Set Window Icon
        ico_path = os.path.join(self.base_dir, "assets", "logo.ico")
        if os.path.exists(ico_path):
            try:
                self.after(100, lambda: self.iconbitmap(ico_path))
            except Exception:
                pass

        # Force window to the foreground and focus immediately
        if parent:
            self.transient(parent)
        self.lift()
        self.attributes("-topmost", True)
        self.after(80, lambda: self._finalize_focus())

        self.defs_path = os.path.join(self.base_dir, GLOBAL_LAYOUTS_FILE)
        self.global_layouts = load_layout_definitions(defs_path=self.defs_path, base_dir=self.base_dir)
        self.project_custom_layouts = dict(self.edition.custom_layouts) if (self.edition and hasattr(self.edition, "custom_layouts")) else {}

        # Working dictionary of layouts: global defaults overlaid with any project-level custom slots
        self.layouts_data = {}
        for k, v in self.global_layouts.items():
            self.layouts_data[k] = copy.deepcopy(v)
        for k, v in self.project_custom_layouts.items():
            self.layouts_data[k] = copy.deepcopy(v)

        # Active layout
        self.current_layout_key = initial_layout if initial_layout in self.layouts_data else "layout_1"
        self.zoom_level = 0.75

        # Canvas & drag state
        self.raw_bg_image = None
        self.scaled_bg_photo = None
        self.selected_slot_index = None

        self.drag_mode = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.orig_rect = None
        self.resize_handle = None
        self.drawing_rect = None

        # By default on first open, turn off the checkbox to save to global template on editing,
        # even if the project manifest had it as true.
        self.save_to_global_var = ctk.BooleanVar(value=False)

        self._setup_ui()
        self._load_layout_into_editor(self.current_layout_key)

    def _finalize_focus(self):
        try:
            self.attributes("-topmost", False)
            self.focus_force()
        except Exception:
            pass

    def _setup_ui(self):
        # 1. TOP TOOLBAR
        top_bar = ctk.CTkFrame(self, fg_color=("#2e261f", "#1c1713"), corner_radius=0, height=56)
        top_bar.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            top_bar,
            text="🛠️ LAYOUT SLOT EDITOR",
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
            text_color="#f5ede0"
        ).pack(side="left", padx=14, pady=8)

        # Layout selector
        ctk.CTkLabel(top_bar, text="Layout:").pack(side="left", padx=(10, 4))
        layout_keys = [k for k in self.layouts_data.keys() if not k.startswith("additional_")]
        if not layout_keys:
            layout_keys = list(self.layouts_data.keys())

        self.layout_menu = ctk.CTkOptionMenu(
            top_bar,
            values=layout_keys,
            width=160,
            command=self._on_layout_selected
        )
        self.layout_menu.set(self.current_layout_key)
        self.layout_menu.pack(side="left", padx=4)

        # Scope badge (Project-Specific vs Global)
        self.scope_badge = ctk.CTkLabel(
            top_bar,
            text="Global Template",
            fg_color="#3d342a",
            text_color="#c2b6a4",
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        self.scope_badge.pack(side="left", padx=6)

        # Template Management buttons (Add, Import, Export, Delete, Reset)
        mgmt_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        mgmt_box.pack(side="left", padx=8)

        ctk.CTkButton(
            mgmt_box,
            text="➕ New",
            width=65,
            fg_color="#34495e",
            hover_color="#2c3e50",
            font=ctk.CTkFont(size=11),
            command=self._show_add_template_dialog
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            mgmt_box,
            text="📥 Import",
            width=70,
            fg_color="#3d4f40",
            hover_color="#2f3d32",
            font=ctk.CTkFont(size=11),
            command=self._import_template_package
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            mgmt_box,
            text="📤 Export",
            width=70,
            fg_color="#3d4f40",
            hover_color="#2f3d32",
            font=ctk.CTkFont(size=11),
            command=self._export_template_package
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            mgmt_box,
            text="🗑️ Delete",
            width=70,
            fg_color="#542525",
            hover_color="#732525",
            font=ctk.CTkFont(size=11),
            command=self._confirm_delete_template
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            mgmt_box,
            text="🔄 Reset",
            width=65,
            fg_color="#4a3e2c",
            hover_color="#382e20",
            font=ctk.CTkFont(size=11),
            command=self._show_reset_dialog
        ).pack(side="left", padx=2)

        # Zoom controls
        zoom_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        zoom_frame.pack(side="left", padx=12)

        ctk.CTkButton(zoom_frame, text="🔍 -", width=38, command=self._zoom_out).pack(side="left", padx=2)
        self.zoom_lbl = ctk.CTkLabel(zoom_frame, text="75%", width=46)
        self.zoom_lbl.pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="🔍 +", width=38, command=self._zoom_in).pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="100%", width=46, command=self._zoom_reset).pack(side="left", padx=2)
        ctk.CTkButton(zoom_frame, text="Fit Width", width=68, command=self._zoom_fit_width).pack(side="left", padx=2)

        # Actions on right: Save to Project (Primary) & Save to Global
        action_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        action_box.pack(side="right", padx=12)

        ctk.CTkButton(
            action_box,
            text="➕ New Slot (Drag)",
            width=120,
            fg_color="#3d5a45",
            hover_color="#2b4736",
            command=self._activate_draw_mode
        ).pack(side="left", padx=3)

        # Checkbox to also update global template (defaults to OFF on open)
        self.save_global_check = ctk.CTkCheckBox(
            action_box,
            text="Also update global template",
            variable=self.save_to_global_var,
            font=ctk.CTkFont(size=11),
            text_color="#c2b6a4",
            checkbox_width=18,
            checkbox_height=18
        )
        self.save_global_check.pack(side="left", padx=6)

        # Primary default action: Save to this project
        ctk.CTkButton(
            action_box,
            text="💾 Save Slots",
            width=120,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#8f2d2d",
            hover_color="#6e2020",
            command=self._save_to_current_project
        ).pack(side="left", padx=4)

        # Global template save action
        ctk.CTkButton(
            action_box,
            text="🌐 Save Global Template",
            width=165,
            font=ctk.CTkFont(size=11),
            fg_color="#2c3e50",
            hover_color="#1a252f",
            command=self._save_to_global_template
        ).pack(side="left", padx=3)

        # 2. MAIN SPLIT (Canvas on left, Inspector on right)
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=8, pady=8)

        # LEFT: Scrollable Canvas Frame
        canvas_container = ctk.CTkFrame(main_split)
        canvas_container.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=0)

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

        # Mouse Bindings
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        # Pan via Right Click / Middle Click
        self.canvas.bind("<ButtonPress-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._do_pan)
        self.canvas.bind("<ButtonPress-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._do_pan)

        # Mouse wheel zoom
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

        # Delete Slot Button
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

    def _update_scope_badge(self):
        """Updates indicator showing whether active layout has modifications comparing against local template."""
        active_layout = self.layouts_data.get(self.current_layout_key, {})
        global_layout = self.global_layouts.get(self.current_layout_key, {})
        is_mod = is_layout_modified(active_layout, global_layout)
        is_bundled = active_layout.get("bundled", self.current_layout_key in BUILTIN_SHIPPED_LAYOUTS)

        if is_mod:
            self.scope_badge.configure(
                text="📌 Modified",
                fg_color="#8f4a2d",
                text_color="#ffffff"
            )
        elif is_bundled:
            self.scope_badge.configure(
                text="🔒 Bundled Template",
                fg_color="#3d342a",
                text_color="#c2b6a4"
            )
        else:
            self.scope_badge.configure(
                text="🌐 Custom Template",
                fg_color="#2b3e50",
                text_color="#c2b6a4"
            )

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
        self._update_scope_badge()
        self._refresh_canvas()
        self._refresh_slots_list()
        self._clear_inspector()

    def _refresh_layout_dropdown(self):
        """Refreshes the dropdown list of layouts."""
        keys = [k for k in self.layouts_data.keys() if not k.startswith("additional_")]
        self.layout_menu.configure(values=keys)
        if self.current_layout_key in keys:
            self.layout_menu.set(self.current_layout_key)
        elif keys:
            self.layout_menu.set(keys[0])
            self._load_layout_into_editor(keys[0])

    def _on_layout_selected(self, choice):
        self._load_layout_into_editor(choice)

    # ------------------ SAVING AND PERSISTENCE ------------------

    def _save_to_current_project(self):
        """Saves current layout slots into the active issue package (.prophet)."""
        active_layout = self.layouts_data.get(self.current_layout_key)
        if not active_layout:
            return

        self.project_custom_layouts[self.current_layout_key] = copy.deepcopy(active_layout)
        if self.edition:
            self.edition.custom_layouts[self.current_layout_key] = copy.deepcopy(active_layout)

        # Generate wireframe mask for this layout
        generate_wireframe_mask_for_layout(
            self.current_layout_key,
            active_layout,
            base_dir=self.base_dir
        )

        # If checkbox is checked, also save to global template
        saved_globally = False
        if self.save_to_global_var.get():
            self._save_to_global_template(quiet=True)
            saved_globally = True

        self._update_scope_badge()

        if callable(self.on_project_save):
            self.on_project_save()

        glob_msg = "\n\n(Also updated and saved to global installed template)." if saved_globally else ""
        messagebox.showinfo(
            "Saved to Issue",
            f"Layout slots for '{active_layout.get('label', self.current_layout_key)}' saved directly to this newspaper issue.{glob_msg}\n\n"
            "These custom slots will be preserved in your .prophet project file and used for rendering and exports.",
            parent=self
        )

    def _export_template_package(self):
        """Exports the active layout to a standalone .prophettemplate file (with compatibility options)."""
        active_layout = self.layouts_data.get(self.current_layout_key)
        if not active_layout:
            return

        out_path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Export Template - {active_layout.get('label', self.current_layout_key)}",
            defaultextension=".prophettemplate",
            initialfile=f"{self.current_layout_key}.prophettemplate",
            filetypes=[
                ("The Daily Prophet Template Package (*.prophettemplate)", "*.prophettemplate"),
                ("Legacy Compatibility Template v1.0 (*.prophettemplate)", "*.prophettemplate"),
                ("All Files", "*.*")
            ]
        )
        if out_path:
            try:
                pkg_file = create_template_package(
                    self.current_layout_key,
                    active_layout,
                    out_path,
                    target_version=CURRENT_TEMPLATE_VERSION,
                    base_dir=self.base_dir
                )
                messagebox.showinfo(
                    "Export Successful",
                    f"Template packaged successfully as a single self-contained file (v{CURRENT_TEMPLATE_VERSION}):\n\n{os.path.basename(pkg_file)}",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export template package: {e}", parent=self)

    def _import_template_package(self):
        """Imports an external .prophettemplate file into installed templates and loads it."""
        in_path = filedialog.askopenfilename(
            parent=self,
            title="Import .prophettemplate File",
            filetypes=[("The Daily Prophet Template Package", "*.prophettemplate"), ("All Files", "*.*")]
        )
        if in_path:
            try:
                # Copy into assets/templates/installed/
                dest_dir = os.path.join(self.base_dir, INSTALLED_TEMPLATES_DIR)
                os.makedirs(dest_dir, exist_ok=True)
                dest_file = os.path.join(dest_dir, os.path.basename(in_path))
                if os.path.abspath(in_path) != os.path.abspath(dest_file):
                    shutil.copy2(in_path, dest_file)

                # Unpack and load
                loaded_def = load_template_package(dest_file, base_dir=self.base_dir)
                tid = loaded_def.get("id", os.path.splitext(os.path.basename(dest_file))[0])

                self.global_layouts[tid] = loaded_def
                self.layouts_data[tid] = copy.deepcopy(loaded_def)

                self._refresh_layout_dropdown()
                self._load_layout_into_editor(tid)

                if callable(self.on_global_change):
                    self.on_global_change()

                messagebox.showinfo(
                    "Import Complete",
                    f"Template '{loaded_def.get('label', tid)}' imported and activated successfully!",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import template package: {e}", parent=self)

    def _save_to_global_template(self, quiet: bool = False):
        """Saves layout slots to an individual .prophettemplate file with auto-backup."""
        active_layout = self.layouts_data.get(self.current_layout_key)
        if not active_layout:
            return

        # Update global layouts dict
        self.global_layouts[self.current_layout_key] = copy.deepcopy(active_layout)
        if not self.current_layout_key.startswith("additional_"):
            alias_key = f"additional_{self.current_layout_key}"
            self.global_layouts[alias_key] = copy.deepcopy(active_layout)

        # Save to disk as .prophettemplate with automatic .bak backup
        try:
            save_installed_template(self.current_layout_key, active_layout, base_dir=self.base_dir)
            save_global_layout_definitions(self.global_layouts, defs_path=self.defs_path, base_dir=self.base_dir)
        except Exception as e:
            if not quiet:
                messagebox.showerror("Error", f"Failed to save template package: {e}", parent=self)
            return

        # Rebuild wireframe mask
        generate_wireframe_mask_for_layout(
            self.current_layout_key,
            active_layout,
            base_dir=self.base_dir
        )

        if callable(self.on_global_change):
            self.on_global_change()

        if not quiet:
            messagebox.showinfo(
                "Saved to Global Templates",
                f"Template '{active_layout.get('label', self.current_layout_key)}' saved globally!\n\n"
                f"Saved to assets/templates/installed/{self.current_layout_key}.prophettemplate\n"
                f"(A backup copy is preserved as {self.current_layout_key}.prophettemplate.bak).\n\n"
                "All new issues using this layout will automatically use these updated slots.",
                parent=self
            )

    def _show_reset_dialog(self):
        """Allows resetting project-specific slots or factory shipped defaults."""
        has_project_override = self.current_layout_key in self.project_custom_layouts

        msg = f"Reset options for '{self.current_layout_key}':\n\n"
        if has_project_override:
            msg += "1. Reset Issue Slots: Revert this issue's custom slots back to the global template.\n"
        msg += "2. Reset Global Factory Defaults: Restore all shipped templates back to original factory values."

        dialog = ctk.CTkToplevel(self)
        dialog.title("Reset Layout Slots")
        dialog.geometry("520x260")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="🔄 Reset Layout Slots",
            font=ctk.CTkFont(family="Georgia", size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            dialog,
            text=msg,
            justify="left",
            wraplength=480
        ).pack(anchor="w", padx=20, pady=8)

        btn_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(16, 10))

        if has_project_override:
            def reset_project():
                del self.project_custom_layouts[self.current_layout_key]
                if self.edition and self.current_layout_key in self.edition.custom_layouts:
                    del self.edition.custom_layouts[self.current_layout_key]
                self.layouts_data[self.current_layout_key] = copy.deepcopy(self.global_layouts[self.current_layout_key])
                self._load_layout_into_editor(self.current_layout_key)
                if callable(self.on_project_save):
                    self.on_project_save()
                dialog.destroy()
                messagebox.showinfo("Reset Complete", "Reverted issue slots to the global template default.", parent=self)

            ctk.CTkButton(
                btn_bar,
                text="Revert Issue Slots",
                fg_color="#8f2d2d",
                hover_color="#6e2020",
                command=reset_project
            ).pack(side="left", padx=4)

        def restore_factory():
            confirm = messagebox.askyesno(
                "Confirm Factory Reset",
                "This will restore all shipped templates from the factory source defaults. Any global edits will be reset. Proceed?",
                parent=dialog
            )
            if not confirm:
                return
            try:
                restored = restore_factory_templates(defs_path=self.defs_path, base_dir=self.base_dir)
                self.global_layouts = restored
                for k, v in restored.items():
                    if k not in self.project_custom_layouts:
                        self.layouts_data[k] = copy.deepcopy(v)
                self._load_layout_into_editor(self.current_layout_key)
                if callable(self.on_global_change):
                    self.on_global_change()
                dialog.destroy()
                messagebox.showinfo("Factory Reset Complete", "Global templates restored to original factory defaults.", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore factory defaults: {e}", parent=dialog)

        ctk.CTkButton(
            btn_bar,
            text="Restore Factory Defaults",
            fg_color="#4a3e2c",
            hover_color="#382e20",
            command=restore_factory
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="Cancel",
            fg_color="#333333",
            hover_color="#444444",
            command=dialog.destroy
        ).pack(side="right", padx=4)

    # ------------------ ADD / REMOVE CUSTOM TEMPLATES ------------------

    def _show_add_template_dialog(self):
        """Dialog to create a new layout template from an image file."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Custom Layout Template")
        dialog.geometry("560x440")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="➕ Add New Custom Template",
            font=ctk.CTkFont(family="Georgia", size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(16, 8))

        ctk.CTkLabel(dialog, text="Template Display Name:").pack(anchor="w", padx=20, pady=(4, 2))
        name_entry = ctk.CTkEntry(dialog, placeholder_text="e.g., Evening Special Broadsheet")
        name_entry.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(dialog, text="Template Identifier (letters, numbers, underscores):").pack(anchor="w", padx=20, pady=(4, 2))
        id_entry = ctk.CTkEntry(dialog, placeholder_text="e.g., custom_evening_1")
        id_entry.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(dialog, text="Background Page Image (PNG or JPG):").pack(anchor="w", padx=20, pady=(4, 2))
        img_row = ctk.CTkFrame(dialog, fg_color="transparent")
        img_row.pack(fill="x", padx=20, pady=(0, 12))

        img_entry = ctk.CTkEntry(img_row, placeholder_text="Path to full-page background parchment image")
        img_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def browse_img():
            fn = filedialog.askopenfilename(
                title="Select Newspaper Background Page Image",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg"), ("All Files", "*.*")],
                parent=dialog
            )
            if fn:
                img_entry.delete(0, "end")
                img_entry.insert(0, fn)
                # Auto suggest id if blank
                if not id_entry.get().strip():
                    clean_name = os.path.splitext(os.path.basename(fn))[0].lower().replace(" ", "_").replace("-", "_")
                    id_entry.insert(0, f"custom_{clean_name}")
                if not name_entry.get().strip():
                    name_entry.insert(0, os.path.splitext(os.path.basename(fn))[0].title())

        ctk.CTkButton(img_row, text="Browse...", width=90, command=browse_img).pack(side="right")

        dim_lbl = ctk.CTkLabel(dialog, text="Dimensions: Will be automatically detected from image.", font=ctk.CTkFont(size=11), text_color="gray70")
        dim_lbl.pack(anchor="w", padx=20, pady=4)

        def create_template():
            label = name_entry.get().strip()
            tid = id_entry.get().strip()
            img_path = img_entry.get().strip()

            if not label or not tid or not img_path:
                messagebox.showwarning("Missing Fields", "Please provide a name, identifier, and image path.", parent=dialog)
                return

            if not os.path.isfile(img_path):
                messagebox.showerror("File Error", f"Image file not found: {img_path}", parent=dialog)
                return

            # Clean id
            tid = "".join(c if c.isalnum() or c == '_' else '_' for c in tid.lower())
            if tid in self.layouts_data:
                messagebox.showerror("Conflict", f"A template with ID '{tid}' already exists.", parent=dialog)
                return

            # Measure image
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception as e:
                messagebox.showerror("Image Error", f"Could not read image: {e}", parent=dialog)
                return

            # Copy image into assets/templates/pages/
            dest_dir = os.path.join(self.base_dir, "assets", "templates", "pages")
            os.makedirs(dest_dir, exist_ok=True)
            dest_name = f"{tid}_{os.path.basename(img_path)}"
            dest_path = os.path.join(dest_dir, dest_name)
            try:
                shutil.copy2(img_path, dest_path)
                rel_page_file = f"assets/templates/pages/{dest_name}"
            except Exception:
                rel_page_file = img_path

            # Generate default sensible slots for the new template
            default_slots = [
                {'id': 'masthead_title', 'type': 'title', 'rect': [int(w * 0.1), int(h * 0.02), int(w * 0.8), int(h * 0.08)], 'label': 'Masthead Title'},
                {'id': 'ear_left', 'type': 'ear_box', 'rect': [int(w * 0.03), int(h * 0.02), int(w * 0.06), int(h * 0.08)], 'label': 'Left Ear'},
                {'id': 'ear_right', 'type': 'ear_box', 'rect': [int(w * 0.91), int(h * 0.02), int(w * 0.06), int(h * 0.08)], 'label': 'Right Ear'},
                {'id': 'ticker_bar', 'type': 'ticker', 'rect': [int(w * 0.03), int(h * 0.11), int(w * 0.94), int(h * 0.03)], 'label': 'Ticker Bar'},
                {'id': 'main_headline', 'type': 'headline', 'rect': [int(w * 0.03), int(h * 0.15), int(w * 0.94), int(h * 0.05)], 'label': 'Main Headline'},
                {'id': 'hero_photo', 'type': 'photo', 'rect': [int(w * 0.25), int(h * 0.22), int(w * 0.5), int(h * 0.28)], 'label': 'Hero Center Photo'},
                {'id': 'lead_body', 'type': 'body', 'rect': [int(w * 0.25), int(h * 0.51), int(w * 0.5), int(h * 0.16)], 'label': 'Hero Story Body'},
                {'id': 'side_col_left', 'type': 'column', 'rect': [int(w * 0.03), int(h * 0.22), int(w * 0.2), int(h * 0.45)], 'label': 'Left Column'},
                {'id': 'side_col_right', 'type': 'column', 'rect': [int(w * 0.77), int(h * 0.22), int(w * 0.2), int(h * 0.45)], 'label': 'Right Column'},
                {'id': 'lore_box_1', 'type': 'lore', 'rect': [int(w * 0.03), int(h * 0.69), int(w * 0.3), int(h * 0.26)], 'label': 'Lower Notice 1'},
                {'id': 'lore_box_2', 'type': 'lore', 'rect': [int(w * 0.35), int(h * 0.69), int(w * 0.3), int(h * 0.26)], 'label': 'Lower Notice 2'},
                {'id': 'lore_box_3', 'type': 'lore', 'rect': [int(w * 0.67), int(h * 0.69), int(w * 0.3), int(h * 0.26)], 'label': 'Lower Notice 3'},
                {'id': 'footer', 'type': 'footer', 'rect': [int(w * 0.03), int(h * 0.96), int(w * 0.94), int(h * 0.025)], 'label': 'Bottom Footer'}
            ]

            new_layout_def = {
                'page_file': rel_page_file,
                'width': w,
                'height': h,
                'label': label,
                'slots': default_slots
            }

            self.global_layouts[tid] = new_layout_def
            self.layouts_data[tid] = copy.deepcopy(new_layout_def)

            # Save as individual .prophettemplate file and register
            save_installed_template(tid, new_layout_def, base_dir=self.base_dir)
            save_global_layout_definitions(self.global_layouts, defs_path=self.defs_path, base_dir=self.base_dir)
            generate_wireframe_mask_for_layout(tid, new_layout_def, base_dir=self.base_dir)

            self._refresh_layout_dropdown()
            self._load_layout_into_editor(tid)

            if callable(self.on_global_change):
                self.on_global_change()

            dialog.destroy()
            messagebox.showinfo(
                "Success",
                f"Custom template '{label}' created as '{tid}.prophettemplate' and opened in editor!",
                parent=self
            )

        action_row = ctk.CTkFrame(dialog, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(16, 12))

        ctk.CTkButton(
            action_row,
            text="Create Template",
            fg_color="#3d5a45",
            hover_color="#2b4736",
            command=create_template
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            action_row,
            text="Cancel",
            fg_color="#333333",
            hover_color="#444444",
            command=dialog.destroy
        ).pack(side="right", padx=4)

    def _confirm_delete_template(self):
        """Deletes a user-created template. Bundled templates cannot be deleted."""
        active_layout = self.layouts_data.get(self.current_layout_key, {})
        if active_layout.get("bundled", False) or self.current_layout_key in BUILTIN_SHIPPED_LAYOUTS:
            messagebox.showwarning(
                "Cannot Delete Bundled Template",
                f"'{self.current_layout_key}' is a pre-included bundled template and cannot be deleted.\n\n"
                "You can freely modify its slots or click 'Reset' to restore factory defaults.",
                parent=self
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Delete Template",
            f"Are you sure you want to delete custom template '{self.current_layout_key}.prophettemplate'?\n\nThis cannot be undone.",
            parent=self
        )
        if not confirm:
            return

        tid = self.current_layout_key

        # Delete installed .prophettemplate file and preview cache
        delete_installed_template(tid, base_dir=self.base_dir)

        # Remove from global layouts
        if tid in self.global_layouts:
            del self.global_layouts[tid]
        if f"additional_{tid}" in self.global_layouts:
            del self.global_layouts[f"additional_{tid}"]

        # Remove from working data and project custom layouts
        if tid in self.layouts_data:
            del self.layouts_data[tid]
        if tid in self.project_custom_layouts:
            del self.project_custom_layouts[tid]
        if self.edition and tid in self.edition.custom_layouts:
            del self.edition.custom_layouts[tid]

        save_global_layout_definitions(self.global_layouts, defs_path=self.defs_path, base_dir=self.base_dir)

        # Delete wireframe mask file if exists
        mask_path = os.path.join(self.base_dir, "assets", "templates", "masks", f"{tid}_wireframe.png")
        if os.path.isfile(mask_path):
            try:
                os.remove(mask_path)
            except Exception:
                pass

        if callable(self.on_global_change):
            self.on_global_change()

        self._refresh_layout_dropdown()
        remaining = [k for k in self.layouts_data.keys() if not k.startswith("additional_")]
        next_key = remaining[0] if remaining else "layout_1"
        self._load_layout_into_editor(next_key)

        messagebox.showinfo("Deleted", f"Custom template '{tid}' removed.", parent=self)

    # ------------------ CANVAS DRAWING & HANDLES ------------------

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

        # Selection handles
        if self.selected_slot_index is not None and 0 <= self.selected_slot_index < len(slots):
            self._draw_selection_handles(slots[self.selected_slot_index])

    def _canvas_to_orig(self, cx, cy):
        ox = (cx - 20) / self.zoom_level
        oy = (cy - 20) / self.zoom_level
        return int(ox), int(oy)

    def _orig_to_canvas(self, ox, oy):
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

        # Label tag
        tag_text = f"[{stype.upper()}] {slabel}"
        self.canvas.create_rectangle(
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
            font=("Arial", max(8, int(9 * self.zoom_level)), "bold"),
            tags=("slot", f"slot_{idx}")
        )

    def _draw_selection_handles(self, slot):
        rx, ry, rw, rh = slot["rect"]
        x1, y1 = self._orig_to_canvas(rx, ry)
        x2, y2 = self._orig_to_canvas(rx + rw, ry + rh)
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2

        handles = {
            "nw": (x1, y1), "n": (xm, y1), "ne": (x2, y1),
            "w": (x1, ym),                 "e": (x2, ym),
            "sw": (x1, y2), "s": (xm, y2), "se": (x2, y2)
        }

        hs = 4
        for name, (hx, hy) in handles.items():
            self.canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill="#FFD700",
                outline="#000000",
                tags=("handle", f"handle_{name}")
            )

    # ------------------ MOUSE / CANVAS INTERACTION ------------------

    def _on_canvas_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._canvas_to_orig(cx, cy)

        self.drag_start_x = ox
        self.drag_start_y = oy

        # Draw Mode
        if self.drag_mode == 'drawing':
            self.drawing_rect = [ox, oy, 10, 10]
            return

        # Check Resize Handle
        handle = self._get_handle_under_pos(cx, cy)
        if handle and self.selected_slot_index is not None:
            self.drag_mode = 'resize'
            self.resize_handle = handle
            slots = self.layouts_data[self.current_layout_key]["slots"]
            self.orig_rect = list(slots[self.selected_slot_index]["rect"])
            return

        # Check Slot Box Hit
        hit_idx = self._get_slot_under_pos(ox, oy)
        if hit_idx is not None:
            self._select_slot_by_index(hit_idx)
            self.drag_mode = 'move'
            slots = self.layouts_data[self.current_layout_key]["slots"]
            self.orig_rect = list(slots[hit_idx]["rect"])
        else:
            self.selected_slot_index = None
            self._clear_inspector()
            self._refresh_canvas()
            self._highlight_active_slot_button(None)
            self.drag_mode = None

    def _on_canvas_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._canvas_to_orig(cx, cy)

        dx = ox - self.drag_start_x
        dy = oy - self.drag_start_y

        slots = self.layouts_data[self.current_layout_key]["slots"]

        if self.drag_mode == 'move' and self.selected_slot_index is not None and self.orig_rect:
            x, y, w, h = self.orig_rect
            nx = max(0, x + dx)
            ny = max(0, y + dy)
            slots[self.selected_slot_index]["rect"] = [nx, ny, w, h]
            self._update_coords_display([nx, ny, w, h])
            self._refresh_canvas()

        elif self.drag_mode == 'resize' and self.selected_slot_index is not None and self.orig_rect:
            x, y, w, h = self.orig_rect
            x2 = x + w
            y2 = y + h

            h_type = self.resize_handle
            if 'w' in h_type:
                nx = min(x + dx, x2 - 20)
                w = x2 - nx
                x = nx
            elif 'e' in h_type:
                w = max(20, w + dx)

            if 'n' in h_type:
                ny = min(y + dy, y2 - 20)
                h = y2 - ny
                y = ny
            elif 's' in h_type:
                h = max(20, h + dy)

            slots[self.selected_slot_index]["rect"] = [x, y, w, h]
            self._update_coords_display([x, y, w, h])
            self._refresh_canvas()

        elif self.drag_mode == 'drawing':
            rx = min(self.drag_start_x, ox)
            ry = min(self.drag_start_y, oy)
            rw = max(10, abs(ox - self.drag_start_x))
            rh = max(10, abs(oy - self.drag_start_y))
            self.drawing_rect = [rx, ry, rw, rh]

            self.canvas.delete("draw_preview")
            c_x1, c_y1 = self._orig_to_canvas(rx, ry)
            c_x2, c_y2 = self._orig_to_canvas(rx + rw, ry + rh)
            self.canvas.create_rectangle(
                c_x1, c_y1, c_x2, c_y2,
                outline="#4DFF88", width=2, dash=(4, 2),
                tags="draw_preview"
            )

    def _on_canvas_release(self, event):
        if self.drag_mode == 'drawing' and self.drawing_rect:
            rx, ry, rw, rh = self.drawing_rect
            self.canvas.delete("draw_preview")
            if rw >= 20 and rh >= 20:
                slots = self.layouts_data[self.current_layout_key]["slots"]
                new_idx = len(slots) + 1
                new_slot = {
                    'id': f'custom_slot_{new_idx}',
                    'type': 'column',
                    'rect': [rx, ry, rw, rh],
                    'label': f'Custom Slot {new_idx}'
                }
                slots.append(new_slot)
                self.selected_slot_index = len(slots) - 1
                self._refresh_slots_list()
                self._select_slot_by_index(self.selected_slot_index)
            self.drawing_rect = None
            self.drag_mode = None
            self._refresh_canvas()
        else:
            self.drag_mode = None
            self.resize_handle = None

    def _on_canvas_motion(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        handle = self._get_handle_under_pos(cx, cy)

        if handle:
            cursors = {
                'nw': 'size_nw_se', 'se': 'size_nw_se',
                'ne': 'size_ne_sw', 'sw': 'size_ne_sw',
                'n': 'size_ns',     's': 'size_ns',
                'w': 'size_we',     'e': 'size_we'
            }
            self.canvas.config(cursor=cursors.get(handle, "arrow"))
        elif self.drag_mode == 'drawing':
            self.canvas.config(cursor="crosshair")
        else:
            ox, oy = self._canvas_to_orig(cx, cy)
            if self._get_slot_under_pos(ox, oy) is not None:
                self.canvas.config(cursor="fleur")
            else:
                self.canvas.config(cursor="arrow")

    def _get_handle_under_pos(self, cx, cy):
        if self.selected_slot_index is None:
            return None
        slots = self.layouts_data[self.current_layout_key]["slots"]
        if self.selected_slot_index >= len(slots):
            return None
        rx, ry, rw, rh = slots[self.selected_slot_index]["rect"]
        x1, y1 = self._orig_to_canvas(rx, ry)
        x2, y2 = self._orig_to_canvas(rx + rw, ry + rh)
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2

        handles = {
            "nw": (x1, y1), "n": (xm, y1), "ne": (x2, y1),
            "w": (x1, ym),                 "e": (x2, ym),
            "sw": (x1, y2), "s": (xm, y2), "se": (x2, y2)
        }
        for name, (hx, hy) in handles.items():
            if abs(cx - hx) <= 8 and abs(cy - hy) <= 8:
                return name
        return None

    def _get_slot_under_pos(self, ox, oy):
        slots = self.layouts_data[self.current_layout_key]["slots"]
        for idx in reversed(range(len(slots))):
            rx, ry, rw, rh = slots[idx]["rect"]
            if rx <= ox <= rx + rw and ry <= oy <= ry + rh:
                return idx
        return None

    # ------------------ PAN & ZOOM CONTROLS ------------------

    def _start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_mousewheel(self, event):
        if event.state & 4:  # Ctrl held down -> zoom
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _zoom_in(self):
        self.zoom_level = min(2.5, self.zoom_level + 0.1)
        self._update_zoom_label()
        self._refresh_canvas()

    def _zoom_out(self):
        self.zoom_level = max(0.25, self.zoom_level - 0.1)
        self._update_zoom_label()
        self._refresh_canvas()

    def _zoom_reset(self):
        self.zoom_level = 1.0
        self._update_zoom_label()
        self._refresh_canvas()

    def _zoom_fit_width(self):
        if not self.raw_bg_image:
            return
        cw = self.canvas.winfo_width() - 50
        iw, _ = self.raw_bg_image.size
        if iw > 0 and cw > 100:
            self.zoom_level = round(cw / iw, 2)
            self._update_zoom_label()
            self._refresh_canvas()

    def _update_zoom_label(self):
        self.zoom_lbl.configure(text=f"{int(self.zoom_level * 100)}%")

    # ------------------ INSPECTOR & EDITING ------------------

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
        x, y, w, h = rect
        for entry, val in [(self.x_entry, x), (self.y_entry, y), (self.w_entry, w), (self.h_entry, h)]:
            entry.delete(0, "end")
            entry.insert(0, str(int(val)))

    def _clear_inspector(self):
        self.slot_id_entry.delete(0, "end")
        self.slot_label_entry.delete(0, "end")
        for entry in [self.x_entry, self.y_entry, self.w_entry, self.h_entry]:
            entry.delete(0, "end")

    def _on_slot_prop_changed(self, event=None):
        if self.selected_slot_index is None:
            return
        slots = self.layouts_data[self.current_layout_key]["slots"]
        slots[self.selected_slot_index]["id"] = self.slot_id_entry.get().strip()
        slots[self.selected_slot_index]["label"] = self.slot_label_entry.get().strip()
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
        self.drag_mode = 'drawing'
        self.selected_slot_index = None
        self._clear_inspector()
        self._refresh_canvas()
        messagebox.showinfo("Draw Slot", "Click and drag anywhere on the parchment canvas to draw a new content slot bounding box.", parent=self)

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


def open_layout_editor(initial_layout="layout_1", edition=None, on_project_save=None, on_global_change=None, base_dir="."):
    """Convenience launcher for the Layout Slot Editor window."""
    editor = LayoutEditorWindow(
        initial_layout=initial_layout,
        edition=edition,
        on_project_save=on_project_save,
        on_global_change=on_global_change,
        base_dir=base_dir
    )
    return editor
