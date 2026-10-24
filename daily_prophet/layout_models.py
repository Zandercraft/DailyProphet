"""Object-oriented domain models for layout definitions, slots, and visual styling."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Union


class SlotType(str, Enum):
    """Enumeration of layout slot content roles across Daily Prophet newspapers."""

    TITLE = "title"
    BANNER = "banner"
    EAR_BOX = "ear_box"
    SLOGAN = "slogan"
    TICKER = "ticker"
    HEADLINE = "headline"
    SUBHEADLINE = "subheadline"
    PHOTO = "photo"
    BODY = "body"
    COLUMN = "column"
    QUOTE = "quote"
    LORE = "lore"
    DIVIDER = "divider"
    FOOTER = "footer"

    @classmethod
    def choices(cls) -> List[str]:
        """Returns string values of all slot types for dropdowns and menus."""
        return [member.value for member in cls]

    @classmethod
    def from_string(cls, val: str | SlotType | object) -> SlotType:
        """Safely parses a string or enum to SlotType, defaulting to BODY."""
        if isinstance(val, SlotType):
            return val
        s_val = str(val).lower().strip()
        for member in cls:
            if member.value == s_val or member.name.lower() == s_val:
                return member
        return cls.BODY

    @property
    def display_name(self) -> str:
        names = {
            SlotType.TITLE: "Newspaper Masthead Title",
            SlotType.BANNER: "Top/Bottom Slate Banner",
            SlotType.EAR_BOX: "Corner Weather/Issue Ear Box",
            SlotType.SLOGAN: "Edition Tagline / Slogan",
            SlotType.TICKER: "Topic Bar / Breaking Ticker",
            SlotType.HEADLINE: "Main Article Headline",
            SlotType.SUBHEADLINE: "Secondary Subheadline",
            SlotType.PHOTO: "Moving Photo / Cutout Frame",
            SlotType.BODY: "Article Body Story Flow",
            SlotType.COLUMN: "Vertical Side Column",
            SlotType.QUOTE: "Callout Speech / Pull Quote",
            SlotType.LORE: "Historical / Hogwarts Lore Block",
            SlotType.DIVIDER: "Decorative Column Divider",
            SlotType.FOOTER: "Footer Slogan & Imprint",
        }
        return names.get(self, self.value.replace("_", " ").title())

    @property
    def ui_colors(self) -> Tuple[str, str]:
        """Returns (fill_hex, outline_hex) for canvas and interactive GUI editing."""
        palette = {
            SlotType.HEADLINE: ("#8B1E1E", "#FF4D4D"),  # Deep Crimson
            SlotType.SUBHEADLINE: ("#B85D19", "#FFA059"),  # Rust Amber
            SlotType.PHOTO: ("#1E5631", "#4DFF88"),  # Forest Emerald Green
            SlotType.BODY: ("#1B365D", "#66A3FF"),  # Ink Navy
            SlotType.COLUMN: ("#2B4C7E", "#7DB4FF"),  # Column Blue
            SlotType.TITLE: ("#4A235A", "#D980FA"),  # Royal Purple
            SlotType.EAR_BOX: ("#641E1E", "#FF7070"),  # Dark Maroon
            SlotType.QUOTE: ("#996515", "#FFD159"),  # Amber Gold
            SlotType.LORE: ("#5C3566", "#E284F7"),  # Plum Lore
            SlotType.TICKER: ("#5A461E", "#E6C687"),  # Bronze
            SlotType.BANNER: ("#28283C", "#A8A8D0"),  # Dark Slate
            SlotType.SLOGAN: ("#333333", "#A0A0A0"),  # Slate Gray
            SlotType.DIVIDER: ("#4F4F4F", "#CCCCCC"),  # Divider Gray
            SlotType.FOOTER: ("#282828", "#B0B0B0"),  # Charcoal
        }
        return palette.get(self, ("#333333", "#999999"))

    @property
    def mask_fill(self) -> Tuple[int, int, int, int]:
        """Returns (R, G, B, A) fill color for PIL wireframe mask generation."""
        fills = {
            SlotType.TITLE: (74, 35, 90, 160),  # Royal Purple
            SlotType.BANNER: (40, 40, 60, 140),  # Dark Slate
            SlotType.EAR_BOX: (100, 40, 40, 140),  # Dark Maroon
            SlotType.SLOGAN: (50, 50, 50, 120),  # Charcoal
            SlotType.TICKER: (90, 70, 30, 130),  # Bronze
            SlotType.HEADLINE: (139, 30, 30, 170),  # Crimson Red
            SlotType.SUBHEADLINE: (160, 60, 40, 130),  # Amber
            SlotType.PHOTO: (30, 86, 49, 180),  # Forest Green
            SlotType.BODY: (27, 54, 93, 140),  # Ink Navy
            SlotType.COLUMN: (27, 54, 93, 130),  # Column Blue
            SlotType.QUOTE: (153, 101, 21, 160),  # Amber Gold
            SlotType.LORE: (92, 53, 102, 140),  # Plum
            SlotType.DIVIDER: (80, 80, 80, 140),  # Divider
            SlotType.FOOTER: (40, 40, 40, 150),  # Footer
        }
        return fills.get(self, (50, 50, 50, 120))

    @property
    def mask_outline(self) -> Tuple[int, int, int]:
        """Returns (R, G, B) outline color for PIL wireframe mask generation."""
        outlines = {
            SlotType.TITLE: (120, 60, 150),
            SlotType.BANNER: (80, 80, 120),
            SlotType.EAR_BOX: (160, 60, 60),
            SlotType.SLOGAN: (100, 100, 100),
            SlotType.TICKER: (140, 110, 50),
            SlotType.HEADLINE: (190, 40, 40),
            SlotType.SUBHEADLINE: (210, 90, 60),
            SlotType.PHOTO: (40, 140, 80),
            SlotType.BODY: (45, 90, 155),
            SlotType.COLUMN: (45, 90, 155),
            SlotType.QUOTE: (210, 145, 30),
            SlotType.LORE: (140, 80, 160),
            SlotType.DIVIDER: (120, 120, 120),
            SlotType.FOOTER: (90, 90, 90),
        }
        return outlines.get(self, (100, 100, 100))


class LayoutStatus(str, Enum):
    """Represents the origin and modification status of a newspaper layout."""

    BUNDLED = "Bundled"
    MODIFIED = "Modified"
    CUSTOM = "Custom"

    @classmethod
    def determine(cls, is_bundled: bool, is_modified: bool) -> LayoutStatus:
        """Calculates layout status from bundled flag and modified diff."""
        if is_modified:
            return cls.MODIFIED
        if is_bundled:
            return cls.BUNDLED
        return cls.CUSTOM

    @property
    def badge_text(self) -> str:
        if self == LayoutStatus.MODIFIED:
            return "Modified (Issue Custom)"
        if self == LayoutStatus.BUNDLED:
            return "Bundled Template (Protected)"
        return "Custom Template"

    @property
    def badge_color(self) -> str:
        if self == LayoutStatus.MODIFIED:
            return "#FFB347"  # Amber Orange
        if self == LayoutStatus.BUNDLED:
            return "#66BB6A"  # Soft Green
        return "#64B5F6"  # Soft Sky Blue


@dataclass
class LayoutSlot:
    """Strongly-typed object-oriented representation of a newspaper layout slot."""

    id: str
    rect: List[int]  # [x, y, w, h]
    type: SlotType = SlotType.BODY
    label: str = ""
    default_val: str = ""

    @property
    def x(self) -> int:
        return self.rect[0] if len(self.rect) > 0 else 0

    @property
    def y(self) -> int:
        return self.rect[1] if len(self.rect) > 1 else 0

    @property
    def width(self) -> int:
        return self.rect[2] if len(self.rect) > 2 else 0

    @property
    def height(self) -> int:
        return self.rect[3] if len(self.rect) > 3 else 0

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    def is_modified(self, other: LayoutSlot) -> bool:
        """Compares geometry, type, and label against another slot definition."""
        if not isinstance(other, LayoutSlot):
            return True
        return (
            self.id != other.id
            or list(self.rect) != list(other.rect)
            or self.type != other.type
            or self.label != other.label
        )

    def to_dict(self) -> Dict[str, object]:
        """Serializes the slot to dictionary format."""
        return {
            "id": self.id,
            "rect": list(self.rect),
            "type": self.type.value if isinstance(self.type, SlotType) else str(self.type),
            "label": self.label,
            "default_val": self.default_val,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> LayoutSlot:
        """Deserializes slot from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            rect=list(data.get("rect", [0, 0, 100, 100])),
            type=SlotType.from_string(data.get("type", "body")),
            label=str(data.get("label", "")),
            default_val=str(data.get("default_val", "")),
        )


