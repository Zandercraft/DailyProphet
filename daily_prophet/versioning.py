"""Version specification and extensible schema migration framework.

Follows the Chain of Responsibility, Strategy, and Semantic Versioning patterns
to establish a clean, future-proof foundation for file format evolution.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Callable, TypeVar, Generic, Tuple, Union

T = TypeVar("T", bound=Dict[str, object])


@dataclass(frozen=True, order=True)
class FormatVersion:
    """Semantic format version representation supporting clean comparisons (v1.0 < v1.1 < v2.0)."""
    major: int
    minor: int
    patch: int = 0

    @classmethod
    def parse(cls, version_str: str | FormatVersion | object) -> FormatVersion:
        if isinstance(version_str, FormatVersion):
            return version_str
        if not version_str:
            return cls(1, 0, 0)
        parts = str(version_str).strip().lstrip("v").split(".")
        try:
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return cls(major, minor, patch)
        except (ValueError, IndexError):
            return cls(1, 0, 0)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}" if self.patch == 0 else f"{self.major}.{self.minor}.{self.patch}"


# Canonical base versions for the initial v1.0 specifications
PROJECT_FORMAT_V1 = FormatVersion(1, 0)
TEMPLATE_FORMAT_V1 = FormatVersion(1, 0)

CURRENT_PROJECT_VERSION = PROJECT_FORMAT_V1
CURRENT_TEMPLATE_VERSION = TEMPLATE_FORMAT_V1


class CompatibilitySeverity(str, Enum):
    """Severity classification for features downgraded across format versions."""
    WARNING = "warning"
    LOSSY = "lossy"
    BREAKING = "breaking"

    @classmethod
    def choices(cls) -> List[str]:
        return [m.value for m in cls]


@dataclass
class CompatibilityIssue:
    """Represents a feature or field that cannot be natively preserved when downgrading."""
    feature_name: str
    description: str
    severity: CompatibilitySeverity = CompatibilitySeverity.WARNING


class SchemaMigrationStep(Generic[T]):
    """An atomic migration step between two specific sequential format versions."""

    def __init__(
        self,
        from_version: FormatVersion,
        to_version: FormatVersion,
        transform_func: Callable[[T], T],
        description: str = ""
    ):
        self.from_version = from_version
        self.to_version = to_version
        self.transform_func = transform_func
        self.description = description

    def apply(self, data: T) -> T:
        return self.transform_func(copy.deepcopy(data))


class SchemaMigrationPipeline(Generic[T]):
    """Chain of Responsibility pipeline for forward-upgrading schema versions in memory.

    Lays the groundwork for future format upgrades (e.g. v1.0 -> v1.1 -> v2.0)
    without running unnecessary transforms when the file is already at the current version.
    """

    def __init__(self, current_version: FormatVersion):
        self.current_version = current_version
        self._steps: List[SchemaMigrationStep[T]] = []

    def register_step(
        self,
        from_version: FormatVersion,
        to_version: FormatVersion,
        description: str = ""
    ) -> Callable[[Callable[[T], T]], Callable[[T], T]]:
        """Decorator to register a new forward migration step."""
        def decorator(func: Callable[[T], T]) -> Callable[[T], T]:
            step = SchemaMigrationStep(from_version, to_version, func, description)
            self._steps.append(step)
            # Maintain steps sorted by source version
            self._steps.sort(key=lambda s: s.from_version)
            return func
        return decorator

    def can_migrate(self, source_version: FormatVersion) -> bool:
        if source_version == self.current_version:
            return True
        if source_version > self.current_version:
            return False
        # Verify a continuous migration path exists
        curr = source_version
        for step in self._steps:
            if step.from_version == curr:
                curr = step.to_version
                if curr >= self.current_version:
                    return True
        return False

    def migrate(self, data: T, source_version: FormatVersion) -> Tuple[T, bool, FormatVersion]:
        """Upgrades data in memory from source_version to current_version.

        Returns:
            Tuple of (migrated_data, was_upgraded, source_version)
        """
        if source_version == self.current_version or not self._steps:
            return data, False, source_version

        migrated_data = copy.deepcopy(data)
        curr = source_version
        upgraded = False

        for step in self._steps:
            if step.from_version == curr and curr < self.current_version:
                migrated_data = step.apply(migrated_data)
                curr = step.to_version
                upgraded = True

        return migrated_data, upgraded, source_version


class CompatibilityModeStrategy(Generic[T]):
    """Strategy defining compatibility analysis and destructive downgrade for a target legacy version."""

    def __init__(
        self,
        target_version: FormatVersion,
        analyzer: Callable[[T], List[CompatibilityIssue]],
        transformer: Callable[[T], T]
    ):
        self.target_version = target_version
        self.analyzer = analyzer
        self.transformer = transformer

    def analyze(self, data: T) -> List[CompatibilityIssue]:
        return self.analyzer(data)

    def export(self, data: T) -> T:
        return self.transformer(copy.deepcopy(data))


class CompatibilityManager(Generic[T]):
    """Manages Microsoft Word-style compatibility export strategies."""

    def __init__(self):
        self._strategies: Dict[FormatVersion, CompatibilityModeStrategy[T]] = {}

    def register_strategy(self, strategy: CompatibilityModeStrategy[T]):
        self._strategies[strategy.target_version] = strategy

    def get_supported_target_versions(self) -> List[FormatVersion]:
        return sorted(self._strategies.keys())

    def analyze_compatibility(self, data: T, target_version: FormatVersion) -> List[CompatibilityIssue]:
        strategy = self._strategies.get(target_version)
        if not strategy:
            return []
        return strategy.analyze(data)

    def export_compatible(self, data: T, target_version: FormatVersion) -> T:
        strategy = self._strategies.get(target_version)
        if not strategy:
            return copy.deepcopy(data)
        return strategy.export(data)


# ---------------------------------------------------------------------------
# Initialized Pipelines for Current v1.0 Formats
# ---------------------------------------------------------------------------

# Project Pipeline (v1.0 is current; future versions register steps here)
project_migration_pipeline: SchemaMigrationPipeline[Dict[str, object]] = SchemaMigrationPipeline(CURRENT_PROJECT_VERSION)
project_compatibility_manager: CompatibilityManager[Dict[str, object]] = CompatibilityManager()
ProjectMigrator = project_migration_pipeline

# Template Pipeline (v1.0 is current; future versions register steps here)
template_migration_pipeline: SchemaMigrationPipeline[Dict[str, object]] = SchemaMigrationPipeline(CURRENT_TEMPLATE_VERSION)
template_compatibility_manager: CompatibilityManager[Dict[str, object]] = CompatibilityManager()
TemplateMigrator = template_migration_pipeline
