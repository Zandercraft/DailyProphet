"""Data models for The Daily Prophet newspaper generator."""
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import json
import os
import zipfile
from typing import List, Optional


class StoryPriority(str, Enum):
    COVER = "Cover Story (Hero)"
    MAJOR = "Major Feature / Side Lead"
    COLUMN = "Side Column"
    SNIPPET = "Notice / Brief / Lore"

    @classmethod
    def choices(cls):
        return [p.value for p in cls]

    @classmethod
    def from_string(cls, val: str) -> "StoryPriority":
        for member in cls:
            if member.value == val or member.name == val:
                return member
        return cls.COLUMN


@dataclass
class Story:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    headline: str = ""
    subheadline: str = ""
    author: str = ""
    priority: str = StoryPriority.COVER.value
    body: str = ""
    image_path: str = ""
    image_caption: str = ""
    inline_image_path: str = ""  # Transparent cutout image for inline text-wrapping
    inline_image_align: str = "right"  # "right", "left", "center"
    character_tag: str = ""  # e.g., "Professor Fig", "Severus Snape", "Sorting Hat"
    pull_quote: str = ""
    box_style: str = "standard"  # "standard", "ornate_box", "parchment_scroll", "wanted_poster", "speech_quote", "banner_feature"
    location_tag: str = ""  # e.g., "HOGWARTS, SCOTLAND", "LONDON", "HOGSMEADE"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Story":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class NewspaperEdition:
    paper_title: str = "The Daily Prophet"
    tagline: str = "THE WIZARDING WORLD'S MOST TRUSTED SOURCE OF NEWS"
    topic_bar: str = "HOGWARTS ★ HOGSMEADE ★ MINISTRY ★ MAGICAL CREATURES ★ COMMUNITY"
    edition_date: str = "22 OCTOBER"
    edition_day: str = "THURSDAY"
    issue_number: str = "EDITION No. 317"
    edition_label: str = "HOGWARTS EDITION"
    price: str = "1 KNUT"
    weather: str = "Mild and Misty with Chance of Spells"
    top_left_banner: str = "WEATHER: Castle Weather - Mild and Misty"
    top_right_banner: str = "HOGWARTS COMMUNITY & CASTLE DISPATCH"
    breaking_banner: str = ""
    footer_slogan: str = "GOOD NEWS, BRIGHTER DAYS, A MORE MAGICAL TOMORROW"
    theme: str = "original_prophet"  # "original_prophet", "parchment", "classic_newsprint", "clean_print"
    border_style: str = "ornate_engraved"  # "ornate_engraved", "weathered_border", "clean_ruled"
    magical_motion: bool = True
    quote_author: str = "PROFESSOR FIG"
    quote_text: str = "It is our choices that show what we truly are, far more than our abilities."
    lore_title_1: str = "THIS DAY IN WIZARDING HISTORY"
    lore_body_1: str = "October 22, 1707: The first recorded official appearance of a Boggart was documented by the Department of Magical Creatures, establishing essential protective guidelines for young witches and wizards."
    lore_title_2: str = "DID YOU KNOW? HOGWARTS LORE"
    lore_body_2: str = "The castle's grand staircases move according to an ancient harmonic enchantment placed by Rowena Ravenclaw herself. Exactly one hundred and forty-two flights of stairs connect the towers to the dungeons."
    stories: List[Story] = field(default_factory=list)
    selected_layout: str = "layout_1"
    custom_layouts: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["stories"] = [s.to_dict() for s in self.stories]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "NewspaperEdition":
        stories_data = data.get("stories", [])
        stories = [Story.from_dict(s) for s in stories_data]
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys and k != "stories"}
        return cls(stories=stories, **filtered)

    def save_to_file(self, file_path: str):
        """Saves edition metadata as raw JSON."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str) -> "NewspaperEdition":
        """Loads edition metadata from raw JSON."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_project_package(self, file_path: str):
        """Saves the complete newspaper issue and all embedded media to a single .prophet file."""
        if file_path.endswith(".json"):
            self.save_to_file(file_path)
            return

        if not file_path.endswith(".prophet"):
            file_path += ".prophet"

        edition_dict = self.to_dict()
        media_files_to_pack = {}

        # Scan stories and collect images into package
        for idx, story_dict in enumerate(edition_dict.get("stories", [])):
            for img_key in ["image_path", "inline_image_path"]:
                local_path = story_dict.get(img_key, "")
                if local_path and os.path.isfile(local_path):
                    safe_basename = os.path.basename(local_path)
                    arcname = f"media/story_{idx}_{img_key[:3]}_{safe_basename}"
                    media_files_to_pack[arcname] = os.path.abspath(local_path)
                    story_dict[img_key] = arcname

        # Scan custom layouts for custom background page images
        for lk, ldef in edition_dict.get("custom_layouts", {}).items():
            if isinstance(ldef, dict):
                page_file = ldef.get("page_file", "")
                if page_file and os.path.isfile(page_file):
                    safe_basename = os.path.basename(page_file)
                    arcname = f"media/layout_{lk}_{safe_basename}"
                    media_files_to_pack[arcname] = os.path.abspath(page_file)
                    ldef["page_file"] = arcname

        manifest = {
            "application": "The Daily Prophet",
            "format": "prophet_package",
            "version": "2.0",
            "edition_title": self.paper_title,
            "selected_layout": self.selected_layout,
            "edition_date": self.edition_date,
            "issue_number": self.issue_number
        }

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("edition.json", json.dumps(edition_dict, indent=2, ensure_ascii=False))
            for arcname, local_path in media_files_to_pack.items():
                zf.write(local_path, arcname)

    @classmethod
    def load_project_package(cls, file_path: str, cache_base_dir: str = "output/projects_cache") -> "NewspaperEdition":
        """Loads a newspaper issue from a .prophet package file or legacy .json file."""
        if file_path.endswith(".json"):
            return cls.load_from_file(file_path)

        with zipfile.ZipFile(file_path, "r") as zf:
            edition_data = json.loads(zf.read("edition.json").decode("utf-8"))

            doc_name = os.path.splitext(os.path.basename(file_path))[0]
            extract_dir = os.path.abspath(os.path.join(cache_base_dir, doc_name))
            os.makedirs(extract_dir, exist_ok=True)

            for member in zf.namelist():
                if member.startswith("media/"):
                    zf.extract(member, extract_dir)

            for story_dict in edition_data.get("stories", []):
                for img_key in ["image_path", "inline_image_path"]:
                    val = story_dict.get(img_key, "")
                    if val and val.startswith("media/"):
                        story_dict[img_key] = os.path.join(extract_dir, val.replace("/", os.sep))

            for lk, ldef in edition_data.get("custom_layouts", {}).items():
                if isinstance(ldef, dict):
                    pf = ldef.get("page_file", "")
                    if pf and pf.startswith("media/"):
                        ldef["page_file"] = os.path.join(extract_dir, pf.replace("/", os.sep))

            edition = cls.from_dict(edition_data)
            return edition
