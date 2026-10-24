import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath("."))

from daily_prophet.models import StoryPriority, BoxStyle, ImageAlign, PaperTheme, BorderStyle, Story, NewspaperEdition
from daily_prophet.layout_models import SlotType, LayoutStatus, LayoutSlot, LayoutDefinition
from daily_prophet.versioning import CompatibilitySeverity
from daily_prophet.template_package import is_layout_modified


class TestEnumsAndOOPRefactoring(unittest.TestCase):
    def test_enums_completeness_and_choices(self):
        """Verify all enums offer clean string choices and safe parsing without raw strings."""
        self.assertIn("Cover Story (Hero)", StoryPriority.choices())
        self.assertEqual(StoryPriority.from_string("Cover Story (Hero)"), StoryPriority.COVER)

        self.assertIn("ornate_box", BoxStyle.choices())
        self.assertEqual(BoxStyle.from_string("ornate_box"), BoxStyle.ORNATE_BOX)
        self.assertEqual(BoxStyle.from_string("non_existent"), BoxStyle.STANDARD)

        self.assertIn("left", ImageAlign.choices())
        self.assertEqual(ImageAlign.from_string("left"), ImageAlign.LEFT)

        self.assertIn("parchment", PaperTheme.choices())
        self.assertEqual(PaperTheme.from_string("parchment"), PaperTheme.PARCHMENT)

        self.assertIn("weathered_border", BorderStyle.choices())
        self.assertEqual(BorderStyle.from_string("weathered_border"), BorderStyle.WEATHERED_BORDER)

        self.assertIn("headline", SlotType.choices())
        self.assertEqual(SlotType.from_string("headline"), SlotType.HEADLINE)
        self.assertEqual(SlotType.from_string("unknown_slot"), SlotType.BODY)

        self.assertIn("warning", CompatibilitySeverity.choices())

    def test_layout_slot_oop_geometry_and_serialization(self):
        """Verify LayoutSlot geometry properties and JSON roundtrip."""
        slot = LayoutSlot(
            id="slot_cover",
            rect=[50, 100, 400, 250],
            type=SlotType.HEADLINE,
            label="Breaking Banner",
            default_val="DEFAULT",
        )
        self.assertEqual(slot.x, 50)
        self.assertEqual(slot.y, 100)
        self.assertEqual(slot.width, 400)
        self.assertEqual(slot.height, 250)
        self.assertEqual(slot.right, 450)
        self.assertEqual(slot.bottom, 350)
        self.assertEqual(slot.area, 100000)

        # JSON Serialization
        slot_dict = slot.to_dict()
        self.assertEqual(slot_dict["type"], "headline")
        json_str = json.dumps(slot_dict)
        deserialized = LayoutSlot.from_dict(json.loads(json_str))
        self.assertEqual(deserialized.id, slot.id)
        self.assertEqual(deserialized.type, SlotType.HEADLINE)
        self.assertEqual(deserialized.rect, [50, 100, 400, 250])

    def test_layout_definition_oop_diff_and_status(self):
        """Verify LayoutDefinition cleanly computes differences and determines LayoutStatus."""
        slot1 = LayoutSlot("s1", [0, 0, 100, 50], SlotType.TITLE, "Title")
        slot2 = LayoutSlot("s2", [0, 60, 100, 150], SlotType.BODY, "Body")

        layout_a = LayoutDefinition("layout_1", "Test Layout", slots=[slot1, slot2], bundled=True)
        layout_b = LayoutDefinition("layout_1", "Test Layout", slots=[slot1, slot2], bundled=True)

        self.assertFalse(layout_a.is_modified_from(layout_b))
        status = LayoutStatus.determine(is_bundled=True, is_modified=layout_a.is_modified_from(layout_b))
        self.assertEqual(status, LayoutStatus.BUNDLED)
        self.assertIn("Bundled", status.badge_text)

        # Modify layout_b slot geometry
        slot2_mod = LayoutSlot("s2", [0, 70, 100, 150], SlotType.BODY, "Body")
        layout_b.slots = [slot1, slot2_mod]

        self.assertTrue(layout_a.is_modified_from(layout_b))
        status_mod = LayoutStatus.determine(is_bundled=True, is_modified=layout_a.is_modified_from(layout_b))
        self.assertEqual(status_mod, LayoutStatus.MODIFIED)
        self.assertIn("Modified", status_mod.badge_text)

        # Verify through is_layout_modified wrapper
        self.assertTrue(is_layout_modified(layout_a.to_dict(), layout_b.to_dict()))

    def test_story_and_edition_enum_integration(self):
        """Verify Story and NewspaperEdition use enums cleanly with seamless serialization."""
        story = Story(
            headline="Dumbledore Returns",
            priority=StoryPriority.COVER,
            box_style=BoxStyle.ORNATE_BOX,
            inline_image_align=ImageAlign.LEFT,
        )
        self.assertEqual(story.priority, StoryPriority.COVER)
        self.assertEqual(story.box_style, BoxStyle.ORNATE_BOX)
        self.assertEqual(story.inline_image_align, ImageAlign.LEFT)

        # Serialization to dict produces expected strings
        s_dict = story.to_dict()
        self.assertEqual(s_dict["box_style"], "ornate_box")
        self.assertEqual(s_dict["inline_image_align"], "left")

        # Deserialization from dict restores typed Enums
        reconstructed_story = Story.from_dict(s_dict)
        self.assertEqual(reconstructed_story.box_style, BoxStyle.ORNATE_BOX)
        self.assertEqual(reconstructed_story.inline_image_align, ImageAlign.LEFT)

        edition = NewspaperEdition(
            paper_title="The Daily Prophet",
            theme=PaperTheme.PARCHMENT,
            border_style=BorderStyle.CLEAN_RULED,
            stories=[story],
        )
        e_dict = edition.to_dict()
        self.assertEqual(e_dict["theme"], "parchment")
        self.assertEqual(e_dict["border_style"], "clean_ruled")

        reconstructed_edition = NewspaperEdition.from_dict(e_dict)
        self.assertEqual(reconstructed_edition.theme, PaperTheme.PARCHMENT)
        self.assertEqual(reconstructed_edition.border_style, BorderStyle.CLEAN_RULED)
        self.assertEqual(reconstructed_edition.stories[0].box_style, BoxStyle.ORNATE_BOX)


if __name__ == "__main__":
    unittest.main()
