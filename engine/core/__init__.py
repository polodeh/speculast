"""Core exports for speculast."""

from .i18n import LanguageCode, get_catalog, normalize_language, resolve_language, tr
from .models import (
    AnalysisResult,
    ArgumentKind,
    ArgumentSchema,
    CoverageEntry,
    DependencyKind,
    DependencySchema,
    FunctionContextSchema,
    FunctionSchema,
    GeneratedTestMode,
    GeneratedTestPlan,
    GeneratorConfig,
    ProjectMetadata,
    TestCaseResult,
    TestExecutionResult,
    TestOutcome,
)
from .protocols import IAnalyzer, IGenerator, IInfraManager

__all__ = [
    "AnalysisResult",
    "ArgumentKind",
    "ArgumentSchema",
    "CoverageEntry",
    "DependencyKind",
    "DependencySchema",
    "FunctionContextSchema",
    "FunctionSchema",
    "GeneratedTestMode",
    "GeneratedTestPlan",
    "GeneratorConfig",
    "IAnalyzer",
    "IGenerator",
    "IInfraManager",
    "LanguageCode",
    "ProjectMetadata",
    "TestCaseResult",
    "TestExecutionResult",
    "TestOutcome",
    "get_catalog",
    "normalize_language",
    "resolve_language",
    "tr",
]
