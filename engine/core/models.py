"""Core domain models for speculast."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EngineModel(BaseModel):
    """Shared strict base model for all engine schemas."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )


class ArgumentKind(StrEnum):
    """Supported Python parameter kinds."""

    POSITIONAL_ONLY = "positional_only"
    POSITIONAL_OR_KEYWORD = "positional_or_keyword"
    VAR_POSITIONAL = "var_positional"
    KEYWORD_ONLY = "keyword_only"
    VAR_KEYWORD = "var_keyword"


class DependencyKind(StrEnum):
    """Infrastructure categories recognized by the engine."""

    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    MESSAGE_BROKER = "message_broker"
    FILESYSTEM = "filesystem"
    UNKNOWN = "unknown"


class GeneratedTestMode(StrEnum):
    """Execution strategies used by the generated pytest suite."""

    BEHAVIORAL = "behavioral"
    INTEGRATION = "integration"
    SKIPPED = "skipped"


class TestOutcome(StrEnum):
    """Normalized pytest outcomes used in reports."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ArgumentSchema(EngineModel):
    """Normalized metadata about a function argument."""

    name: str = Field(min_length=1)
    kind: ArgumentKind
    annotation: str | None = None
    default_value: str | None = None
    required: bool = True


class DependencySchema(EngineModel):
    """Description of an external dependency used by analyzed code."""

    name: str = Field(min_length=1)
    kind: DependencyKind = DependencyKind.UNKNOWN
    import_path: str | None = None
    symbol: str | None = None
    container_image: str | None = None
    container_port: int | None = Field(default=None, ge=1, le=65535)
    endpoint: str | None = None
    is_optional: bool = False
    evidence: tuple[str, ...] = ()
    metadata: dict[str, str] = Field(default_factory=dict)


class FunctionSchema(EngineModel):
    """Semantic representation of a Python function or method."""

    name: str = Field(min_length=1)
    qualname: str = Field(min_length=1)
    module: str = Field(min_length=1)
    file_path: Path
    lineno: int = Field(ge=1)
    end_lineno: int = Field(ge=1)
    arguments: tuple[ArgumentSchema, ...] = ()
    return_annotation: str | None = None
    decorators: tuple[str, ...] = ()
    docstring: str | None = None
    is_async: bool = False
    is_method: bool = False
    class_name: str | None = None
    node_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    external_calls: list[str] = Field(default_factory=list)
    dependencies: tuple[DependencySchema, ...] = ()

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("file_path must be absolute to keep cache keys deterministic")
        return value


class ProjectMetadata(EngineModel):
    """Top-level metadata returned after project analysis."""

    project_name: str = Field(min_length=1)
    root_path: Path
    python_version: str = Field(min_length=1)
    imports: list[str] = Field(default_factory=list)
    source_roots: tuple[Path, ...] = ()
    analyzed_files: tuple[Path, ...] = ()
    discovered_dependencies: tuple[DependencySchema, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("root_path")
    @classmethod
    def validate_root_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("root_path must be absolute")
        return value

    @field_validator("source_roots", "analyzed_files")
    @classmethod
    def validate_paths(cls, values: tuple[Path, ...]) -> tuple[Path, ...]:
        for value in values:
            if not value.is_absolute():
                raise ValueError("all project paths must be absolute")
        return values


class GeneratorConfig(EngineModel):
    """Runtime options that influence test generation."""

    use_real_db: bool = False
    behavioral_mode: bool = True


class FunctionContextSchema(EngineModel):
    """Localized business context for a discovered function."""

    localized_name: str = Field(min_length=1)
    description_ru: str = Field(min_length=1)
    module_label_ru: str | None = None


class GeneratedTestPlan(EngineModel):
    """Describes how a generated test is expected to execute."""

    test_name: str = Field(min_length=1)
    module: str = Field(min_length=1)
    qualname: str = Field(min_length=1)
    mode: GeneratedTestMode = GeneratedTestMode.BEHAVIORAL
    uses_real_db: bool = False
    mock_targets: tuple[str, ...] = ()
    skip_reason: str | None = None
    expected_return_type: str | None = None


class CoverageEntry(EngineModel):
    """Coverage summary for a single measured file."""

    path: str = Field(min_length=1)
    covered_lines: int = Field(ge=0)
    missing_lines: int = Field(ge=0)
    num_statements: int = Field(ge=0)
    percent_covered: float = Field(ge=0.0, le=100.0)


class TestCaseResult(EngineModel):
    """Structured test-case result captured from pytest output."""

    nodeid: str = Field(min_length=1)
    outcome: TestOutcome
    duration: float = Field(default=0.0, ge=0.0)
    message: str | None = None
    longrepr: str | None = None
    mocked_calls: tuple[str, ...] = ()


class TestExecutionResult(EngineModel):
    """Aggregate result of the generated pytest session."""

    exit_code: int = Field(ge=0)
    total: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    duration: float = Field(default=0.0, ge=0.0)
    coverage_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    stdout: str = ""
    stderr: str = ""
    tests: tuple[TestCaseResult, ...] = ()
    coverage: tuple[CoverageEntry, ...] = ()
    report_path: Path | None = None
    coverage_path: Path | None = None

    @field_validator("report_path", "coverage_path")
    @classmethod
    def validate_optional_path(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        if not value.is_absolute():
            raise ValueError("artifact paths must be absolute")
        return value


class AnalysisResult(EngineModel):
    """Aggregate produced by the analyzer layer."""

    project: ProjectMetadata
    functions: tuple[FunctionSchema, ...] = ()
    required_infra: list[str] = Field(default_factory=list)
    function_context: dict[str, FunctionContextSchema] = Field(default_factory=dict)
