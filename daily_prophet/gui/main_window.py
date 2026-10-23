"""Main application window for The Daily Prophet generator."""
from __future__ import annotations
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from typing import List, Optional
from ..models import NewspaperEdition, Story, StoryPriority, PaperTheme, BorderStyle, ExportFormat, LayoutStatus
from ..sample_data import get_original_hogwarts_edition, get_azkaban_edition, get_sample_edition
from ..template_engine import generate_newspaper_html
from ..pdf_exporter import export_html_to_pdf, export_html_to_image
from ..native_renderer import export_native_image, export_native_pdf, NativeBroadsheetRenderer
from .story_dialog import StoryDialog
from .preview_window import open_webview_window, open_in_browser, save_temp_preview, open_image_preview
from .layout_editor_window import LayoutEditorWindow
from .theme import Theme, IconManager
from ..generate_masks import load_layout_definitions
from ..versioning import ProjectMigrator, CURRENT_PROJECT_VERSION


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Appearance configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("The Daily Prophet - Newspaper Generator")
        self.geometry("1180x820")
        self.minsize(1020, 720)

        # Ensure Windows AppUserModelID is registered for taskbar icon
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

        # Active edition state
        self.base_dir = os.path.abspath(".")
        self.current_project_path = None
        self.edition = get_original_hogwarts_edition(".")

        self._setup_ui()
        self._load_edition_into_ui()

    def _setup_ui(self):
        # 1. TOP MASTHEAD TOOLBAR
        top_bar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, corner_radius=0, height=65)
        top_bar.pack(fill="x", padx=0, pady=0)

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        # Brand Logo in top bar
        if os.path.exists(self.icon_png):
            try:
                logo_pil = Image.open(self.icon_png)
                self.brand_logo_img = ctk.CTkImage(light_image=logo_pil, dark_image=logo_pil, size=(46, 46))
                logo_lbl = ctk.CTkLabel(title_box, image=self.brand_logo_img, text="")
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        titles_text_box = ctk.CTkFrame(title_box, fg_color="transparent")
        titles_text_box.pack(side="left", fill="y")

        app_title = ctk.CTkLabel(
            titles_text_box,
            text="THE DAILY PROPHET",
            font=ctk.CTkFont(family="Georgia", size=20, weight="bold"),
            text_color=Theme.TEXT_PARCHMENT,
        )
        app_title.pack(anchor="w")

        app_sub = ctk.CTkLabel(
            titles_text_box,
            text="Wizarding Broadsheet Generator & Layout Publisher",
            font=ctk.CTkFont(family="Georgia", size=11, slant="italic"),
            text_color=Theme.TEXT_MUTED,
        )
        app_sub.pack(anchor="w")

        # Top Project Buttons
        top_btns = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_btns.pack(side="right", padx=20, pady=12)

        ctk.CTkButton(
            top_btns,
            text="Hogwarts Issue",
            width=130,
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=self._load_hogwarts_original,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            top_btns,
            text="Azkaban Edition",
            width=130,
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=self._load_azkaban_sample,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            top_btns,
            text="Open...",
            width=75,
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._open_project,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            top_btns,
            text="Save",
            width=65,
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=self._save_project,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            top_btns,
            text="Save As...",
            width=85,
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=self._save_as_project,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            top_btns,
            text="New",
            width=60,
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._new_project,
        ).pack(side="left", padx=3)

        # 2. MAIN TABVIEW (STORIES vs EDITION SETTINGS)
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(10, 6))

        self.tab_stories = self.tabview.add("📰 Stories & Layout")
        self.tab_settings = self.tabview.add("⚙️ Newspaper Header & Settings")

        self._setup_stories_tab()
        self._setup_settings_tab()

        # 2.5 LAYOUT TEMPLATE SELECTOR & WIREFRAME BAR
        layout_bar = ctk.CTkFrame(self, fg_color=("#26201a", "#16120e"), corner_radius=0, height=44)
        layout_bar.pack(fill="x", padx=0, pady=(0, 2))

        ctk.CTkLabel(
            layout_bar,
            text="📐 Layout Template:",
            font=ctk.CTkFont(family="Georgia", size=12, weight="bold"),
            text_color="#f5ede0",
        ).pack(side="left", padx=(20, 8), pady=8)

        self.layout_map = {}
        self.layout_meta = {}

        self.template_selector = ctk.CTkOptionMenu(
            layout_bar,
            values=["Layout 1: Broadsheet Lead & Gazette"],
            width=330,
            fg_color="#3d342a",
            button_color="#54483a",
            button_hover_color="#6e5e4c",
            dropdown_fg_color="#2b231c",
            command=self._on_layout_changed
        )
        self.template_selector.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            layout_bar,
            text="👁️ View Wireframe Mask",
            width=165,
            fg_color="#54483a",
            hover_color="#6e5e4c",
            command=self._view_wireframe_mask
        ).pack(side="left", padx=6, pady=8)

        ctk.CTkButton(
            layout_bar,
            text="✏️ Edit Layout Slots",
            width=155,
            fg_color="#3d5a45",
            hover_color="#2b4736",
            command=self._open_layout_editor
        ).pack(side="left", padx=4, pady=8)

        self.layout_info_lbl = ctk.CTkLabel(
            layout_bar,
            text="1122x1402 Broadsheet • 18 Content Slots",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#c2b6a4"
        )
        self.layout_info_lbl.pack(side="right", padx=20, pady=8)

        # Initialize layout options dynamically from layout definitions
        self._refresh_layout_options()

        # 3. BOTTOM ACTION BAR (PREVIEW, PDF & IMAGE EXPORT)
        bottom_bar = ctk.CTkFrame(self, fg_color=("#2e261f", "#1c1713"), corner_radius=0, height=62)
        bottom_bar.pack(fill="x", padx=0, pady=0)

        # Status text on the left
        self.status_lbl = ctk.CTkLabel(
            bottom_bar,
            text="Ready. Layout 1 loaded.",
            font=ctk.CTkFont(size=12),
            text_color="#c2b6a4",
        )
        self.status_lbl.pack(side="left", padx=20, pady=12)

        # Action buttons on the right: PDF and IMAGE are prioritized
        action_btns = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        action_btns.pack(side="right", padx=20, pady=10)

        ctk.CTkButton(
            action_btns,
            text="Preview Publication",
            width=165,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=self._preview_newspaper,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            action_btns,
            text="Export PDF",
            width=135,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Theme.BTN_SUCCESS[0],
            hover_color=Theme.BTN_SUCCESS[1],
            command=self._export_pdf,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            action_btns,
            text="Export Image",
            width=135,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Theme.BTN_NEUTRAL[0],
            hover_color=Theme.BTN_NEUTRAL[1],
            command=self._export_image,
        ).pack(side="left", padx=6)

    def _setup_stories_tab(self):
        parent = self.tab_stories

        split_frame = ctk.CTkFrame(parent, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # LEFT PANE: Stories management
        left_pane = ctk.CTkFrame(split_frame)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=0)

        stories_bar = ctk.CTkFrame(left_pane, fg_color="transparent")
        stories_bar.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            stories_bar,
            text="Stories in this Edition:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            stories_bar,
            text="Add Story",
            width=100,
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=self._add_story,
        ).pack(side="right", padx=(6, 0))

        # Stories scrollable list
        self.stories_scroll = ctk.CTkScrollableFrame(left_pane)
        self.stories_scroll.pack(fill="both", expand=True, padx=12, pady=6)

        # Ordering / deleting buttons below list
        list_ctrls = ctk.CTkFrame(left_pane, fg_color="transparent")
        list_ctrls.pack(fill="x", padx=12, pady=(6, 10))

        ctk.CTkButton(list_ctrls, text="Move Up", width=85, fg_color=Theme.BTN_CONTROL[0], hover_color=Theme.BTN_CONTROL[1], command=self._move_story_up).pack(side="left", padx=(0, 4))
        ctk.CTkButton(list_ctrls, text="Move Down", width=85, fg_color=Theme.BTN_CONTROL[0], hover_color=Theme.BTN_CONTROL[1], command=self._move_story_down).pack(side="left", padx=4)
        ctk.CTkButton(list_ctrls, text="Edit Story", width=95, fg_color=Theme.BTN_SECONDARY[0], hover_color=Theme.BTN_SECONDARY[1], command=self._edit_selected_story).pack(side="left", padx=4)
        ctk.CTkButton(list_ctrls, text="Delete", width=75, fg_color=Theme.BTN_DANGER[0], hover_color=Theme.BTN_DANGER[1], command=self._delete_selected_story).pack(side="right")

        # RIGHT PANE: Story Inspector
        self.right_pane = ctk.CTkFrame(split_frame, width=380)
        self.right_pane.pack(side="right", fill="both", expand=False, padx=(8, 0), pady=0)
        self.right_pane.pack_propagate(False)

        ctk.CTkLabel(
            self.right_pane,
            text="Story Inspector",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.inspector_scroll = ctk.CTkScrollableFrame(self.right_pane)
        self.inspector_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.inspect_prio_lbl = ctk.CTkLabel(self.inspector_scroll, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.inspect_prio_lbl.pack(anchor="w", padx=6, pady=2)

        self.inspect_title_lbl = ctk.CTkLabel(
            self.inspector_scroll,
            text="Select a story on the left to inspect.",
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
            wraplength=340,
            justify="left",
        )
        self.inspect_title_lbl.pack(anchor="w", padx=6, pady=(4, 6))

        self.inspect_author_lbl = ctk.CTkLabel(self.inspector_scroll, text="", font=ctk.CTkFont(size=11), text_color="gray70")
        self.inspect_author_lbl.pack(anchor="w", padx=6, pady=(0, 8))

        self.inspect_photo_preview = ctk.CTkLabel(self.inspector_scroll, text="", height=140)
        self.inspect_photo_preview.pack(fill="x", padx=6, pady=4)

        self.inspect_caption_lbl = ctk.CTkLabel(self.inspector_scroll, text="", font=ctk.CTkFont(size=11, slant="italic"), wraplength=340, justify="left")
        self.inspect_caption_lbl.pack(anchor="w", padx=6, pady=2)

        self.inspect_body_lbl = ctk.CTkLabel(self.inspector_scroll, text="", font=ctk.CTkFont(size=12), wraplength=340, justify="left")
        self.inspect_body_lbl.pack(anchor="w", padx=6, pady=(8, 4))

        self.selected_story_id = None
        self.story_item_frames = {}

    def _setup_settings_tab(self):
        parent = self.tab_settings

        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # MASTHEAD SECTION
        m_frame = ctk.CTkFrame(scroll)
        m_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(m_frame, text="Masthead & Header", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

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

        ctk.CTkLabel(meta_row, text="Ear Boxes & Issue Metadata", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        r1 = ctk.CTkFrame(meta_row, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(0, 6))

        c1 = ctk.CTkFrame(r1, fg_color="transparent")
        c1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(c1, text="Issue Number (Left Ear Top):").pack(anchor="w")
        self.issue_entry = ctk.CTkEntry(c1)
        self.issue_entry.pack(fill="x")

        c2 = ctk.CTkFrame(r1, fg_color="transparent")
        c2.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(c2, text="Day of Week:").pack(anchor="w")
        self.day_entry = ctk.CTkEntry(c2)
        self.day_entry.pack(fill="x")

        c3 = ctk.CTkFrame(r1, fg_color="transparent")
        c3.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(c3, text="Edition Date:").pack(anchor="w")
        self.date_entry = ctk.CTkEntry(c3)
        self.date_entry.pack(fill="x")

        r2 = ctk.CTkFrame(meta_row, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=(6, 6))

        c4 = ctk.CTkFrame(r2, fg_color="transparent")
        c4.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(c4, text="Edition Label (Ear Subhead):").pack(anchor="w")
        self.label_entry = ctk.CTkEntry(c4)
        self.label_entry.pack(fill="x")

        c5 = ctk.CTkFrame(r2, fg_color="transparent")
        c5.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(c5, text="Price (e.g. 1 KNUT):").pack(anchor="w")
        self.price_entry = ctk.CTkEntry(c5)
        self.price_entry.pack(fill="x")

        c6 = ctk.CTkFrame(r2, fg_color="transparent")
        c6.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(c6, text="Castle Weather (Right Ear):").pack(anchor="w")
        self.weather_entry = ctk.CTkEntry(c6)
        self.weather_entry.pack(fill="x")

        # EDITORIAL QUOTE & WORDS OF WISDOM
        quote_frame = ctk.CTkFrame(scroll)
        quote_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(quote_frame, text="Words of Wisdom / Editorial Quote", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        q_r = ctk.CTkFrame(quote_frame, fg_color="transparent")
        q_r.pack(fill="x", padx=12, pady=(4, 10))

        q_c1 = ctk.CTkFrame(q_r, fg_color="transparent")
        q_c1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(q_c1, text="Quote Text:").pack(anchor="w")
        self.quote_text_entry = ctk.CTkEntry(q_c1)
        self.quote_text_entry.pack(fill="x")

        q_c2 = ctk.CTkFrame(q_r, fg_color="transparent")
        q_c2.pack(side="right", fill="x", padx=(8, 0))
        ctk.CTkLabel(q_c2, text="Quote Author:").pack(anchor="w")
        self.quote_author_entry = ctk.CTkEntry(q_c2, width=200)
        self.quote_author_entry.pack(fill="x")

        # BANNERS & SLOGAN
        banner_frame = ctk.CTkFrame(scroll)
        banner_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(banner_frame, text="Banners & Footer Slogan", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(banner_frame, text="Breaking News Banner (Optional, e.g. for emergencies):").pack(anchor="w", padx=12, pady=(4, 2))
        self.breaking_entry = ctk.CTkEntry(banner_frame)
        self.breaking_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(banner_frame, text="Bottom Footer Slogan:").pack(anchor="w", padx=12, pady=(4, 2))
        self.footer_entry = ctk.CTkEntry(banner_frame)
        self.footer_entry.pack(fill="x", padx=12, pady=(0, 10))

        # VISUAL THEME & MOTION
        theme_frame = ctk.CTkFrame(scroll)
        theme_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(theme_frame, text="Broadsheet Styling & Magic", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        t_row = ctk.CTkFrame(theme_frame, fg_color="transparent")
        t_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(t_row, text="Broadsheet Theme:").pack(side="left", padx=(0, 12))
        self.theme_var = ctk.StringVar(value=PaperTheme.ORIGINAL_PROPHET.value)
        self.theme_menu = ctk.CTkOptionMenu(
            t_row,
            variable=self.theme_var,
            values=PaperTheme.choices(),
            width=220,
        )
        self.theme_menu.pack(side="left")

        self.motion_var = ctk.BooleanVar(value=True)
        self.motion_check = ctk.CTkCheckBox(
            theme_frame,
            text="Enable Magical Photo Motion (Subtle alive portraits in browser)",
            variable=self.motion_var,
        )
        self.motion_check.pack(anchor="w", padx=12, pady=(4, 12))

    def _load_edition_into_ui(self):
        """Populates UI widgets from current `self.edition`."""
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, self.edition.paper_title)

        self.tagline_entry.delete(0, "end")
        self.tagline_entry.insert(0, self.edition.tagline)

        self.topic_bar_entry.delete(0, "end")
        self.topic_bar_entry.insert(0, getattr(self.edition, "topic_bar", "NEWS ★ SPELLS ★ EVENTS ★ RUMOURS ★ HOGWARTS ★ THE MINISTRY"))

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
        self.quote_text_entry.insert(0, getattr(self.edition, "quote_text", "It is our choices that show what we truly are, far more than our abilities."))

        self.quote_author_entry.delete(0, "end")
        self.quote_author_entry.insert(0, getattr(self.edition, "quote_author", "PROFESSOR FIG"))

        self.breaking_entry.delete(0, "end")
        self.breaking_entry.insert(0, self.edition.breaking_banner)

        self.footer_entry.delete(0, "end")
        self.footer_entry.insert(0, getattr(self.edition, "footer_slogan", "GOOD NEWS, BRIGHTER DAYS, A MORE MAGICAL TOMORROW"))

        self.theme_var.set(self.edition.theme)
        self.motion_var.set(self.edition.magical_motion)

        self._refresh_stories_list()

    def _sync_settings_from_ui(self):
        """Updates `self.edition` attributes from the UI inputs."""
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
        self.edition.theme = self.theme_var.get()
        self.edition.magical_motion = self.motion_var.get()

    def _refresh_stories_list(self):
        for widget in self.stories_scroll.winfo_children():
            widget.destroy()

        self.story_item_frames.clear()

        if not self.edition.stories:
            empty_lbl = ctk.CTkLabel(
                self.stories_scroll,
                text="No stories added yet.\nClick '➕ Add Story' or load an issue preset above.",
                font=ctk.CTkFont(size=13),
                text_color="gray60",
                justify="center",
            )
            empty_lbl.pack(pady=40)
            self._select_story(None)
            self.status_lbl.configure(text="No stories in current edition.")
            return

        for idx, story in enumerate(self.edition.stories):
            card = self._create_story_card(story, idx)
            card.pack(fill="x", pady=4)
            self.story_item_frames[story.id] = card

        if self.selected_story_id and any(s.id == self.selected_story_id for s in self.edition.stories):
            self._select_story(self.selected_story_id)
        elif self.edition.stories:
            self._select_story(self.edition.stories[0].id)

        self.status_lbl.configure(text=f"Total: {len(self.edition.stories)} stories in broadsheet edition.")

    def _create_story_card(self, story: Story, index: int) -> ctk.CTkFrame:
        prio = story.priority
        if prio == StoryPriority.COVER.value:
            badge_text = "🌟 COVER HERO"
            badge_color = "#992b2b"
        elif prio == StoryPriority.MAJOR.value:
            badge_text = "📰 MAJOR FEATURE"
            badge_color = "#355b82"
        elif prio == StoryPriority.COLUMN.value:
            badge_text = "📑 SIDE COLUMN"
            badge_color = "#4c6643"
        else:
            badge_text = "📜 NOTICE / LORE"
            badge_color = "#7a6229"

        card = ctk.CTkFrame(self.stories_scroll, fg_color=("#332b24", "#26201b"), corner_radius=6)
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=8)

        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        badge = ctk.CTkLabel(
            top_row,
            text=f" {badge_text} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=badge_color,
            corner_radius=4,
            text_color="#ffffff",
        )
        badge.pack(side="left")

        if story.image_path and os.path.isfile(story.image_path):
            img_ind = ctk.CTkLabel(top_row, text="📷 Image attached", font=ctk.CTkFont(size=10), text_color="#d6ba8d")
            img_ind.pack(side="left", padx=8)

        headline_lbl = ctk.CTkLabel(
            content,
            text=story.headline or "[Untitled Headline]",
            font=ctk.CTkFont(family="Georgia", size=13, weight="bold"),
            anchor="w",
            justify="left",
        )
        headline_lbl.pack(fill="x", pady=(4, 2))

        meta_info = f"{story.author} • {story.location_tag}" if story.location_tag else story.author
        meta_lbl = ctk.CTkLabel(
            content,
            text=meta_info or story.subheadline or "",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
            justify="left",
        )
        meta_lbl.pack(fill="x")

        for w in [card, content, top_row, badge, headline_lbl, meta_lbl]:
            w.bind("<Button-1>", lambda e, sid=story.id: self._select_story(sid))
            w.bind("<Double-Button-1>", lambda e, s=story: self._open_story_editor(s))

        return card

    def _select_story(self, story_id: str | None = None):
        self.selected_story_id = story_id

        for sid, card in self.story_item_frames.items():
            if sid == story_id:
                card.configure(fg_color=("#4a3e32", "#3b3026"), border_width=2, border_color="#c49a62")
            else:
                card.configure(fg_color=("#332b24", "#26201b"), border_width=0)

        story = next((s for s in self.edition.stories if s.id == story_id), None)
        if not story:
            self.inspect_prio_lbl.configure(text="")
            self.inspect_title_lbl.configure(text="No story selected.")
            self.inspect_author_lbl.configure(text="")
            self.inspect_photo_preview.configure(text="", image=None)
            self.inspect_caption_lbl.configure(text="")
            self.inspect_body_lbl.configure(text="")
            return

        self.inspect_prio_lbl.configure(text=f"Placement: {story.priority}")
        self.inspect_title_lbl.configure(text=story.headline)
        byline_text = f"Byline: {story.author}" if story.author else ""
        if story.location_tag:
            byline_text += f" | Location: {story.location_tag}"
        self.inspect_author_lbl.configure(text=byline_text)

        if story.image_path and os.path.isfile(story.image_path):
            try:
                pil_img = Image.open(story.image_path)
                pil_img.thumbnail((320, 160))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self.inspect_photo_preview.configure(text="", image=ctk_img)
                self.inspect_photo_preview._image = ctk_img
                self.inspect_caption_lbl.configure(text=f"Caption: {story.image_caption}" if story.image_caption else "")
            except Exception:
                self.inspect_photo_preview.configure(text="[Error loading image preview]", image=None)
                self.inspect_caption_lbl.configure(text="")
        else:
            self.inspect_photo_preview.configure(text="[No image attached to story]", image=None)
            self.inspect_caption_lbl.configure(text="")

        preview_text = story.body[:400] + ("..." if len(story.body) > 400 else "")
        self.inspect_body_lbl.configure(text=preview_text)

    def _add_story(self):
        new_story = Story(headline="", priority=StoryPriority.COLUMN.value)
        self._open_story_editor(new_story, is_new=True)

    def _edit_selected_story(self):
        if not self.selected_story_id:
            messagebox.showinfo("No Selection", "Please select a story to edit.", parent=self)
            return
        story = next((s for s in self.edition.stories if s.id == self.selected_story_id), None)
        if story:
            self._open_story_editor(story, is_new=False)

    def _open_story_editor(self, story: Story, is_new: bool = False):
        StoryDialog(self, story=story, on_save=self._on_story_saved)

    def _on_story_saved(self, story: Story, is_new: bool):
        if is_new:
            self.edition.stories.append(story)
        self._refresh_stories_list()
        self._select_story(story.id)
        self.status_lbl.configure(text=f"Saved story: '{story.headline[:35]}'")

    def _delete_selected_story(self):
        if not self.selected_story_id:
            messagebox.showinfo("No Selection", "Please select a story to delete.", parent=self)
            return
        story = next((s for s in self.edition.stories if s.id == self.selected_story_id), None)
        if not story:
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Delete story '{story.headline}'?", parent=self)
        if confirm:
            self.edition.stories = [s for s in self.edition.stories if s.id != self.selected_story_id]
            self.selected_story_id = None
            self._refresh_stories_list()
            self.status_lbl.configure(text="Story removed from edition.")

    def _move_story_up(self):
        if not self.selected_story_id:
            return
        idx = next((i for i, s in enumerate(self.edition.stories) if s.id == self.selected_story_id), -1)
        if idx > 0:
            self.edition.stories[idx - 1], self.edition.stories[idx] = self.edition.stories[idx], self.edition.stories[idx - 1]
            self._refresh_stories_list()
            self._select_story(self.selected_story_id)

    def _move_story_down(self):
        if not self.selected_story_id:
            return
        idx = next((i for i, s in enumerate(self.edition.stories) if s.id == self.selected_story_id), -1)
        if 0 <= idx < len(self.edition.stories) - 1:
            self.edition.stories[idx + 1], self.edition.stories[idx] = self.edition.stories[idx], self.edition.stories[idx + 1]
            self._refresh_stories_list()
            self._select_story(self.selected_story_id)

    def _load_hogwarts_original(self):
        confirm = messagebox.askyesno(
            "Load Hogwarts Original Issue",
            "Replace current stories with the complete Hogwarts Original Issue (Mysterious Transformation, Four Houses, Owl Post, Muggle Studies Discord)?",
            parent=self,
        )
        if confirm:
            self.edition = get_original_hogwarts_edition(".")
            self._load_edition_into_ui()
            self.status_lbl.configure(text="Hogwarts Issue loaded successfully!")

    def _load_azkaban_sample(self):
        confirm = messagebox.askyesno(
            "Load Azkaban Edition",
            "Load the Azkaban / Sirius Black Breakout edition?",
            parent=self,
        )
        if confirm:
            self.edition = get_azkaban_edition(".")
            self._load_edition_into_ui()
            self.status_lbl.configure(text="Azkaban edition loaded successfully!")

    def _new_project(self):
        confirm = messagebox.askyesno("New Project", "Create a blank newspaper edition?", parent=self)
        if confirm:
            self.edition = NewspaperEdition()
            self.current_project_path = None
            self._load_edition_into_ui()
            self.status_lbl.configure(text="New newspaper project created.")

    def _save_project(self):
        self._sync_settings_from_ui()
        if not self.current_project_path:
            return self._save_as_project()

        try:
            self.edition.selected_layout = self._get_selected_template_ids()
            self.edition.save_project_package(self.current_project_path)
            self.status_lbl.configure(text=f"Project saved to: {os.path.basename(self.current_project_path)}")
            messagebox.showinfo("Project Saved", f"Newspaper issue package saved successfully:\n{self.current_project_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save project package:\n{str(e)}", parent=self)

    def _save_as_project(self):
        self._sync_settings_from_ui()
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Newspaper Issue Package",
            defaultextension=".prophet",
            filetypes=[
                ("The Daily Prophet Publication (*.prophet)", "*.prophet"),
                ("Legacy Project JSON (*.json)", "*.json"),
                ("All Files", "*.*")
            ],
        )
        if not path:
            return

        self.current_project_path = path
        try:
            self.edition.selected_layout = self._get_selected_template_ids()
            self.edition.save_project_package(self.current_project_path)
            self.status_lbl.configure(text=f"Project saved as: {os.path.basename(self.current_project_path)}")
            messagebox.showinfo("Project Saved", f"Newspaper issue package saved successfully:\n{self.current_project_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save project package:\n{str(e)}", parent=self)

    def _open_project(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Open Newspaper Issue",
            filetypes=[
                ("The Daily Prophet Publication (*.prophet)", "*.prophet"),
                ("Legacy Project JSON (*.json)", "*.json"),
                ("All Files", "*.*")
            ],
        )
        if path:
            try:
                self.edition = NewspaperEdition.load_project_package(
                    path,
                    cache_base_dir=os.path.join(self.base_dir, "output", "projects_cache")
                )
                self.current_project_path = path
                self._load_edition_into_ui()

                # Restore selected layout in UI dropdown if stored in package
                if hasattr(self.edition, "selected_layout") and self.edition.selected_layout:
                    for label, tid in getattr(self, "layout_map", {}).items():
                        if self.edition.selected_layout == tid:
                            self.template_selector.set(label)
                            self._on_layout_changed(label)
                            break

                self.status_lbl.configure(text=f"Loaded project: {os.path.basename(path)}")
                messagebox.showinfo("Project Loaded", f"Newspaper issue loaded successfully:\n{os.path.basename(path)}", parent=self)
            except Exception as e:
                messagebox.showerror("Error Opening Project", f"Could not load project file:\n{str(e)}", parent=self)

    def _generate_html(self, embed_images: bool = True, export_mode: bool = False) -> str:
        self._sync_settings_from_ui()
        return generate_newspaper_html(self.edition, embed_images=embed_images, export_mode=export_mode)

    def _preview_newspaper(self):
        self._sync_settings_from_ui()
        tids = self._get_selected_template_ids()
        target_tid = tids[0] if isinstance(tids, list) else tids
        self.status_lbl.configure(text=f"Generating publication preview for {target_tid.replace('_', ' ').title()}...")

        try:
            renderer = NativeBroadsheetRenderer(".")
            img = renderer.render_template(self.edition, template_id=target_tid, scale=1.5)
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), f"daily_prophet_preview_{target_tid}.png")
            img.save(temp_path, "PNG")
            opened = open_image_preview(temp_path)
            if opened:
                self.status_lbl.configure(text=f"Preview opened for {target_tid.replace('_', ' ').title()}.")
            else:
                self.status_lbl.configure(text="Preview saved to temporary directory.")
        except Exception as e:
            messagebox.showerror("Preview Error", f"Unable to generate preview:\n{str(e)}", parent=self)

    def _open_in_browser(self):
        html = self._generate_html(embed_images=True, export_mode=False)
        open_in_browser(html)
        self.status_lbl.configure(text="Opened publication in browser.")

    def _export_html(self):
        html = self._generate_html(embed_images=True, export_mode=False)
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Standalone Newspaper HTML",
            defaultextension=".html",
            filetypes=[("HTML Document", "*.html"), ("All Files", "*.*")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.status_lbl.configure(text=f"Exported HTML to: {os.path.basename(path)}")
            messagebox.showinfo(
                "Export Complete",
                f"Newspaper exported successfully as standalone HTML.\n\nSaved to:\n{path}",
                parent=self,
            )

    def _refresh_layout_options(self, preferred_selection=None):
        """Dynamically reloads layouts from individual .prophettemplate files and populates the layout menu."""
        data = load_layout_definitions(base_dir=getattr(self, 'base_dir', '.'))
        self.raw_layout_defs = data

        self.layout_map = {}
        self.layout_meta = {}

        # Scan all single (non-alias) layouts
        single_keys = [k for k in data.keys() if not k.startswith("additional_")]
        for k in single_keys:
            info = data[k]
            label = info.get("label", k.replace("_", " ").title())
            self.layout_map[label] = k
            self.layout_meta[k] = {
                "width": info.get("width", 1024),
                "height": info.get("height", 1400),
                "slots": len(info.get("slots", []))
            }

        # Multi-page option for all layouts
        if len(single_keys) > 1:
            multi_label = f"📚 Full {len(single_keys)}-Page Wizarding Publication (Multi-Page)"
            self.layout_map[multi_label] = single_keys

        labels = list(self.layout_map.keys())
        self.template_selector.configure(values=labels)

        current = preferred_selection or self.template_selector.get()
        if current in self.layout_map:
            self.template_selector.set(current)
        elif labels:
            self.template_selector.set(labels[0])

        self._on_layout_changed(self.template_selector.get())

    def _on_layout_changed(self, choice: str):
        tids = self._get_selected_template_ids()
        if isinstance(tids, list):
            self.layout_info_lbl.configure(text=f"Multi-Page Issue • {len(tids)} Full Pages")
            self.status_lbl.configure(text=f"Selected: {choice} ({len(tids)} pages).")
        else:
            meta = getattr(self, "layout_meta", {}).get(tids, {})
            w = meta.get("width", 1122)
            h = meta.get("height", 1402)
            slots_n = meta.get("slots", 18)

            local_defs = getattr(self, "raw_layout_defs", {})
            edition_layout = self.edition.custom_layouts.get(tids) if hasattr(self.edition, "custom_layouts") else None
            local_layout = local_defs.get(tids)

            from ..template_package import is_layout_modified
            is_mod = is_layout_modified(edition_layout, local_layout) if (edition_layout and local_layout) else False
            is_bundled = meta.get("bundled", True)
            status = LayoutStatus.determine(is_bundled, is_mod)

            badge = " • [Modified]" if status == LayoutStatus.MODIFIED else ""
            self.layout_info_lbl.configure(text=f"{w}x{h} Broadsheet • {slots_n} Content Slots{badge}")
            if hasattr(self, "status_lbl"):
                self.status_lbl.configure(text=f"Layout changed to: {choice}")

    def _get_selected_template_ids(self) -> str | List[str]:
        selected = self.template_selector.get()
        if hasattr(self, "layout_map") and selected in self.layout_map:
            return self.layout_map[selected]
        return "layout_1"

    def _view_wireframe_mask(self):
        tids = self._get_selected_template_ids()
        first_id = tids[0] if isinstance(tids, list) else tids
        mask_file = os.path.join("assets", "templates", "masks", f"{first_id}_wireframe.png")
        if not os.path.exists(mask_file):
            alt_mask = os.path.join("assets", "templates", "masks", f"additional_{first_id}_wireframe.png")
            if os.path.exists(alt_mask):
                mask_file = alt_mask

        if os.path.exists(mask_file):
            abs_mask = os.path.abspath(mask_file)
            try:
                os.startfile(abs_mask)
                self.status_lbl.configure(text=f"Opened wireframe mask for {first_id.replace('_', ' ').title()}.")
            except Exception as e:
                messagebox.showerror("Wireframe Error", f"Could not open mask: {e}", parent=self)
        else:
            messagebox.showwarning("Mask Not Found", f"Wireframe mask not found: {mask_file}", parent=self)

    def _open_layout_editor(self):
        tids = self._get_selected_template_ids()
        target_tid = tids[0] if isinstance(tids, list) else tids
        LayoutEditorWindow(
            self,
            initial_layout=target_tid,
            edition=self.edition,
            on_project_save=self._on_layout_saved_to_project,
            on_global_change=self._refresh_layout_options,
            base_dir="."
        )
        self.status_lbl.configure(text=f"Opened Layout Slot Editor for {target_tid.replace('_', ' ').title()}.")

    def _on_layout_saved_to_project(self):
        self._on_layout_changed(self.template_selector.get())
        self.status_lbl.configure(text="Custom layout slots saved to this issue! Issue modified.")

    def _export_pdf(self):
        self._sync_settings_from_ui()
        tids = self._get_selected_template_ids()
        page_count_str = f"{len(tids)} pages" if isinstance(tids, list) else "1 page"
        self.status_lbl.configure(text=f"Rendering PDF ({page_count_str})...")

        pdf_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Newspaper to PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf"), ("All Files", "*.*")],
        )
        if not pdf_path:
            return

        success, msg = export_native_pdf(self.edition, pdf_path, template_ids=tids, scale=2.0)
        if success:
            self.status_lbl.configure(text=f"Successfully exported PDF to: {os.path.basename(pdf_path)}")
            messagebox.showinfo(
                "PDF Export Complete",
                f"Your Daily Prophet PDF has been created successfully.\n\nPages: {page_count_str}\nSaved to:\n{pdf_path}",
                parent=self
            )
        else:
            self.status_lbl.configure(text="PDF export failed.")
            messagebox.showerror("PDF Export Error", msg, parent=self)

    def _export_image(self):
        self._sync_settings_from_ui()
        tids = self._get_selected_template_ids()
        tid = tids[0] if isinstance(tids, list) else tids
        self.status_lbl.configure(text=f"Rendering image for {tid.replace('_', ' ').title()}...")

        img_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Newspaper to Image (PNG or JPG)",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg;*.jpeg"), ("All Files", "*.*")],
        )
        if not img_path:
            return

        success, msg = export_native_image(self.edition, img_path, template_id=tid, scale=2.0)
        if success:
            self.status_lbl.configure(text=f"Successfully exported Image to: {os.path.basename(img_path)}")
            messagebox.showinfo(
                "Image Export Complete",
                f"Your Daily Prophet Image has been created successfully in high resolution.\n\nSaved to:\n{img_path}",
                parent=self,
            )
        else:
            self.status_lbl.configure(text="Image export failed.")
            messagebox.showerror("Image Export Error", msg, parent=self)

    def _apply_win32_icon(self):
        """Explicitly set high-resolution native Windows icons on the HWND to bypass Tk downsampling."""
        if sys.platform != "win32" or not hasattr(self, "icon_ico") or not os.path.exists(self.icon_ico):
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = self.winfo_id()
            root_hwnd = user32.GetAncestor(hwnd, 2)  # GA_ROOT
            target_hwnd = root_hwnd if root_hwnd else hwnd

            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1

            cx_big = user32.GetSystemMetrics(11)  # SM_CXICON
            cy_big = user32.GetSystemMetrics(12)  # SM_CYICON
            cx_sm = user32.GetSystemMetrics(49)   # SM_CXSMICON
            cy_sm = user32.GetSystemMetrics(50)   # SM_CYSMICON

            hicon_big = user32.LoadImageW(None, self.icon_ico, IMAGE_ICON, cx_big, cy_big, LR_LOADFROMFILE)
            hicon_sm = user32.LoadImageW(None, self.icon_ico, IMAGE_ICON, cx_sm, cy_sm, LR_LOADFROMFILE)

            if hicon_big:
                user32.SendMessageW(target_hwnd, WM_SETICON, ICON_BIG, hicon_big)
            if hicon_sm:
                user32.SendMessageW(target_hwnd, WM_SETICON, ICON_SMALL, hicon_sm)
        except Exception:
            pass
