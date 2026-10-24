"""Streamlined Article Composer for The Daily Prophet.

Word-inspired article writing workspace with live auto-fit gauge,
one-click wizarding archetypes, authentic lorem ipsum generator,
and collapsible styling drawers.
"""
from __future__ import annotations
import os
import random
from typing import Optional, Callable
import customtkinter as ctk

from ..models import Story, StoryPriority, BoxStyle
from .theme import Theme, IconManager
from .library_dialog import ImageLibraryDialog


WIZARDING_LOREM_IPSUM = [
    (
        "DIAGON ALLEY POTION INGREDIENT SHORTAGE",
        "Apothecaries across Diagon Alley reported a critical deficit of powdered moonstone and boomslang skin at dawn. The Potions Guild attributes the supply disruption to unseasonable weather over the Scottish Highlands.",
        "Ministry officials urge potion-makers not to seek black-market substitutes from Knockturn Alley, citing hazardous volatility in uncertified cauldrons."
    ),
    (
        "MINISTRY OF MAGIC ISSUES WAND CARE ADVISORY",
        "The Department of Magical Equipment has released an urgent reminder regarding winter core maintenance. Wands containing dragon heartstring require regular polishing with crushed bicorn horn to prevent sporadic backfires during damp spells.",
        "Auror Headquarters confirmed that faulty maintenance was responsible for several minor levitation accidents in central London this morning."
    ),
    (
        "CHUDLEY CANNONS CELEBRATE RARE VICTORY",
        "In a thrilling match that stunned Quidditch enthusiasts at Appleby, the Chudley Cannons secured their first win of the season after Seeker Galvin Gudgeon snatched the Golden Snitch in the ninety-second minute.",
        "Manager Ragmar Dumbleton hailed the triumph as 'the beginning of an unstoppable orange epoch,' amidst exuberant fireworks outside the Leaky Cauldron."
    ),
    (
        "OWL POST EXPEDITION DELAYED BY MOORLAND MIST",
        "Dense magical fog across the moors has forced the Eeylops Owl Emporium courier corps to ground all heavy deliveries until noon. Letters bearing emergency hex-charms are prioritized via great horned owls equipped with enchanted navigational lanterns."
    ),
    (
        "GOBLIN LIAISON OFFICE CLARIFIES VAULT POLICIES",
        "Gringotts Wizarding Bank has issued strict revisions regarding third-party vault inspections. Any wizard attempting entry without certified goblin blood-line verification will be subject to immediate detention by the subterranean security sphinxes."
    )
]


