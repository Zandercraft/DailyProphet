"""Story Editor dialog for The Daily Prophet."""

import os
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from ..models import Story, StoryPriority, ImageAlign, BoxStyle
from .library_dialog import ImageLibraryDialog
from .theme import Theme, IconManager


class StoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, story: Story = None, on_save=None):
        super().__init__(parent)
        self.story = story or Story()
        self.on_save = on_save
        self.is_new = story is None

        self.title("Edit Newspaper Story" if not self.is_new else "Add New Story")
        self.geometry("780x820")
        self.minsize(680, 650)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self):
        # Header banner
        Theme.create_header_banner(
            self, title="Story Article Editor", subtitle="Configure headline, body text, priority, and cutout artwork"
        )

        # Scrollable container for form fields
        scroll_container = ctk.CTkScrollableFrame(self)
        scroll_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # 1. PRIORITY LEVEL (CRITICAL FOR LAYOUT)
        prio_frame = ctk.CTkFrame(scroll_container)
        prio_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(
            prio_frame,
            text="Story Priority / Placement Role:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            prio_frame,
            text="• Cover Story: Giant headline, front-page centerpiece & multi-column spread\n"
            "• Major Feature: Secondary lead, prominent 2-column block\n"
            "• Side Column: Vertical newspaper column with dividing rules\n"
            "• Notice / Brief: Boxed bulletin, Ministry decree or classified snippet",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray70"),
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 6))

        self.priority_var = ctk.StringVar(value=self.story.priority)
        self.priority_menu = ctk.CTkOptionMenu(
            prio_frame,
            variable=self.priority_var,
            values=StoryPriority.choices(),
            width=280,
            command=self._on_priority_changed,
        )
        self.priority_menu.pack(anchor="w", padx=12, pady=(0, 10))

        # 2. HEADLINE & SUBHEADLINE
        meta_frame = ctk.CTkFrame(scroll_container)
        meta_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(meta_frame, text="Headline (Main Title):", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        self.headline_entry = ctk.CTkEntry(meta_frame, placeholder_text="e.g. MASS BREAKOUT FROM AZKABAN!")
        self.headline_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(meta_frame, text="Subheadline / Kicker (Secondary line):").pack(anchor="w", padx=12, pady=(2, 2))
        self.subheadline_entry = ctk.CTkEntry(
            meta_frame, placeholder_text="e.g. Ministry confirms Sirius Black at large; Dementor patrols increased"
        )
        self.subheadline_entry.pack(fill="x", padx=12, pady=(0, 8))

        # Author and Location row
        row_frame = ctk.CTkFrame(meta_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=12, pady=(0, 8))

        col1 = ctk.CTkFrame(row_frame, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(col1, text="Author / Byline:").pack(anchor="w")
        self.author_entry = ctk.CTkEntry(col1, placeholder_text="e.g. By Rita Skeeter, Special Inquirer")
        self.author_entry.pack(fill="x")

        col2 = ctk.CTkFrame(row_frame, fg_color="transparent")
        col2.pack(side="right", fill="x", expand=True, padx=(8, 0))
        ctk.CTkLabel(col2, text="Location Tag:").pack(anchor="w")
        self.location_entry = ctk.CTkEntry(col2, placeholder_text="e.g. LONDON / HOGSMEADE")
        self.location_entry.pack(fill="x")

        # 3. PHOTO & CAPTION
        photo_frame = ctk.CTkFrame(scroll_container)
        photo_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(
            photo_frame, text="Accompanying Photograph / Moving Portrait:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 2))

        picker_row = ctk.CTkFrame(photo_frame, fg_color="transparent")
        picker_row.pack(fill="x", padx=12, pady=(0, 6))

        self.image_path_var = ctk.StringVar(value=self.story.image_path)
        self.image_path_entry = ctk.CTkEntry(
            picker_row, textvariable=self.image_path_var, placeholder_text="No image selected (optional)"
        )
        self.image_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            picker_row,
            text=" Browse Image...",
            image=IconManager.get_icon("folder-open", size=13),
            compound="left",
            width=130,
            command=self._browse_image,
        )
        browse_btn.pack(side="left", padx=(0, 6))

        lib_btn = ctk.CTkButton(
            picker_row,
            text=" Image Library...",
            image=IconManager.get_icon("image", size=13),
            compound="left",
            width=135,
            fg_color=Theme.BTN_SECONDARY[0],
            hover_color=Theme.BTN_SECONDARY[1],
            command=lambda: self._open_library(is_cutout_target=False),
        )
        lib_btn.pack(side="left", padx=(0, 6))

        clear_img_btn = ctk.CTkButton(
            picker_row,
            text=" Clear",
            image=IconManager.get_icon("x", size=12),
            compound="left",
            width=65,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._clear_image,
        )
        clear_img_btn.pack(side="left")

        # Thumbnail display
        self.thumb_preview = ctk.CTkLabel(photo_frame, text="[No photo chosen]", height=110)
        self.thumb_preview.pack(pady=4)

        ctk.CTkLabel(photo_frame, text="Photo Caption:").pack(anchor="w", padx=12, pady=(4, 2))
        self.caption_entry = ctk.CTkEntry(
            photo_frame, placeholder_text="e.g. Sirius Black photographed during initial apprehension."
        )
        self.caption_entry.pack(fill="x", padx=12, pady=(0, 8))

        # 3b. INLINE TRANSPARENT CHARACTER / CUTOUT
        cutout_box = ctk.CTkFrame(photo_frame, fg_color="#2b231c", corner_radius=6)
        cutout_box.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(
            cutout_box,
            text="Inline Transparent Cutout (Characters, Creatures, Artifacts):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f5ede0",
        ).pack(anchor="w", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            cutout_box,
            text="Transparent PNGs allow text to flow and morph directly around the character silhouette.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#c2b4a1",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        cutout_row = ctk.CTkFrame(cutout_box, fg_color="transparent")
        cutout_row.pack(fill="x", padx=10, pady=(0, 6))

        self.inline_path_var = ctk.StringVar(value=self.story.inline_image_path)
        self.inline_entry = ctk.CTkEntry(
            cutout_row, textvariable=self.inline_path_var, placeholder_text="No transparent cutout selected"
        )
        self.inline_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        cutout_lib_btn = ctk.CTkButton(
            cutout_row,
            text=" Select Cutout...",
            image=IconManager.get_icon("sparkles", size=13),
            compound="left",
            width=135,
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            command=lambda: self._open_library(is_cutout_target=True),
        )
        cutout_lib_btn.pack(side="left", padx=(0, 6))

        clear_cutout_btn = ctk.CTkButton(
            cutout_row,
            text=" Clear",
            image=IconManager.get_icon("x", size=12),
            compound="left",
            width=65,
            fg_color=Theme.BTN_CONTROL[0],
            hover_color=Theme.BTN_CONTROL[1],
            command=self._clear_cutout,
        )
        clear_cutout_btn.pack(side="left")

        # Alignment row
        align_row = ctk.CTkFrame(cutout_box, fg_color="transparent")
        align_row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(align_row, text="Cutout Alignment:").pack(side="left", padx=(0, 8))
        self.inline_align_var = ctk.StringVar(value=str(self.story.inline_image_align or ImageAlign.RIGHT.value))
        self.align_menu = ctk.CTkOptionMenu(
            align_row, variable=self.inline_align_var, values=ImageAlign.choices(), width=110
        )
        self.align_menu.pack(side="left")

        # 4. PULL QUOTE & BOX STYLE
        opt_frame = ctk.CTkFrame(scroll_container)
        opt_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(opt_frame, text="Highlight Pull Quote (Callout text):").pack(anchor="w", padx=12, pady=(8, 2))
        self.quote_entry = ctk.CTkEntry(
            opt_frame, placeholder_text="e.g. 'He could be anywhere, disguised or lurking in shadow.'"
        )
        self.quote_entry.pack(fill="x", padx=12, pady=(0, 8))

        box_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        box_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(box_row, text="Box Style (for Notices/Briefs):").pack(side="left", padx=(0, 10))
        self.box_style_var = ctk.StringVar(value=str(self.story.box_style or BoxStyle.STANDARD.value))
        self.box_style_menu = ctk.CTkOptionMenu(
            box_row,
            variable=self.box_style_var,
            values=BoxStyle.choices(),
            width=180,
        )
        self.box_style_menu.pack(side="left")

        # 5. ARTICLE BODY
        body_frame = ctk.CTkFrame(scroll_container)
        body_frame.pack(fill="both", expand=True, pady=6)

        ctk.CTkLabel(
            body_frame, text="Article Body Text (paragraphs separated by blank lines):", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.body_text = ctk.CTkTextbox(body_frame, height=220, font=ctk.CTkFont(size=12))
        self.body_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Bottom Action Bar
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=20, pady=10)

        cancel_btn = ctk.CTkButton(
            action_bar,
            text=" Cancel",
            image=IconManager.get_icon("x", size=13),
            compound="left",
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray80"),
            command=self.destroy,
            width=100,
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        save_btn = ctk.CTkButton(
            action_bar,
            text=" Save Story Article",
            image=IconManager.get_icon("save", size=14),
            compound="left",
            fg_color=Theme.BTN_PRIMARY[0],
            hover_color=Theme.BTN_PRIMARY[1],
            font=ctk.CTkFont(weight="bold"),
            command=self._save_story,
            width=165,
        )
        save_btn.pack(side="right")

    def _populate_fields(self):
        self.headline_entry.insert(0, self.story.headline)
        self.subheadline_entry.insert(0, self.story.subheadline)
        self.author_entry.insert(0, self.story.author)
        self.location_entry.insert(0, self.story.location_tag)
        self.caption_entry.insert(0, self.story.image_caption)
        self.quote_entry.insert(0, self.story.pull_quote)
        self.body_text.insert("1.0", self.story.body)
        self._update_thumbnail(self.story.image_path)

    def _on_priority_changed(self, choice):
        # Adjust UI hints if needed
        pass

    def _open_library(self, is_cutout_target: bool = False):
        def _on_select(path: str, is_cutout: bool):
            if is_cutout_target or is_cutout:
                self.inline_path_var.set(path)
            else:
                self.image_path_var.set(path)
                self._update_thumbnail(path)

        ImageLibraryDialog(self, on_select=_on_select, base_dir=".")

    def _clear_cutout(self):
        self.inline_path_var.set("")

    def _browse_image(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Story Photograph",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.webp;*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.image_path_var.set(path)
            self._update_thumbnail(path)

    def _clear_image(self):
        self.image_path_var.set("")
        self._update_thumbnail("")

    def _update_thumbnail(self, path: str):
        if not path or not os.path.isfile(path):
            self.thumb_preview.configure(text="[No photograph selected]", image=None)
            return

        try:
            pil_img = Image.open(path)
            pil_img.thumbnail((160, 110))
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            self.thumb_preview.configure(text="", image=ctk_img)
            self.thumb_preview._image = ctk_img  # prevent garbage collection
        except Exception:
            self.thumb_preview.configure(text="[Could not load image preview]", image=None)

    def _save_story(self):
        headline = self.headline_entry.get().strip()
        if not headline:
            messagebox.showwarning("Headline Required", "Please enter a headline for this story.", parent=self)
            return

        self.story.headline = headline
        self.story.subheadline = self.subheadline_entry.get().strip()
        self.story.author = self.author_entry.get().strip()
        self.story.location_tag = self.location_entry.get().strip()
        self.story.priority = self.priority_var.get()
        self.story.image_path = self.image_path_var.get().strip()
        self.story.inline_image_path = self.inline_path_var.get().strip()
        self.story.inline_image_align = self.inline_align_var.get()
        self.story.image_caption = self.caption_entry.get().strip()
        self.story.pull_quote = self.quote_entry.get().strip()
        self.story.box_style = self.box_style_var.get()
        self.story.body = self.body_text.get("1.0", "end-1c").strip()

        if self.on_save:
            self.on_save(self.story, self.is_new)
        self.destroy()
