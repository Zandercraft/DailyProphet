"""Visual Image Library dialog for selecting Harry Potter & Hogwarts Legacy artwork."""
import os
import customtkinter as ctk
from PIL import Image
from typing import Callable, Dict, List
from .theme import Theme, IconManager


class ImageLibraryDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_select: Callable[[str, bool], None], base_dir: str = "."):
        super().__init__(parent)
        self.title("Hogwarts Image & Character Library")
        self.geometry("860x640")
        self.minsize(740, 500)
        self.on_select = on_select
        self.base_dir = os.path.abspath(base_dir)
        self.thumbnails_cache = []

        self.transient(parent)
        self.grab_set()

        self._scan_library()
        self._setup_ui()

    def _scan_library(self):
        self.library_items = {
            "Characters": [],
            "Creatures & Artifacts": [],
            "Locations & Castles": [],
            "Borders & Ornaments": [],
        }

        lib_dir = os.path.join(self.base_dir, "assets", "library")
        folder_map = {
            "characters": "Characters",
            "creatures_and_artifacts": "Creatures & Artifacts",
            "locations": "Locations & Castles",
            "borders_and_frames": "Borders & Ornaments",
        }

        for sub, cat in folder_map.items():
            dir_path = os.path.join(lib_dir, sub)
            if os.path.isdir(dir_path):
                for f in sorted(os.listdir(dir_path)):
                    if f.lower().endswith((".png", ".jpg", ".jpeg")):
                        full_p = os.path.join(dir_path, f)
                        is_cutout = "_cutout" in f.lower() or "transparent" in f.lower()
                        label = f.replace("_cutout", "").replace("_", " ").replace(".png", "").replace(".jpg", "").title()
                        self.library_items[cat].append({
                            "name": label,
                            "filename": f,
                            "path": full_p,
                            "is_cutout": is_cutout,
                        })

    def _setup_ui(self):
        # Header
        Theme.create_header_banner(
            self,
            title="Artwork & Character Library",
            subtitle="Select an illustration or transparent character cutout for your story"
        )

        # Tab view for categories
        self.tabview = ctk.CTkTabview(self, fg_color=Theme.APP_BG)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=10)

        for cat_name, items in self.library_items.items():
            tab = self.tabview.add(cat_name)
            self._populate_category_tab(tab, items)

    def _populate_category_tab(self, tab, items: List[Dict]):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        if not items:
            ctk.CTkLabel(scroll, text="No images in this category.", text_color="#a89a88").pack(pady=40)
            return

        # Grid of cards
        cols = 3
        for idx, item in enumerate(items):
            row = idx // cols
            col = idx % cols

            card = ctk.CTkFrame(scroll, fg_color="#2b231c", corner_radius=6, border_width=1, border_color="#544436")
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            # Thumbnail
            thumb_img = self._load_thumb(item["path"])
            if thumb_img:
                lbl_img = ctk.CTkLabel(card, image=thumb_img, text="")
                lbl_img.pack(padx=8, pady=(8, 4))

            # Title
            name_text = item["name"]
            if item["is_cutout"]:
                name_text += " (Cutout)"

            ctk.CTkLabel(
                card,
                text=name_text,
                font=ctk.CTkFont(family="Georgia", size=12, weight="bold"),
                text_color="#f5ede0",
                wraplength=210,
            ).pack(padx=8, pady=2)

            # Choose button
            icon = IconManager.get_icon("sparkles" if item["is_cutout"] else "check", size=13)
            btn = ctk.CTkButton(
                card,
                text=" Use as Inline Cutout" if item["is_cutout"] else " Select Image",
                image=icon,
                compound="left",
                fg_color=Theme.BTN_PRIMARY[0] if item["is_cutout"] else Theme.BTN_SECONDARY[0],
                hover_color=Theme.BTN_PRIMARY[1] if item["is_cutout"] else Theme.BTN_SECONDARY[1],
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p=item["path"], c=item["is_cutout"]: self._on_item_chosen(p, c),
            )
            btn.pack(padx=8, pady=(4, 8), fill="x")

        for c in range(cols):
            scroll.grid_columnconfigure(c, weight=1)

    def _load_thumb(self, path: str):
        try:
            with Image.open(path) as im:
                im_copy = im.copy()
                im_copy.thumbnail((200, 130), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=im_copy, dark_image=im_copy, size=im_copy.size)
                self.thumbnails_cache.append(ctk_img)
                return ctk_img
        except Exception:
            return None

    def _on_item_chosen(self, path: str, is_cutout: bool):
        self.on_select(path, is_cutout)
        self.destroy()
