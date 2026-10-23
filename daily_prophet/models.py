"""Data models for The Daily Prophet newspaper generator."""
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import json
import os
import zipfile
import copy
from typing import List, Optional, Dict, Any
from .versioning import FormatVersion, CURRENT_PROJECT_VERSION, project_migration_pipeline
from .layout_models import SlotType, LayoutSlot, LayoutDefinition, LayoutStatus


class StoryPriority(str, Enum):
    """Priority level determining layout placement hierarchy."""
    COVER = "Cover Story (Hero)"
    MAJOR = "Major Feature / Side Lead"
    COLUMN = "Side Column"
    SNIPPET = "Notice / Brief / Lore"

    @classmethod
    def choices(cls) -> List[str]:
        return [p.value for p in cls]

    @classmethod
    def from_string(cls, val: Any) -> "StoryPriority":
        if isinstance(val, StoryPriority):
            return val
        s_val = str(val).strip()
        for member in cls:
            if member.value == s_val or member.name == s_val:
                return member
        return cls.COLUMN


class ImageAlign(str, Enum):
    """Alignment direction for inline transparent cutout silhouettes."""
    RIGHT = "right"
    LEFT = "left"
    CENTER = "center"

    @classmethod
    def choices(cls) -> List[str]:
        return [m.value for m in cls]

    @classmethod
    def from_string(cls, val: Any) -> "ImageAlign":
        if isinstance(val, ImageAlign):
            return val
        s_val = str(val).lower().strip()
        for member in cls:
            if member.value == s_val or member.name.lower() == s_val:
                return member
        return cls.RIGHT


class BoxStyle(str, Enum):
    """Styling motif for notice boxes, decrees, quotes, and callouts."""
    STANDARD = "standard"
    ORNATE_BOX = "ornate_box"
    PARCHMENT_SCROLL = "parchment_scroll"
    WANTED_POSTER = "wanted_poster"
    SPEECH_QUOTE = "speech_quote"
    BANNER_FEATURE = "banner_feature"

    @classmethod
    def choices(cls) -> List[str]:
        return [m.value for m in cls]

    @classmethod
    def from_string(cls, val: Any) -> "BoxStyle":
        if isinstance(val, BoxStyle):
            return val
        s_val = str(val).lower().strip()
        for member in cls:
            if member.value == s_val or member.name.lower() == s_val:
                return member
        return cls.STANDARD


class PaperTheme(str, Enum):
    """Color palette and paper texture theme for newspaper rendering."""
    ORIGINAL_PROPHET = "original_prophet"
    PARCHMENT = "parchment"
    CLASSIC_NEWSPRINT = "classic_newsprint"
    CLEAN_PRINT = "clean_print"

    @classmethod
    def choices(cls) -> List[str]:
        return [m.value for m in cls]

    @classmethod
    def from_string(cls, val: Any) -> "PaperTheme":
        if isinstance(val, PaperTheme):
            return val
        s_val = str(val).lower().strip()
        for member in cls:
            if member.value == s_val or member.name.lower() == s_val:
                return member
        return cls.ORIGINAL_PROPHET


class BorderStyle(str, Enum):
    """Decorative broadsheet boundary engraved rule styling."""
    ORNATE_ENGRAVED = "ornate_engraved"
    WEATHERED_BORDER = "weathered_border"
    CLEAN_RULED = "clean_ruled"

    @classmethod
    def choices(cls) -> List[str]:
        return [m.value for m in cls]

    @classmethod
    def from_string(cls, val: Any) -> "BorderStyle":
        if isinstance(val, BorderStyle):
            return val
        s_val = str(val).lower().strip()
        for member in cls:
            if member.value == s_val or member.name.lower() == s_val:
                return member
        return cls.ORNATE_ENGRAVED


class ExportFormat(str, Enum):
    """File export format targets."""
    PROJECT = "prophet"
    TEMPLATE = "prophettemplate"
    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpg"

    @classmethod
    def choices(cls) -> List[str]:
        return [m.value for m in cls]


@dataclass
class Story:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    headline: str = ""
    subheadline: str = ""
    author: str = ""
    priority: StoryPriority = StoryPriority.COVER
    body: str = ""
    image_path: str = ""
    image_caption: str = ""
    inline_image_path: str = ""  # Transparent cutout image for inline text-wrapping
    inline_image_align: ImageAlign = ImageAlign.RIGHT
    character_tag: str = ""  # e.g., "Professor Fig", "Severus Snape", "Sorting Hat"
    pull_quote: str = ""
    box_style: BoxStyle = BoxStyle.STANDARD
    location_tag: str = ""  # e.g., "HOGWARTS, SCOTLAND", "LONDON", "HOGSMEADE"

    def to_dict(self):
        d = asdict(self)
        d["priority"] = self.priority.value if isinstance(self.priority, StoryPriority) else str(self.priority)
        d["inline_image_align"] = self.inline_image_align.value if isinstance(self.inline_image_align, ImageAlign) else str(self.inline_image_align)
        d["box_style"] = self.box_style.value if isinstance(self.box_style, BoxStyle) else str(self.box_style)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Story":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if "priority" in filtered:
            filtered["priority"] = StoryPriority.from_string(filtered["priority"])
        if "inline_image_align" in filtered:
            filtered["inline_image_align"] = ImageAlign.from_string(filtered["inline_image_align"])
        if "box_style" in filtered:
            filtered["box_style"] = BoxStyle.from_string(filtered["box_style"])
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
    theme: PaperTheme = PaperTheme.ORIGINAL_PROPHET
    border_style: BorderStyle = BorderStyle.ORNATE_ENGRAVED
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
    format_version: str = str(CURRENT_PROJECT_VERSION)

    def to_dict(self):
        d = asdict(self)
        d["stories"] = [s.to_dict() for s in self.stories]
        d["theme"] = self.theme.value if isinstance(self.theme, PaperTheme) else str(self.theme)
        d["border_style"] = self.border_style.value if isinstance(self.border_style, BorderStyle) else str(self.border_style)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "NewspaperEdition":
        stories_data = data.get("stories", [])
        stories = [Story.from_dict(s) for s in stories_data]
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys and k != "stories"}
        if "theme" in filtered:
            filtered["theme"] = PaperTheme.from_string(filtered["theme"])
        if "border_style" in filtered:
            filtered["border_style"] = BorderStyle.from_string(filtered["border_style"])
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

        # Ensure active layout is bundled directly inside the .prophet file
        target_tid = self.selected_layout
        if isinstance(target_tid, list):
            target_tid = target_tid[0] if target_tid else "layout_1"
        if target_tid and target_tid not in edition_dict.get("custom_layouts", {}):
            from .generate_masks import load_layout_definitions
            all_defs = load_layout_definitions()
            if target_tid in all_defs:
                edition_dict.setdefault("custom_layouts", {})[target_tid] = copy.deepcopy(all_defs[target_tid])
                self.custom_layouts[target_tid] = copy.deepcopy(all_defs[target_tid])

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
            "format_version": str(CURRENT_PROJECT_VERSION),
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
            manifest = None
            if "manifest.json" in zf.namelist():
                try:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                except Exception:
                    pass

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

            # Run through migration pipeline (extensible for future format versions)
            raw_ver = "1.0"
            if manifest:
                raw_ver = manifest.get("format_version") or manifest.get("version", "1.0")
            source_ver = FormatVersion.parse(raw_ver)
            migrated_data, was_upgraded, orig_ver = project_migration_pipeline.migrate(edition_data, source_ver)

            edition = cls.from_dict(migrated_data)
            edition.format_version = str(CURRENT_PROJECT_VERSION)
            return edition
