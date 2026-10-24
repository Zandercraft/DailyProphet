"""Main application window for The Daily Prophet generator."""

from __future__ import annotations
import sys
import os
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from typing import Optional, Dict
from ..models import NewspaperEdition, Story, StoryPriority
from ..sample_data import get_original_hogwarts_edition
from ..pdf_exporter import PublicationExporter
from .layout_editor_window import LayoutEditorWindow
from .preview_canvas import BroadsheetPreviewCanvas, PreviewToplevelWindow
from .story_composer import StoryComposer
from .theme import Theme, IconManager
from .tooltip import add_tooltip
from ..native_renderer import map_slots_to_stories
from ..generate_masks import load_layout_definitions


class MainWindow(ctk.CTk):
    """Word-inspired, multi-pane publication workspace for The Daily Prophet."""

    def __init__(self):
        super().__init__()

        # Appearance configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("The Daily Prophet - Newspaper Generator")
        self.geometry("1280x820")
        self.minsize(960, 620)

        # Register Windows AppUserModelID for taskbar icon
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ca.zandercraft.dailyprophet.editor")
            except Exception:
                pass

        # Set Window and Taskbar Icon
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.icon_ico = os.path.join(project_root, "assets", "logo.ico")
        self.icon_png = os.path.join(project_root, "assets", "logo.png")
        if os.path.exists(self.icon_ico):
            try:
                self.iconbitmap(self.icon_ico)
            except Exception:
                pass
            if sys.platform == "win32":
                self.after(200, self._apply_win32_icon)

        # Active state
        self.base_dir = os.path.abspath(".")
        self.current_project_path = None
        self.edition = get_original_hogwarts_edition(".")
        self.current_page_idx = 0
        self.selected_story_id: Optional[str] = None
        self.story_item_frames: Dict[str, ctk.CTkFrame] = {}

        self.exporter = PublicationExporter(self.base_dir)
        self.floating_preview_win: Optional[PreviewToplevelWindow] = None

        self._setup_ui()
        self._load_edition_into_ui()

    def _setup_ui(self):
        self._setup_top_ribbon()

        # Main Tabview (Workspace vs Edition Settings)
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=8,
            fg_color=Theme.PANEL_BG,
            segmented_button_fg_color=Theme.HEADER_BG,
            segmented_button_selected_color=Theme.BTN_PRIMARY[0],
            segmented_button_selected_hover_color=Theme.BTN_PRIMARY[1],
            segmented_button_unselected_color=Theme.HEADER_BG,
            segmented_button_unselected_hover_color="#3a3027",
            text_color=Theme.TEXT_PARCHMENT,
        )
        self.tabview._segmented_button.configure(border_width=0)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(6, 4))

        self.tab_stories = self.tabview.add("Story Workspace")
        self.tab_settings = self.tabview.add("Header & Project Settings")

        self._setup_workspace_tab()
        self._setup_settings_tab()
        self._setup_bottom_bar()

    def _setup_top_ribbon(self):
        top_bar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, corner_radius=0, height=66)
        top_bar.pack(fill="x", padx=0, pady=0)

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=4)

        if os.path.exists(self.icon_png):
            try:
                logo_pil = Image.open(self.icon_png)
                self.brand_logo_img = ctk.CTkImage(light_image=logo_pil, dark_image=logo_pil, size=(58, 58))
                ctk.CTkLabel(title_box, image=self.brand_logo_img, text="").pack(side="left", padx=(0, 12))
            except Exception:
                pass

        titles_text_box = ctk.CTkFrame(title_box, fg_color="transparent")
        titles_text_box.pack(side="left")

        ctk.CTkLabel(
            titles_text_box,
            text="THE DAILY PROPHET",
            font=Theme.font_masthead(size=20, weight="bold"),
            text_color=Theme.TEXT_PARCHMENT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            titles_text_box,
            text="Wizarding Broadsheet Editor & Layout Publisher",
            font=Theme.font_masthead_subtitle(size=12, slant="italic"),
            text_color="#d6c9b6",
        ).pack(anchor="w", pady=(2, 0))

        # Responsive Icon-First Toolbar on Right
        top_btns = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_btns.pack(side="right", padx=14, pady=12)

        new_btn = ctk.CTkButton(
            top_btns,
            text="",
            image=IconManager.get_icon("plus", size=14),
            width=32,
            height=30,
            corner_radius=4,
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._new_project,
        )
        new_btn.pack(side="left", padx=2)
        add_tooltip(new_btn, "New Project")

        open_btn = ctk.CTkButton(
            top_btns,
            text="",
            image=IconManager.get_icon("folder-open", size=14),
            width=32,
            height=30,
            corner_radius=4,
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._open_project,
        )
        open_btn.pack(side="left", padx=2)
        add_tooltip(open_btn, "Open Project (.prophet)")

        save_btn = ctk.CTkButton(
            top_btns,
            text="",
            image=IconManager.get_icon("save", size=14),
            width=32,
            height=30,
            corner_radius=4,
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=self._save_project,
        )
        save_btn.pack(side="left", padx=2)
        add_tooltip(save_btn, "Save Project")

        # Subtle separator
        ctk.CTkFrame(top_btns, width=1, height=22, fg_color=Theme.BORDER_MEDIUM).pack(side="left", padx=6)

        sample_btn = ctk.CTkButton(
            top_btns,
            text="",
            image=IconManager.get_icon("scroll-unfurled", size=16, pack="rpg"),
            width=36,
            height=32,
            corner_radius=4,
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=self._load_hogwarts_original,
        )
        sample_btn.pack(side="left", padx=2)
        add_tooltip(sample_btn, "Load Hogwarts Community Issue Preset")

    def _setup_workspace_tab(self):
        parent = self.tab_stories

        # Page Ribbon Strip
        self.page_ribbon = ctk.CTkFrame(parent, fg_color=Theme.HEADER_BG, height=42, corner_radius=6)
        self.page_ribbon.pack(fill="x", padx=4, pady=(4, 6))

        # Integrated page tabs container (holds tabs and add/delete buttons)
        self.pages_tabs_frame = ctk.CTkFrame(self.page_ribbon, fg_color="transparent")
        self.pages_tabs_frame.pack(side="left", padx=6, pady=4)

        # Right side of ribbon: Layout template picker & editor
        layout_box = ctk.CTkFrame(self.page_ribbon, fg_color="transparent")
        layout_box.pack(side="right", padx=6, pady=4)

        ctk.CTkLabel(
            layout_box,
            text=" Layout:",
            image=IconManager.get_icon("layout-grid", size=15),
            compound="left",
            font=ctk.CTkFont(family="Georgia", size=12, weight="bold"),
            text_color=Theme.TEXT_PARCHMENT,
        ).pack(side="left", padx=(0, 4))

        self.layout_map: Dict[str, str] = {}
        self.layout_meta: Dict[str, Dict[str, object]] = {}
        self.template_selector = ctk.CTkOptionMenu(
            layout_box,
            values=["Layout 1: Broadsheet Lead & Gazette"],
            width=190,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BTN_SECONDARY[0],
            button_color=Theme.BTN_SECONDARY[1],
            command=self._on_layout_template_changed,
        )
        self.template_selector.pack(side="left", padx=2)
        add_tooltip(self.template_selector, "Select Page Template Layout")

        slots_btn = ctk.CTkButton(
            layout_box,
            text="",
            image=IconManager.get_icon("pencil", size=15),
            width=36,
            height=30,
            corner_radius=4,
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._open_layout_editor,
        )
        slots_btn.pack(side="left", padx=2)
        add_tooltip(slots_btn, "Open Slot & Layout Grid Editor")

        # Three-Pane Workspace
        self.workspace = ctk.CTkFrame(parent, fg_color="transparent")
        self.workspace.pack(fill="both", expand=True, padx=2, pady=2)

        self.workspace.columnconfigure(0, weight=0, minsize=275)
        self.workspace.columnconfigure(1, weight=5, minsize=370)
        self.workspace.columnconfigure(2, weight=4, minsize=380)
        self.workspace.rowconfigure(0, weight=1)

        # 1. LEFT PANE: Stories Navigator
        self.left_pane = ctk.CTkFrame(self.workspace, width=275, fg_color=Theme.PANEL_BG)
        self.left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.left_pane.pack_propagate(False)

        nav_header = ctk.CTkFrame(self.left_pane, fg_color="transparent")
        nav_header.pack(fill="x", padx=8, pady=(6, 4))

        self.page_stories_lbl = ctk.CTkLabel(
            nav_header, text="Stories", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_PARCHMENT
        )
        self.page_stories_lbl.pack(side="left")

        add_s_btn = ctk.CTkButton(
            nav_header,
            text="",
            image=IconManager.get_icon("plus", size=13),
            width=30,
            height=26,
            corner_radius=4,
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=self._add_story,
        )
        add_s_btn.pack(side="right")
        add_tooltip(add_s_btn, "Add New Story to Current Page")

        self.stories_scroll = ctk.CTkScrollableFrame(self.left_pane, fg_color="transparent")
        self.stories_scroll.pack(fill="both", expand=True, padx=4, pady=2)

        # Story Reorder / Move toolbar below list
        nav_tools = ctk.CTkFrame(self.left_pane, fg_color="transparent")
        nav_tools.pack(fill="x", padx=4, pady=(4, 6))

        up_btn = ctk.CTkButton(
            nav_tools,
            text="",
            image=IconManager.get_icon("arrow-up", size=13),
            width=32,
            height=26,
            corner_radius=4,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._move_story_up,
        )
        up_btn.pack(side="left", padx=1)
        add_tooltip(up_btn, "Move Story Up in Priority / Slot Order")

        down_btn = ctk.CTkButton(
            nav_tools,
            text="",
            image=IconManager.get_icon("arrow-down", size=13),
            width=32,
            height=26,
            corner_radius=4,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._move_story_down,
        )
        down_btn.pack(side="left", padx=1)
        add_tooltip(down_btn, "Move Story Down in Priority / Slot Order")

        move_btn = ctk.CTkButton(
            nav_tools,
            text="",
            image=IconManager.get_icon("arrow-right", size=14),
            width=32,
            height=26,
            corner_radius=4,
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=self._move_story_to_page_dialog,
        )
        move_btn.pack(side="left", padx=1)
        add_tooltip(move_btn, "Move Story to Another Page")

        del_s_btn = ctk.CTkButton(
            nav_tools,
            text="",
            image=IconManager.get_icon("trash-2", size=13),
            width=32,
            height=26,
            corner_radius=4,
            fg_color=Theme.BTN_DANGER[0],
            hover_color=Theme.BTN_DANGER[1],
            command=self._delete_selected_story,
        )
        del_s_btn.pack(side="right", padx=1)
        add_tooltip(del_s_btn, "Delete Selected Story")

        # 2. CENTER PANE: Article Composer
        self.center_composer = StoryComposer(
            self.workspace, on_story_updated=self._on_composer_story_updated, base_dir=self.base_dir
        )
        self.center_composer.grid(row=0, column=1, sticky="nsew", padx=4)

        # 3. RIGHT PANE: Live Broadsheet Preview Dock (Responsive scaling)
        self.right_dock = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.right_dock.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        self.preview_canvas = BroadsheetPreviewCanvas(
            self.right_dock,
            edition=self.edition,
            on_slot_clicked=self._on_slot_clicked_on_canvas,
            on_page_changed=self._on_preview_page_flipped,
            on_detach_requested=self._toggle_preview_detachment,
            is_detached=False,
        )
        self.preview_canvas.pack(fill="both", expand=True)

        self._refresh_layout_options()

    def _setup_bottom_bar(self):
        bottom_bar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, corner_radius=0, height=42)
        bottom_bar.pack(fill="x", side="bottom", padx=0, pady=0)

        self.status_lbl = ctk.CTkLabel(
            bottom_bar,
            text="The Daily Prophet ready.",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_MUTED,
        )
        self.status_lbl.pack(side="left", padx=14, pady=6)

        action_btns = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        action_btns.pack(side="right", padx=10, pady=4)

        pdf_btn = ctk.CTkButton(
            action_btns,
            text="",
            image=IconManager.get_icon("file-text", size=17),
            width=38,
            height=30,
            corner_radius=4,
            fg_color=Theme.BTN_SUCCESS[0],
            hover_color=Theme.BTN_SUCCESS[1],
            command=self._export_pdf,
        )
        pdf_btn.pack(side="left", padx=2)
        add_tooltip(pdf_btn, "Export Multi-Page Issue as High-Resolution PDF")

        img_btn = ctk.CTkButton(
            action_btns,
            text="",
            image=IconManager.get_icon("image", size=17),
            width=38,
            height=30,
            corner_radius=4,
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._export_images_dialog,
        )
        img_btn.pack(side="left", padx=2)
        add_tooltip(img_btn, "Export Pages as PNG Images or Animated GIF")

    def _setup_settings_tab(self):
        parent = self.tab_settings
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # MASTHEAD SECTION
        m_frame = ctk.CTkFrame(scroll)
        m_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(m_frame, text="Masthead & Header", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        ctk.CTkLabel(m_frame, text="Newspaper Title:").pack(anchor="w", padx=12, pady=(4, 2))
        self.title_entry = ctk.CTkEntry(m_frame)
        self.title_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(m_frame, text="Slogan / Tagline:").pack(anchor="w", padx=12, pady=(4, 2))
        self.tagline_entry = ctk.CTkEntry(m_frame)
        self.tagline_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(m_frame, text="Topic Navigation Bar:").pack(anchor="w", padx=12, pady=(4, 2))
        self.topic_bar_entry = ctk.CTkEntry(m_frame)
        self.topic_bar_entry.pack(fill="x", padx=12, pady=(0, 10))

        # DATE, ISSUE & EARS
        meta_row = ctk.CTkFrame(scroll)
        meta_row.pack(fill="x", pady=6)
        ctk.CTkLabel(meta_row, text="Ear Boxes & Issue Metadata", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        r1 = ctk.CTkFrame(meta_row, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(4, 6))

        c1 = ctk.CTkFrame(r1, fg_color="transparent")
        c1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(c1, text="Edition Date:").pack(anchor="w")
        self.date_entry = ctk.CTkEntry(c1)
        self.date_entry.pack(fill="x")

        c2 = ctk.CTkFrame(r1, fg_color="transparent")
        c2.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(c2, text="Day of Week:").pack(anchor="w")
        self.day_entry = ctk.CTkEntry(c2)
        self.day_entry.pack(fill="x")

        c3 = ctk.CTkFrame(r1, fg_color="transparent")
        c3.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(c3, text="Issue Number:").pack(anchor="w")
        self.issue_entry = ctk.CTkEntry(c3)
        self.issue_entry.pack(fill="x")

        r2 = ctk.CTkFrame(meta_row, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=(0, 10))

        c4 = ctk.CTkFrame(r2, fg_color="transparent")
        c4.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(c4, text="Edition Label (Upper Left):").pack(anchor="w")
        self.label_entry = ctk.CTkEntry(c4)
        self.label_entry.pack(fill="x")

        c5 = ctk.CTkFrame(r2, fg_color="transparent")
        c5.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(c5, text="Price:").pack(anchor="w")
        self.price_entry = ctk.CTkEntry(c5)
        self.price_entry.pack(fill="x")

        c6 = ctk.CTkFrame(r2, fg_color="transparent")
        c6.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(c6, text="Weather Condition:").pack(anchor="w")
        self.weather_entry = ctk.CTkEntry(c6)
        self.weather_entry.pack(fill="x")

        # QUOTES & BANNERS
        banner_frame = ctk.CTkFrame(scroll)
        banner_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(banner_frame, text="Quotes, Lore & Banners", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        q_row = ctk.CTkFrame(banner_frame, fg_color="transparent")
        q_row.pack(fill="x", padx=12, pady=(4, 6))

        qc1 = ctk.CTkFrame(q_row, fg_color="transparent")
        qc1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(qc1, text="Quotation Text:").pack(anchor="w")
        self.quote_text_entry = ctk.CTkEntry(qc1)
        self.quote_text_entry.pack(fill="x")

        qc2 = ctk.CTkFrame(q_row, width=220, fg_color="transparent")
        qc2.pack(side="right", padx=(6, 0))
        ctk.CTkLabel(qc2, text="Quote Author:").pack(anchor="w")
        self.quote_author_entry = ctk.CTkEntry(qc2)
        self.quote_author_entry.pack(fill="x")

        ctk.CTkLabel(banner_frame, text="Breaking Midday News Banner:").pack(anchor="w", padx=12, pady=(4, 2))
        self.breaking_entry = ctk.CTkEntry(banner_frame)
        self.breaking_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(banner_frame, text="Bottom Footer Slogan:").pack(anchor="w", padx=12, pady=(4, 2))
        self.footer_entry = ctk.CTkEntry(banner_frame)
        self.footer_entry.pack(fill="x", padx=12, pady=(0, 10))

        # Bind live preview updates on settings field changes
        for entry in [
            self.title_entry,
            self.tagline_entry,
            self.topic_bar_entry,
            self.date_entry,
            self.day_entry,
            self.issue_entry,
            self.label_entry,
            self.price_entry,
            self.weather_entry,
            self.quote_text_entry,
            self.quote_author_entry,
            self.breaking_entry,
            self.footer_entry,
        ]:
            entry.bind("<KeyRelease>", self._on_settings_field_changed)

    def _on_settings_field_changed(self, event=None):
        self._sync_settings_from_ui()
        self._update_preview()

    # -----------------------------------------------------------------------
    # Multi-Page Navigation and Ribbon Management
    # -----------------------------------------------------------------------
    def _refresh_page_tabs(self):
        for widget in self.pages_tabs_frame.winfo_children():
            widget.destroy()

        pages = self.edition.pages if hasattr(self.edition, "pages") and self.edition.pages else []
        if not pages:
            return

        for idx, page in enumerate(pages):
            is_active = idx == self.current_page_idx
            btn_fg = Theme.BTN_PRIMARY[0] if is_active else Theme.HEADER_BG
            btn_hover = Theme.BTN_PRIMARY[1] if is_active else "#3e3227"
            font_weight = "bold" if is_active else "normal"

            tab_btn = ctk.CTkButton(
                self.pages_tabs_frame,
                text=f"Page {page.page_number}",
                font=ctk.CTkFont(size=11, weight=font_weight),
                fg_color=btn_fg,
                hover_color=btn_hover,
                width=68,
                height=28,
                corner_radius=4,
                command=lambda p_idx=idx: self._on_page_tab_clicked(p_idx),
            )
            tab_btn.pack(side="left", padx=2)

        # Quick Add Page button
        add_p_btn = ctk.CTkButton(
            self.pages_tabs_frame,
            text="",
            image=IconManager.get_icon("plus", size=13),
            width=28,
            height=28,
            corner_radius=4,
            fg_color=Theme.BTN_SUCCESS[0],
            hover_color=Theme.BTN_SUCCESS[1],
            command=self._add_new_page,
        )
        add_p_btn.pack(side="left", padx=2)
        add_tooltip(add_p_btn, "Add New Blank Page to Issue")

        # Quick Delete Page button
        if len(pages) > 1:
            del_p_btn = ctk.CTkButton(
                self.pages_tabs_frame,
                text="",
                image=IconManager.get_icon("trash-2", size=13),
                width=28,
                height=28,
                corner_radius=4,
                fg_color=Theme.BTN_DANGER[0],
                hover_color=Theme.BTN_DANGER[1],
                command=self._delete_current_page,
            )
            del_p_btn.pack(side="left", padx=2)
            add_tooltip(del_p_btn, f"Delete Page {self.current_page_idx + 1}")

        active_page = self.edition.get_page(self.current_page_idx)
        if active_page:
            self.page_stories_lbl.configure(text=f"Stories (P{active_page.page_number})")
            if active_page.layout_id in self.layout_meta:
                label = [k for k, v in self.layout_map.items() if v == active_page.layout_id]
                if label:
                    self.template_selector.set(label[0])

    def _on_page_tab_clicked(self, page_idx: int):
        self.current_page_idx = page_idx
        self._refresh_page_tabs()
        self._refresh_stories_list()
        self.preview_canvas.set_current_page(page_idx)
        if self.floating_preview_win:
            self.floating_preview_win.preview_canvas.set_current_page(page_idx)

    def _add_new_page(self):
        new_page = self.edition.add_page()
        self.current_page_idx = len(self.edition.pages) - 1
        self._refresh_page_tabs()
        self._refresh_stories_list()
        self._update_preview()
        self.status_lbl.configure(text=f"Added new {new_page.title} to publication.")

    def _delete_current_page(self):
        if len(self.edition.pages) <= 1:
            return
        if messagebox.askyesno(
            "Delete Page", f"Delete Page {self.current_page_idx + 1} and its assigned stories?", parent=self
        ):
            self.edition.remove_page(self.current_page_idx)
            self.current_page_idx = max(0, self.current_page_idx - 1)
            self._refresh_page_tabs()
            self._refresh_stories_list()
            self._update_preview()
            self.status_lbl.configure(text="Page removed from publication.")

    def _move_story_to_page_dialog(self):
        if not self.selected_story_id or len(self.edition.pages) <= 1:
            messagebox.showinfo("Move Story", "Publication only has 1 page. Add a page first.", parent=self)
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Move Story to Page")
        dialog.geometry("340x220")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Select Target Page:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(16, 8))

        page_options = [
            f"Page {p.page_number}: {p.title}"
            for idx, p in enumerate(self.edition.pages)
            if idx != self.current_page_idx
        ]
        choice_var = ctk.StringVar(value=page_options[0] if page_options else "")
        ctk.CTkOptionMenu(dialog, variable=choice_var, values=page_options, width=240).pack(pady=8)

        def _confirm_move():
            chosen = choice_var.get()
            target_page_idx = 0
            for idx, p in enumerate(self.edition.pages):
                if f"Page {p.page_number}:" in chosen:
                    target_page_idx = idx
                    break
            self.edition.move_story(self.selected_story_id, self.current_page_idx, target_page_idx)
            dialog.destroy()
            self._refresh_stories_list()
            self._update_preview()
            self.status_lbl.configure(text=f"Moved story to Page {target_page_idx + 1}.")

        ctk.CTkButton(
            dialog,
            text="Move Story",
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=_confirm_move,
        ).pack(pady=12)

    # -----------------------------------------------------------------------
    # Story List & Composer Synchronization
    # -----------------------------------------------------------------------
    def _refresh_stories_list(self):
        for widget in self.stories_scroll.winfo_children():
            widget.destroy()
        self.story_item_frames.clear()

        active_page = self.edition.get_page(self.current_page_idx)
        stories = active_page.stories if active_page else []

        if not stories:
            ctk.CTkLabel(
                self.stories_scroll,
                text="No stories on this page.\nClick 'Add' above or insert lorem ipsum.",
                font=ctk.CTkFont(size=11),
                text_color="gray60",
                justify="center",
            ).pack(pady=30)
            self.center_composer.load_story(None)
            return

        for idx, story in enumerate(stories):
            card = self._create_story_card(story, idx)
            card.pack(fill="x", pady=3)
            self.story_item_frames[story.id] = card

        if self.selected_story_id and any(s.id == self.selected_story_id for s in stories):
            self._select_story(self.selected_story_id)
        elif stories:
            self._select_story(stories[0].id)

    def _create_story_card(self, story: Story, index: int) -> ctk.CTkFrame:
        prio = story.priority.value if isinstance(story.priority, StoryPriority) else str(story.priority)
        if prio == StoryPriority.COVER.value:
            badge_text = "COVER HERO"
            badge_color = "#992b2b"
        elif prio == StoryPriority.MAJOR.value:
            badge_text = "MAJOR FEATURE"
            badge_color = "#355b82"
        elif prio == StoryPriority.COLUMN.value:
            badge_text = "SIDE COLUMN"
            badge_color = "#4c6643"
        else:
            badge_text = "NOTICE / LORE"
            badge_color = "#7a6229"

        card = ctk.CTkFrame(self.stories_scroll, fg_color=Theme.CARD_BG, corner_radius=5)
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=8, pady=6)

        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row,
            text=f" {badge_text} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=badge_color,
            corner_radius=3,
            text_color="#ffffff",
        ).pack(side="left")

        if story.image_path and os.path.isfile(story.image_path):
            ctk.CTkLabel(
                top_row,
                text=" Image",
                image=IconManager.get_icon("image", size=12),
                compound="left",
                font=ctk.CTkFont(size=10),
                text_color=Theme.TEXT_MUTED,
            ).pack(side="left", padx=6)

        raw_headline = story.headline.strip() if (story.headline and story.headline.strip()) else "[Untitled Headline]"
        # Display heading wrapping up to 3 lines (truncating cleanly beyond ~3 lines)
        cleaned_text = " ".join(raw_headline.split())
        if len(cleaned_text) > 115:
            display_headline = cleaned_text[:112].rsplit(" ", 1)[0] + "..."
        else:
            display_headline = cleaned_text

        headline_lbl = ctk.CTkLabel(
            content,
            text=display_headline,
            font=ctk.CTkFont(family="Georgia", size=12, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=235,
        )
        headline_lbl.pack(fill="x", pady=(3, 1))

        # Dynamically adjust wraplength if story card expands or shrinks
        def _adjust_wrap(e, lbl=headline_lbl):
            if e.width > 60:
                lbl.configure(wraplength=max(160, e.width - 12))

        content.bind("<Configure>", _adjust_wrap)

        # Click handler
        def _on_click(e=None, sid=story.id):
            self._select_story(sid)

        card.bind("<Button-1>", _on_click)
        content.bind("<Button-1>", _on_click)
        top_row.bind("<Button-1>", _on_click)
        headline_lbl.bind("<Button-1>", _on_click)
        for child in top_row.winfo_children():
            child.bind("<Button-1>", _on_click)
        return card

    def _select_story(self, story_id: Optional[str] = None):
        self.selected_story_id = story_id
        active_page = self.edition.get_page(self.current_page_idx)
        stories = active_page.stories if active_page else []

        for sid, frame in self.story_item_frames.items():
            if sid == story_id:
                frame.configure(border_width=2, border_color="#e5c158")
            else:
                frame.configure(border_width=0)

        found = next((s for s in stories if s.id == story_id), None)
        if found:
            self.center_composer.load_story(found)
            # Find slot id on current layout
            self._highlight_story_on_preview(found)

    def _highlight_story_on_preview(self, story: Story):
        active_page = self.edition.get_page(self.current_page_idx)
        layout_id = active_page.layout_id
        defs = getattr(self, "raw_layout_defs", {})
        slots = defs.get(layout_id, {}).get("slots", [])
        _, story_to_slots = map_slots_to_stories(active_page.stories, slots)

        slots_for_story = story_to_slots.get(story.id, [])
        primary_slot = slots_for_story[0] if slots_for_story else None

        self.preview_canvas.set_highlight(story_id=story.id, slot_id=primary_slot, slot_ids=slots_for_story)
        if self.floating_preview_win:
            self.floating_preview_win.preview_canvas.set_highlight(
                story_id=story.id, slot_id=primary_slot, slot_ids=slots_for_story
            )

    def _on_composer_story_updated(self, story: Story):
        self._refresh_story_card_text(story)
        self._update_preview()

    def _refresh_story_card_text(self, story: Story):
        card = self.story_item_frames.get(story.id)
        if card:
            for child in card.winfo_children():
                for sub in child.winfo_children():
                    if isinstance(sub, ctk.CTkLabel) and getattr(sub, "_text", "") not in (
                        "COVER HERO",
                        "MAJOR FEATURE",
                        "SIDE COLUMN",
                        "NOTICE / LORE",
                        " Image",
                    ):
                        sub.configure(text=story.headline or "[Untitled Headline]")

    def _on_slot_clicked_on_canvas(self, slot_id: str, story_id: Optional[str]):
        if story_id:
            self._select_story(story_id)
        else:
            self.status_lbl.configure(text=f"Selected layout slot: {slot_id}")

    def _on_preview_page_flipped(self, page_idx: int):
        self._on_page_tab_clicked(page_idx)

    # -----------------------------------------------------------------------
    # Dual-Monitor Floating Preview Detach & Dock
    # -----------------------------------------------------------------------
    def _toggle_preview_detachment(self):
        if self.floating_preview_win:
            self.floating_preview_win.destroy()
            self.floating_preview_win = None
            self.workspace.columnconfigure(2, weight=4, minsize=380)
            self.right_dock.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
            self.preview_canvas.refresh_preview()
            self.status_lbl.configure(text="Preview docked to main workspace.")
        else:
            self.right_dock.grid_remove()
            self.workspace.columnconfigure(2, weight=0, minsize=0)
            self.floating_preview_win = PreviewToplevelWindow(
                self,
                edition=self.edition,
                on_slot_clicked=self._on_slot_clicked_on_canvas,
                on_page_changed=self._on_preview_page_flipped,
                on_dock=self._toggle_preview_detachment,
            )
            self.floating_preview_win.preview_canvas.set_current_page(self.current_page_idx)
            self.status_lbl.configure(text="Preview detached to secondary monitor. Main window expanded.")

    def _update_preview(self):
        if getattr(self, "_preview_timer", None):
            self.after_cancel(self._preview_timer)
        self._preview_timer = self.after(50, self._do_refresh_preview)

    def _do_refresh_preview(self):
        self._preview_timer = None
        self.preview_canvas.refresh_preview()
        if self.floating_preview_win:
            self.floating_preview_win.preview_canvas.refresh_preview()

    # -----------------------------------------------------------------------
    # Story Actions (Add, Delete, Reorder)
    # -----------------------------------------------------------------------
    def _add_story(self):
        active_page = self.edition.get_page(self.current_page_idx)
        new_story = Story(headline="NEW STORY ARTICLE", priority=StoryPriority.COLUMN)
        active_page.stories.append(new_story)
        self.edition.stories = self.edition.all_stories()
        self._refresh_stories_list()
        self._select_story(new_story.id)
        self._update_preview()
        self.status_lbl.configure(text="Added new story draft.")

    def _delete_selected_story(self):
        if not self.selected_story_id:
            return
        active_page = self.edition.get_page(self.current_page_idx)
        story = next((s for s in active_page.stories if s.id == self.selected_story_id), None)
        if story and messagebox.askyesno("Delete Story", f"Delete article '{story.headline}'?", parent=self):
            active_page.stories.remove(story)
            self.edition.stories = self.edition.all_stories()
            self.selected_story_id = None
            self._refresh_stories_list()
            self._update_preview()
            self.status_lbl.configure(text="Story deleted.")

    def _move_story_up(self):
        self._reorder_story(-1)

    def _move_story_down(self):
        self._reorder_story(1)

    def _reorder_story(self, offset: int):
        if not self.selected_story_id:
            return
        active_page = self.edition.get_page(self.current_page_idx)
        idx = next((i for i, s in enumerate(active_page.stories) if s.id == self.selected_story_id), -1)
        if idx == -1:
            return
        new_idx = idx + offset
        if 0 <= new_idx < len(active_page.stories):
            active_page.stories[idx], active_page.stories[new_idx] = (
                active_page.stories[new_idx],
                active_page.stories[idx],
            )
            self.edition.stories = self.edition.all_stories()
            self._refresh_stories_list()
            self._update_preview()

    # -----------------------------------------------------------------------
    # Layout and Project Management
    # -----------------------------------------------------------------------
    def _on_layout_template_changed(self, choice: str):
        active_page = self.edition.get_page(self.current_page_idx)
        if choice in self.layout_map:
            active_page.layout_id = self.layout_map[choice]
            self.edition.selected_layout = active_page.layout_id
            self._update_preview()
            self.status_lbl.configure(text=f"Page {self.current_page_idx + 1} layout set to: {choice}")

    def _refresh_layout_options(self, preferred_selection=None):
        data = load_layout_definitions(base_dir=self.base_dir)
        self.raw_layout_defs = data
        self.layout_map.clear()
        self.layout_meta.clear()

        single_keys = [k for k in data.keys() if not k.startswith("additional_")]
        for k in single_keys:
            info = data[k]
            label = info.get("label", k.replace("_", " ").title())
            self.layout_map[label] = k
            self.layout_meta[k] = info

        labels = list(self.layout_map.keys())
        self.template_selector.configure(values=labels)

        active_page = self.edition.get_page(self.current_page_idx)
        target_tid = active_page.layout_id if active_page else "layout_1"
        for lbl, tid in self.layout_map.items():
            if tid == target_tid:
                self.template_selector.set(lbl)
                break

    def _open_layout_editor(self):
        active_page = self.edition.get_page(self.current_page_idx)
        win = LayoutEditorWindow(
            self,
            initial_layout=active_page.layout_id,
            edition=self.edition,
            on_project_save=self._on_layout_saved_to_project,
            on_global_change=self._refresh_layout_options,
            base_dir=self.base_dir,
        )
        win.lift(self)
        win.focus_force()

    def _on_layout_saved_to_project(self):
        self._update_preview()
        self.status_lbl.configure(text="Custom layout slots saved to this issue.")

    def _load_edition_into_ui(self):
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, self.edition.paper_title)

        self.tagline_entry.delete(0, "end")
        self.tagline_entry.insert(0, self.edition.tagline)

        self.topic_bar_entry.delete(0, "end")
        self.topic_bar_entry.insert(
            0, getattr(self.edition, "topic_bar", "HOGWARTS ★ HOGSMEADE ★ MINISTRY ★ COMMUNITY")
        )

        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, self.edition.edition_date)

        self.day_entry.delete(0, "end")
        self.day_entry.insert(0, getattr(self.edition, "edition_day", "MONDAY"))

        self.issue_entry.delete(0, "end")
        self.issue_entry.insert(0, self.edition.issue_number)

        self.label_entry.delete(0, "end")
        self.label_entry.insert(0, getattr(self.edition, "edition_label", "HOGWARTS EDITION"))

        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, self.edition.price)

        self.weather_entry.delete(0, "end")
        self.weather_entry.insert(0, getattr(self.edition, "weather", "Mild and Misty with Chance of Spells"))

        self.quote_text_entry.delete(0, "end")
        self.quote_text_entry.insert(0, getattr(self.edition, "quote_text", ""))

        self.quote_author_entry.delete(0, "end")
        self.quote_author_entry.insert(0, getattr(self.edition, "quote_author", "PROFESSOR FIG"))

        self.breaking_entry.delete(0, "end")
        self.breaking_entry.insert(0, self.edition.breaking_banner)

        self.footer_entry.delete(0, "end")
        self.footer_entry.insert(0, getattr(self.edition, "footer_slogan", ""))

        self._refresh_page_tabs()
        self._refresh_stories_list()
        self.preview_canvas.set_edition(self.edition)
        if self.floating_preview_win:
            self.floating_preview_win.preview_canvas.set_edition(self.edition)

    def _sync_settings_from_ui(self):
        self.edition.paper_title = self.title_entry.get().strip() or "The Daily Prophet"
        self.edition.tagline = self.tagline_entry.get().strip()
        self.edition.topic_bar = self.topic_bar_entry.get().strip()
        self.edition.edition_date = self.date_entry.get().strip()
        self.edition.edition_day = self.day_entry.get().strip()
        self.edition.issue_number = self.issue_entry.get().strip()
        self.edition.edition_label = self.label_entry.get().strip()
        self.edition.price = self.price_entry.get().strip()
        self.edition.weather = self.weather_entry.get().strip()
        self.edition.quote_text = self.quote_text_entry.get().strip()
        self.edition.quote_author = self.quote_author_entry.get().strip()
        self.edition.breaking_banner = self.breaking_entry.get().strip()
        self.edition.footer_slogan = self.footer_entry.get().strip()

    def _load_hogwarts_original(self):
        self.edition = get_original_hogwarts_edition(self.base_dir)
        self.current_page_idx = 0
        self._load_edition_into_ui()
        self.status_lbl.configure(text="Loaded Hogwarts Community Edition preset.")

    def _new_project(self):
        if messagebox.askyesno("New Project", "Start a blank new newspaper project?", parent=self):
            self.edition = NewspaperEdition()
            self.current_page_idx = 0
            self.current_project_path = None
            self._load_edition_into_ui()
            self.status_lbl.configure(text="Created new blank edition.")

    def _open_project(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Open Newspaper Issue",
            filetypes=[("Prophet Issue Package", "*.prophet"), ("Legacy JSON Project", "*.json"), ("All Files", "*.*")],
        )
        if path:
            try:
                self.edition = NewspaperEdition.load_project_package(path)
                self.current_project_path = path
                self.current_page_idx = 0
                self._load_edition_into_ui()
                self.status_lbl.configure(text=f"Loaded project: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error Opening Project", str(e), parent=self)

    def _save_project(self):
        if self.current_project_path:
            self._sync_settings_from_ui()
            try:
                self.edition.save_project_package(self.current_project_path)
                self.status_lbl.configure(text=f"Saved project: {os.path.basename(self.current_project_path)}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e), parent=self)
        else:
            self._save_as_project()

    def _save_as_project(self):
        self._sync_settings_from_ui()
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Daily Prophet Issue",
            defaultextension=".prophet",
            filetypes=[("Prophet Issue Package", "*.prophet"), ("All Files", "*.*")],
        )
        if path:
            try:
                self.edition.save_project_package(path)
                self.current_project_path = path
                self.status_lbl.configure(text=f"Saved project: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e), parent=self)

    # -----------------------------------------------------------------------
    # Exporters (Multi-Page PDF, Image, Animated GIF)
    # -----------------------------------------------------------------------
    def _export_pdf(self):
        self._sync_settings_from_ui()
        num_pages = len(self.edition.pages) if hasattr(self.edition, "pages") and self.edition.pages else 1

        path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Export Multi-Page PDF ({num_pages} Pages)",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf"), ("All Files", "*.*")],
        )
        if not path:
            return

        self.status_lbl.configure(text="Compiling multi-page broadsheet PDF...")
        success, msg = self.exporter.export_pdf(self.edition, path, scale=2.0)
        if success:
            self.status_lbl.configure(text=f"Exported PDF to: {os.path.basename(path)}")
            messagebox.showinfo(
                "PDF Export Complete", f"Created {num_pages}-page print-ready PDF:\n{path}", parent=self
            )
        else:
            messagebox.showerror("Export Failed", msg, parent=self)

    def _export_images_dialog(self):
        self._sync_settings_from_ui()
        num_pages = len(self.edition.pages) if hasattr(self.edition, "pages") and self.edition.pages else 1

        dialog = ctk.CTkToplevel(self)
        dialog.title("Export Broadsheet Images")
        dialog.geometry("400x320")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Export Broadsheet Images / GIF", font=ctk.CTkFont(size=14, weight="bold")).pack(
            pady=(16, 8)
        )

        scope_var = ctk.StringVar(value="current")
        ctk.CTkRadioButton(
            dialog,
            text=f"Export Active Page ({self.current_page_idx + 1} of {num_pages})",
            variable=scope_var,
            value="current",
        ).pack(anchor="w", padx=30, pady=4)
        ctk.CTkRadioButton(dialog, text=f"Export All Pages ({num_pages} Pages)", variable=scope_var, value="all").pack(
            anchor="w", padx=30, pady=4
        )

        anim_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(dialog, text="Export as Animated Broadsheet GIF (moving pictures)", variable=anim_var).pack(
            anchor="w", padx=30, pady=(12, 16)
        )

        def _do_export():
            is_anim = anim_var.get()
            scope = scope_var.get()
            dialog.destroy()

            if scope == "current":
                ext = ".gif" if is_anim else ".png"
                filetypes = [("GIF Animation", "*.gif")] if is_anim else [("PNG Image", "*.png"), ("JPEG", "*.jpg")]
                out_path = filedialog.asksaveasfilename(
                    parent=self, title="Export Page Image", defaultextension=ext, filetypes=filetypes
                )
                if out_path:
                    if is_anim:
                        success, msg = self.exporter.export_animated_gif(
                            self.edition, out_path, page_idx=self.current_page_idx
                        )
                    else:
                        success, msg = self.exporter.export_page_image(
                            self.edition, out_path, page_idx=self.current_page_idx, scale=2.0
                        )
                    if success:
                        messagebox.showinfo("Export Complete", msg, parent=self)
                    else:
                        messagebox.showerror("Export Failed", msg, parent=self)
            else:
                out_dir = filedialog.askdirectory(parent=self, title="Select Directory for Exported Pages")
                if out_dir:
                    fmt = "gif" if is_anim else "png"
                    success, msg, paths = self.exporter.export_all_page_images(
                        self.edition, out_dir, format_ext=fmt, scale=2.0
                    )
                    if success:
                        messagebox.showinfo(
                            "Batch Export Complete", f"Exported {len(paths)} pages into:\n{out_dir}", parent=self
                        )
                    else:
                        messagebox.showerror("Export Failed", msg, parent=self)

        ctk.CTkButton(
            dialog,
            text="Export Publication",
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=_do_export,
        ).pack(pady=10)

    def _apply_win32_icon(self):
        if sys.platform != "win32" or not hasattr(self, "icon_ico") or not os.path.exists(self.icon_ico):
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32
            hwnd = self.winfo_id()
            root_hwnd = user32.GetAncestor(hwnd, 2)
            target_hwnd = root_hwnd if root_hwnd else hwnd

            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010
            WM_SETICON = 0x0080
            ICON_BIG = 1

            cx_big = user32.GetSystemMetrics(11)
            cy_big = user32.GetSystemMetrics(12)
            hicon_big = user32.LoadImageW(None, self.icon_ico, IMAGE_ICON, cx_big, cy_big, LR_LOADFROMFILE)
            if hicon_big:
                user32.SendMessageW(target_hwnd, WM_SETICON, ICON_BIG, hicon_big)
        except Exception:
            pass


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
