import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from daily_prophet.versioning import (
    FormatVersion,
    SchemaMigrationPipeline,
    CompatibilityManager,
    CompatibilityModeStrategy,
    CompatibilityIssue,
    CURRENT_PROJECT_VERSION,
    CURRENT_TEMPLATE_VERSION,
)
from daily_prophet.template_package import load_all_installed_templates, delete_installed_template


class TestOOPArchitectureAndV10(unittest.TestCase):
    def test_canonical_v10_constants(self):
        self.assertEqual(CURRENT_PROJECT_VERSION, FormatVersion(1, 0))
        self.assertEqual(CURRENT_TEMPLATE_VERSION, FormatVersion(1, 0))
        self.assertEqual(str(CURRENT_PROJECT_VERSION), "1.0")

    def test_format_version_comparisons(self):
        v10 = FormatVersion.parse("1.0")
        v11 = FormatVersion.parse("1.1")
        v20 = FormatVersion.parse("2.0")
        v201 = FormatVersion.parse("2.0.1")

        self.assertTrue(v10 < v11 < v20 < v201)
        self.assertEqual(FormatVersion.parse("v1.0"), v10)
        self.assertEqual(FormatVersion.parse(None), v10)

    def test_extensible_migration_pipeline_chain(self):
        """Verify Chain of Responsibility forward migration pipeline works when steps are registered."""
        pipeline = SchemaMigrationPipeline[dict](FormatVersion(2, 0))

        @pipeline.register_step(FormatVersion(1, 0), FormatVersion(1, 1), "Add slot styling")
        def step_10_to_11(data):
            data["styling"] = {"font": "Cinzel"}
            return data

        @pipeline.register_step(FormatVersion(1, 1), FormatVersion(2, 0), "Add multi-page layout index")
        def step_11_to_20(data):
            data["pages"] = [data.get("stories", [])]
            return data

        initial_data = {"stories": [{"headline": "Test"}]}
        migrated, upgraded, orig_ver = pipeline.migrate(initial_data, FormatVersion(1, 0))

        self.assertTrue(upgraded)
        self.assertEqual(orig_ver, FormatVersion(1, 0))
        self.assertEqual(migrated["styling"]["font"], "Cinzel")
        self.assertIn("pages", migrated)

    def test_compatibility_mode_strategy(self):
        """Verify Strategy pattern for compatibility analysis and lossy downgrade."""
        manager = CompatibilityManager[dict]()

        def v10_analyzer(data):
            issues = []
            if "animated_gif_url" in data:
                issues.append(
                    CompatibilityIssue(
                        feature_name="Animated Photos",
                        description="Animated GIFs will be flattened to static images in v1.0.",
                        severity="lossy",
                    )
                )
            return issues

        def v10_transformer(data):
            if "animated_gif_url" in data:
                del data["animated_gif_url"]
            return data

        strategy = CompatibilityModeStrategy(FormatVersion(1, 0), v10_analyzer, v10_transformer)
        manager.register_strategy(strategy)

        sample_v2 = {"headline": "Hogwarts Express", "animated_gif_url": "train.gif"}
        issues = manager.analyze_compatibility(sample_v2, FormatVersion(1, 0))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].feature_name, "Animated Photos")

        exported = manager.export_compatible(sample_v2, FormatVersion(1, 0))
        self.assertNotIn("animated_gif_url", exported)
        self.assertEqual(exported["headline"], "Hogwarts Express")

    def test_bundled_templates_flag_and_protection(self):
        """Verify pre-included templates have bundled=True and cannot be deleted."""
        templates = load_all_installed_templates()
        for i in range(1, 10):
            tid = f"layout_{i}"
            self.assertIn(tid, templates)
            self.assertTrue(templates[tid].get("bundled", False), f"{tid} must be flagged bundled=True")

            # Verify deletion is blocked
            deleted = delete_installed_template(tid)
            self.assertFalse(deleted, f"{tid} should not be deletable")


if __name__ == "__main__":
    unittest.main()