@dataclass
class LayoutDefinition:
    """Strongly-typed object-oriented representation of a complete newspaper layout."""

    id: str
    name: str = ""
    description: str = ""
    slots: List[LayoutSlot] = field(default_factory=list)
    bundled: bool = False
    format_version: str = "1.0"
    page_file: str = ""
    wireframe_file: str = ""

    def get_slot(self, slot_id: str) -> Optional[LayoutSlot]:
        for s in self.slots:
            if s.id == slot_id:
                return s
        return None

    def find_slots_by_type(self, slot_type: SlotType) -> List[LayoutSlot]:
        target = SlotType.from_string(slot_type)
        return [s for s in self.slots if s.type == target]

    def is_modified_from(self, other: Optional[LayoutDefinition]) -> bool:
        """Determines if this layout differs in slot count, bounds, types, or labels."""
        if not other:
            return False

        if len(self.slots) != len(other.slots):
            return True

        other_map = {s.id: s for s in other.slots}
        for s in self.slots:
            if s.id not in other_map:
                return True
            if s.is_modified(other_map[s.id]):
                return True

        return False

    def to_dict(self) -> Dict[str, object]:
        """Serializes layout definition to dictionary."""
        d: Dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "slots": [s.to_dict() for s in self.slots],
            "bundled": self.bundled,
            "format_version": self.format_version,
        }
        if self.page_file:
            d["page_file"] = self.page_file
        if self.wireframe_file:
            d["wireframe_file"] = self.wireframe_file
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> LayoutDefinition:
        """Deserializes layout definition from dictionary."""
        raw_slots = data.get("slots", [])
        slots = [s if isinstance(s, LayoutSlot) else LayoutSlot.from_dict(s) for s in raw_slots]
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            slots=slots,
            bundled=bool(data.get("bundled", False)),
            format_version=str(data.get("format_version", "1.0")),
            page_file=str(data.get("page_file", "")),
            wireframe_file=str(data.get("wireframe_file", "")),
        )
