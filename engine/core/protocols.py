"""Protocol contracts for pluggable engine components."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from .models import (
    AnalysisResult,
    DependencySchema,
    FunctionSchema,
    GeneratedTestPlan,
    ProjectMetadata,
)


@runtime_checkable
class IAnalyzer(Protocol):
    """Transforms Python source code into semantic models."""

    def analyze(self, project_root: Path, file_path: Path, /) -> AnalysisResult:
        """Analyze a single file in the context of a project root."""

    def analyze_file(self, file_path: Path, /) -> tuple[FunctionSchema, ...]:
        """Analyze a single Python file."""

    def analyze_project(self, root_path: Path, /) -> AnalysisResult:
        """Analyze every supported Python file inside a project root."""


@runtime_checkable
class IGenerator(Protocol):
    """Renders test artifacts from analyzed function schemas."""

    def generate(self, metadata: AnalysisResult, output_path: Path, /) -> Path:
        """Render a pytest suite from analysis metadata and write it to disk."""

    def build_suite_plan(self, metadata: AnalysisResult, /) -> tuple[GeneratedTestPlan, ...]:
        """Describe the generated tests before they are rendered."""

    def render_module(self, function: FunctionSchema, project: ProjectMetadata, /) -> str:
        """Render a pytest module for a single function."""

    def render_suite(
        self,
        functions: Sequence[FunctionSchema],
        project: ProjectMetadata,
        /,
    ) -> Mapping[Path, str]:
        """Render a full test suite keyed by target path."""


@runtime_checkable
class IInfraManager(Protocol):
    """Resolves semantic dependencies into executable infrastructure plans."""

    def detect_required_infra(self, analysis: AnalysisResult, /) -> list[str]:
        """Inspect an analysis result and determine required infrastructure services."""

    def enrich_analysis(self, analysis: AnalysisResult, /) -> AnalysisResult:
        """Return a copy of analysis metadata with detected infrastructure attached."""

    def resolve_dependency(self, dependency: DependencySchema, /) -> DependencySchema:
        """Attach infra-specific details to a discovered dependency."""

    def plan_environment(self, required_infra: Sequence[str], /) -> Mapping[str, str]:
        """Produce a deterministic environment plan for the detected services."""

    def create_compose_file(self, project_root: Path, required_infra: Sequence[str], /) -> Path | None:
        """Create a docker-compose.yaml file for the requested services."""
