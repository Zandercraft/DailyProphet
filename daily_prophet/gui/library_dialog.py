"""Visual Image Library dialog for selecting Harry Potter & Hogwarts Legacy artwork."""
import os
import customtkinter as ctk
from PIL import Image
from typing import Callable, Optional, Dict, List


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
        top_frame = ctk.CTkFrame(self, fg_color="#2b231c", corner_radius=0, height=55)
        top_frame.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            top_frame,
            text="🏰 Hogwarts Artwork & Character Library",
            font=ctk.CTkFont(family="Georgia", size=17, weight="bold"),
            text_color="#f5ede0",
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            top_frame,
            text="Select an illustration or transparent character cutout for your story",
            font=ctk.CTkFont(family="Georgia", size=12, slant="italic"),
            text_color="#c4b7a5",
        ).pack(side="left", padx=10, pady=12)

        # Tab view for categories
        self.tabview = ctk.CTkTabview(self, fg_color="#1c1713")
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
                name_text += " (Cutout ✨)"

            ctk.CTkLabel(
                card,
                text=name_text,
                font=ctk.CTkFont(family="Georgia", size=12, weight="bold"),
                text_color="#f5ede0",
                wraplength=210,
            ).pack(padx=8, pady=2)

            # Choose button
            btn = ctk.CTkButton(
                card,
                text="Use as Inline Cutout" if item["is_cutout"] else "Select Image",
                fg_color="#6e1919" if item["is_cutout"] else "#3d3226",
                hover_color="#872222" if item["is_cutout"] else "#574838",
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
