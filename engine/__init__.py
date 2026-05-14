"""Public package surface for speculast."""

from .analyzer.engine import AnalyzerEngine
from .analyzer.visitors import BaseVisitor, CallsVisitor, DefinitionsVisitor, ImportsVisitor
from .core.i18n import LanguageCode, get_catalog, normalize_language, resolve_language, tr
from .core.models import (
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
from .core.protocols import IAnalyzer, IGenerator, IInfraManager
from .generator.engine import GeneratorEngine
from .infra.manager import InfraManager
from .infra.registry import DependencyRegistry
from .visualizer.dashboard import DashboardBuilder
from .visualizer.renderer import VisualReportRenderer

__all__ = [
    "AnalysisResult",
    "AnalyzerEngine",
    "ArgumentKind",
    "ArgumentSchema",
    "BaseVisitor",
    "CallsVisitor",
    "CoverageEntry",
    "DashboardBuilder",
    "DefinitionsVisitor",
    "DependencyRegistry",
    "DependencyKind",
    "DependencySchema",
    "FunctionContextSchema",
    "FunctionSchema",
    "GeneratedTestMode",
    "GeneratedTestPlan",
    "GeneratorEngine",
    "GeneratorConfig",
    "IAnalyzer",
    "IGenerator",
    "IInfraManager",
    "InfraManager",
    "ImportsVisitor",
    "LanguageCode",
    "ProjectMetadata",
    "TestCaseResult",
    "TestExecutionResult",
    "TestOutcome",
    "VisualReportRenderer",
    "get_catalog",
    "normalize_language",
    "resolve_language",
    "tr",
]