class StoryComposer(ctk.CTkFrame):
    """Rich article composer panel replacing modal popups with in-place editing."""

    def __init__(
        self,
        master,
        on_story_updated: Optional[Callable[[Story], None]] = None,
        base_dir: str = ".",
        **kwargs
    ):
        super().__init__(master, fg_color=Theme.PANEL_BG, corner_radius=6, **kwargs)
        self.on_story_updated = on_story_updated
        self.base_dir = os.path.abspath(base_dir)

        self.current_story: Optional[Story] = None
        self._debounce_timer: Optional[str] = None
        self._is_populating = False
        self._accordion_expanded = False

        self._setup_ui()

    def _setup_ui(self):
        # 1. Header Toolbar: Archetypes & Actions
        header_bar = ctk.CTkFrame(self, fg_color=Theme.HEADER_BG, height=40, corner_radius=4)
        header_bar.pack(fill="x", padx=6, pady=(6, 4))

        ctk.CTkLabel(
            header_bar,
            text=" Article Composer",
            image=IconManager.get_icon("pencil", size=13),
            compound="left",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Theme.TEXT_PARCHMENT
        ).pack(side="left", padx=8)

        # Quick Archetype Presets Menu
        self.archetype_menu = ctk.CTkOptionMenu(
            header_bar,
            values=[
                "Select Archetype Preset...",
                "Breaking Scandal / Alert",
                "Ministry Official Decree",
                "Rita Skeeter Exclusive",
                "Quidditch Match Report",
                "Hogwarts Notice & Snippet"
            ],
            width=180,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=Theme.BTN_NEUTRAL[0],
            button_color=Theme.BTN_NEUTRAL[1],
            command=self._apply_archetype
        )
        self.archetype_menu.pack(side="left", padx=4)

        # Lorem Ipsum Button
        ctk.CTkButton(
            header_bar,
            text=" Wizarding Lorem Ipsum",
            image=IconManager.get_icon("sparkles", size=12),
            compound="left",
            width=150,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=self._insert_lorem_ipsum
        ).pack(side="left", padx=4)

        # 2. Main Scrollable Editing Body
        scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=4, pady=2)

        # Headline
        ctk.CTkLabel(scroll_container, text="Headline (Main Title):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=6, pady=(4, 1))
        self.headline_entry = ctk.CTkEntry(scroll_container, placeholder_text="e.g. MASS BREAKOUT FROM AZKABAN!")
        self.headline_entry.pack(fill="x", padx=6, pady=(0, 4))
        self.headline_entry.bind("<KeyRelease>", self._schedule_update)

        # Subheadline
        ctk.CTkLabel(scroll_container, text="Subheadline / Kicker:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=6, pady=(2, 1))
        self.subhead_entry = ctk.CTkEntry(scroll_container, placeholder_text="e.g. Ministry confirms Sirius Black at large")
        self.subhead_entry.pack(fill="x", padx=6, pady=(0, 4))
        self.subhead_entry.bind("<KeyRelease>", self._schedule_update)

        # Byline & Location Grid
        meta_grid = ctk.CTkFrame(scroll_container, fg_color="transparent")
        meta_grid.pack(fill="x", padx=6, pady=(0, 4))

        col1 = ctk.CTkFrame(meta_grid, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(col1, text="Author / Byline:", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.author_entry = ctk.CTkEntry(col1, placeholder_text="By Rita Skeeter")
        self.author_entry.pack(fill="x")
        self.author_entry.bind("<KeyRelease>", self._schedule_update)

        col2 = ctk.CTkFrame(meta_grid, fg_color="transparent")
        col2.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(col2, text="Location Tag:", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.location_entry = ctk.CTkEntry(col2, placeholder_text="LONDON / HOGSMEADE")
        self.location_entry.pack(fill="x")
        self.location_entry.bind("<KeyRelease>", self._schedule_update)

        # Priority & Slot Fitting Strip
        prio_strip = ctk.CTkFrame(scroll_container, fg_color=Theme.CARD_BG, corner_radius=4)
        prio_strip.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(prio_strip, text="Priority Role:", font=ctk.CTkFont(size=10, weight="bold")).pack(side="left", padx=8, pady=4)
        self.priority_var = ctk.StringVar(value=StoryPriority.COVER.value)
        self.priority_menu = ctk.CTkOptionMenu(
            prio_strip,
            variable=self.priority_var,
            values=StoryPriority.choices(),
            width=180,
            height=24,
            font=ctk.CTkFont(size=10),
            command=self._on_field_changed
        )
        self.priority_menu.pack(side="left", padx=4, pady=4)

        # Auto-Fit & Word Count Indicator
        self.word_meter_lbl = ctk.CTkLabel(
            prio_strip,
            text="Words: 0 • Slot Fit: Optimal",
            font=ctk.CTkFont(size=10),
            text_color="#6bb377"
        )
        self.word_meter_lbl.pack(side="right", padx=10, pady=4)

        # Body Text Area
        body_hdr = ctk.CTkFrame(scroll_container, fg_color="transparent")
        body_hdr.pack(fill="x", padx=6, pady=(4, 1))

        ctk.CTkLabel(body_hdr, text="Article Body Text:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")

        self.body_text = ctk.CTkTextbox(scroll_container, height=160, font=ctk.CTkFont(size=11))
        self.body_text.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.body_text.bind("<KeyRelease>", self._schedule_update)

        # Artwork & Photo Section
        art_box = ctk.CTkFrame(scroll_container, fg_color=Theme.CARD_BG, corner_radius=4)
        art_box.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(art_box, text="Photograph & Character Cutout:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(6, 2))

        art_row = ctk.CTkFrame(art_box, fg_color="transparent")
        art_row.pack(fill="x", padx=8, pady=(0, 6))

        self.photo_path_var = ctk.StringVar()
        self.photo_entry = ctk.CTkEntry(art_row, textvariable=self.photo_path_var, placeholder_text="No photo selected", height=24)
        self.photo_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            art_row,
            text=" Library...",
            image=IconManager.get_icon("image", size=12),
            compound="left",
            width=90,
            height=24,
            font=ctk.CTkFont(size=10),
            command=self._open_library
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            art_row,
            text=" Clear",
            image=IconManager.get_icon("x", size=10),
            compound="left",
            width=60,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=Theme.BTN_CONTROL[0],
            command=self._clear_photo
        ).pack(side="left", padx=2)

        # Caption
        self.caption_entry = ctk.CTkEntry(art_box, placeholder_text="Photo caption...", height=24)
        self.caption_entry.pack(fill="x", padx=8, pady=(0, 6))
        self.caption_entry.bind("<KeyRelease>", self._schedule_update)

        # 3. Collapsible Accordion Drawer for Advanced Tweaks
        self.accordion_btn = ctk.CTkButton(
            scroll_container,
            text=" ▼ Advanced Styling & Decorative Borders",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=Theme.HEADER_BG,
            hover_color="#382e25",
            height=26,
            command=self._toggle_accordion
        )
        self.accordion_btn.pack(fill="x", padx=6, pady=(4, 2))

        self.drawer_frame = ctk.CTkFrame(scroll_container, fg_color=Theme.CARD_BG, corner_radius=4)
        # initially unmapped

        # Drawer contents: Box Style & Pull Quote
        ctk.CTkLabel(self.drawer_frame, text="Box Style / Decorative Border:").pack(anchor="w", padx=8, pady=(6, 2))
        self.box_style_var = ctk.StringVar(value=BoxStyle.STANDARD.value)
        self.box_style_menu = ctk.CTkOptionMenu(
            self.drawer_frame,
            variable=self.box_style_var,
            values=BoxStyle.choices(),
            width=200,
            command=self._on_field_changed
        )
        self.box_style_menu.pack(anchor="w", padx=8, pady=(0, 6))

        ctk.CTkLabel(self.drawer_frame, text="Pull Quote (Callout text):").pack(anchor="w", padx=8, pady=(2, 2))
        self.pull_quote_entry = ctk.CTkEntry(self.drawer_frame, placeholder_text="e.g. 'He could be anywhere, lurking in shadow.'")
        self.pull_quote_entry.pack(fill="x", padx=8, pady=(0, 8))
        self.pull_quote_entry.bind("<KeyRelease>", self._schedule_update)

    def load_story(self, story: Optional[Story]):
        """Populates the composer with the selected story's fields."""
        self.current_story = story
        if not story:
            return

        self._is_populating = True
        self.headline_entry.delete(0, "end")
        self.headline_entry.insert(0, story.headline)

        self.subhead_entry.delete(0, "end")
        self.subhead_entry.insert(0, story.subheadline)

        self.author_entry.delete(0, "end")
        self.author_entry.insert(0, story.author)

        self.location_entry.delete(0, "end")
        self.location_entry.insert(0, story.location_tag)

        self.priority_var.set(story.priority.value if isinstance(story.priority, StoryPriority) else str(story.priority))

        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", story.body)

        self.photo_path_var.set(story.image_path)

        self.caption_entry.delete(0, "end")
        self.caption_entry.insert(0, story.image_caption)

        self.box_style_var.set(story.box_style.value if isinstance(story.box_style, BoxStyle) else str(story.box_style))

        self.pull_quote_entry.delete(0, "end")
        self.pull_quote_entry.insert(0, story.pull_quote)

        self._update_word_meter()
        self._is_populating = False

    def _sync_to_story(self):
        if not self.current_story or self._is_populating:
            return

        self.current_story.headline = self.headline_entry.get().strip()
        self.current_story.subheadline = self.subhead_entry.get().strip()
        self.current_story.author = self.author_entry.get().strip()
        self.current_story.location_tag = self.location_entry.get().strip()
        self.current_story.priority = StoryPriority.from_string(self.priority_var.get())
        self.current_story.body = self.body_text.get("1.0", "end-1c").strip()
        self.current_story.image_path = self.photo_path_var.get().strip()
        self.current_story.image_caption = self.caption_entry.get().strip()
        self.current_story.box_style = BoxStyle.from_string(self.box_style_var.get())
        self.current_story.pull_quote = self.pull_quote_entry.get().strip()

        self._update_word_meter()

        if self.on_story_updated:
            self.on_story_updated(self.current_story)

    def _schedule_update(self, event=None):
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
        self._debounce_timer = self.after(150, self._sync_to_story)

    def _on_field_changed(self, choice=None):
        self._sync_to_story()

    def _update_word_meter(self):
        text = self.body_text.get("1.0", "end-1c")
        words = len(text.split())
        prio = self.priority_var.get()

        # Expected word counts by priority
        targets = {
            StoryPriority.COVER.value: (80, 250),
            StoryPriority.MAJOR.value: (50, 180),
            StoryPriority.COLUMN.value: (30, 120),
            StoryPriority.SNIPPET.value: (10, 60),
        }
        min_w, max_w = targets.get(prio, (30, 150))

        if words < min_w:
            status = "Brief"
            color = "#8fb3de"
        elif min_w <= words <= max_w:
            status = "Optimal"
            color = "#6bb377"
        else:
            status = "Dense (May Overflow)"
            color = "#e07858"

        self.word_meter_lbl.configure(text=f"Words: {words} • Slot Fit: {status}", text_color=color)

    def _apply_archetype(self, choice: str):
        if not self.current_story or choice.startswith("Select"):
            return

        if "Scandal" in choice or "Alert" in choice:
            self.priority_var.set(StoryPriority.COVER.value)
            self.box_style_var.set(BoxStyle.WANTED_POSTER.value)
            if not self.headline_entry.get():
                self.headline_entry.insert(0, "MASS BREAKOUT FROM AZKABAN!")
        elif "Decree" in choice:
            self.priority_var.set(StoryPriority.MAJOR.value)
            self.box_style_var.set(BoxStyle.ORNATE_BOX.value)
            self.author_entry.delete(0, "end")
            self.author_entry.insert(0, "Ministry of Magic Proclamation")
        elif "Rita Skeeter" in choice:
            self.priority_var.set(StoryPriority.MAJOR.value)
            self.box_style_var.set(BoxStyle.PARCHMENT_SCROLL.value)
            self.author_entry.delete(0, "end")
            self.author_entry.insert(0, "By Rita Skeeter, Special Inquirer")
        elif "Quidditch" in choice:
            self.priority_var.set(StoryPriority.COLUMN.value)
            self.box_style_var.set(BoxStyle.STANDARD.value)
            self.author_entry.delete(0, "end")
            self.author_entry.insert(0, "By Quidditch Correspondent")
        elif "Notice" in choice or "Snippet" in choice:
            self.priority_var.set(StoryPriority.SNIPPET.value)
            self.box_style_var.set(BoxStyle.STANDARD.value)

        self._sync_to_story()
        self.archetype_menu.set("Select Archetype Preset...")

    def _insert_lorem_ipsum(self):
        title, para1, *rest = random.choice(WIZARDING_LOREM_IPSUM)
        if not self.headline_entry.get():
            self.headline_entry.insert(0, title)

        full_body = para1
        if rest:
            full_body += "\n\n" + rest[0]

        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", full_body)
        self._sync_to_story()

    def _toggle_accordion(self):
        if self._accordion_expanded:
            self.drawer_frame.pack_forget()
            self.accordion_btn.configure(text=" ▼ Advanced Styling & Decorative Borders")
            self._accordion_expanded = False
        else:
            self.drawer_frame.pack(fill="x", padx=6, pady=(2, 6))
            self.accordion_btn.configure(text=" ▲ Hide Advanced Styling")
            self._accordion_expanded = True

    def _open_library(self):
        def _on_select(path: str, is_cutout: bool):
            self.photo_path_var.set(path)
            self._sync_to_story()

        ImageLibraryDialog(self, on_select=_on_select, base_dir=self.base_dir)

    def _clear_photo(self):
        self.photo_path_var.set("")
        self._sync_to_story()
