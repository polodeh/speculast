"""Production-oriented test generator for arbitrary Python projects."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import Any

from jinja2 import DictLoader, Environment, FileSystemLoader, StrictUndefined

from ..core.models import (
    AnalysisResult,
    ArgumentSchema,
    DependencyKind,
    FunctionSchema,
    GeneratedTestMode,
    GeneratedTestPlan,
    GeneratorConfig,
    ProjectMetadata,
)
from ..core.protocols import IGenerator
from ..parser import build_module_members


class GeneratorEngine(IGenerator):
    """Generate generic pytest suites from analyzed project functions."""

    TEMPLATE_SUITE = "pytest_template.jinja2"
    TEMPLATE_CONFTEST = "tests_conftest_template.jinja2"
    TEMPLATE_PYPROJECT = "tests_pyproject_template.jinja2"
    TEMPLATE_NAMES = (
        TEMPLATE_SUITE,
        TEMPLATE_CONFTEST,
        TEMPLATE_PYPROJECT,
    )
    DATABASE_CALL_ROOTS = frozenset({"sqlalchemy", "asyncpg", "psycopg", "psycopg2"})
    DATABASE_MODULE_HINTS = frozenset({"database", "db", "models", "repositories"})
    HTTP_MOCK_TARGETS = frozenset({"requests.get", "requests.post"})

    def __init__(
        self,
        *,
        templates_path: Path | None = None,
        config: GeneratorConfig | None = None,
    ) -> None:
        self.templates_path = templates_path.resolve() if templates_path is not None else None
        self.config = config or GeneratorConfig()
        self.environment = Environment(
            loader=self._build_loader(templates_path),
            keep_trailing_newline=True,
            lstrip_blocks=True,
            trim_blocks=True,
            undefined=StrictUndefined,
            autoescape=False,
        )
        self.last_suite_plan: tuple[GeneratedTestPlan, ...] = ()

    def generate(self, metadata: AnalysisResult, output_path: Path, /) -> Path:
        """Generate a structured pytest suite under tests/."""

        tests_root = self._resolve_tests_root(output_path)
        tests_root.mkdir(parents=True, exist_ok=True)
        suite_output = self._resolve_suite_output(output_path)
        suite_output.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup_legacy_generated_suite(tests_root, suite_output)

        suite_plan = self._build_suite_plan(metadata.functions)
        context = self._build_context(metadata.project, metadata.functions, suite_plan)

        self._write_template(self.TEMPLATE_SUITE, suite_output, context)
        self._write_template(self.TEMPLATE_CONFTEST, tests_root / "conftest.py", context)
        self._write_template(self.TEMPLATE_PYPROJECT, tests_root / "pyproject.toml", context)
        self._ensure_package_marker(tests_root / "__init__.py")

        self.last_suite_plan = suite_plan
        return suite_output

    def build_suite_plan(self, metadata: AnalysisResult, /) -> tuple[GeneratedTestPlan, ...]:
        """Describe the tests that will be generated for the analyzed project."""

        return self._build_suite_plan(metadata.functions)

    def render_module(self, function: FunctionSchema, project: ProjectMetadata, /) -> str:
        """Render a single-function-oriented view for protocol compatibility."""

        suite_plan = self._build_suite_plan((function,))
        context = self._build_context(project, (function,), suite_plan)
        return self.environment.get_template(self.TEMPLATE_SUITE).render(**context)

    def render_suite(
        self,
        functions: Sequence[FunctionSchema],
        project: ProjectMetadata,
        /,
    ) -> Mapping[Path, str]:
        """Render the suite into an in-memory file mapping."""

        suite_plan = self._build_suite_plan(functions)
        context = self._build_context(project, functions, suite_plan)
        return OrderedDict(
            {
                Path("tests/conftest.py"): self.environment.get_template(self.TEMPLATE_CONFTEST).render(**context),
                Path("tests/pyproject.toml"): self.environment.get_template(self.TEMPLATE_PYPROJECT).render(**context),
                Path("tests/test_generated.py"): self.environment.get_template(self.TEMPLATE_SUITE).render(**context),
            }
        )

    def _build_context(
        self,
        project: ProjectMetadata,
        functions: Sequence[FunctionSchema],
        suite_plan: Sequence[GeneratedTestPlan],
    ) -> dict[str, Any]:
        module_members = build_module_members(functions)
        plan_lookup = {
            (plan.module, plan.qualname): plan
            for plan in suite_plan
        }
        serialized_functions = [
            self._serialize_function(function, plan_lookup[(function.module, function.qualname)])
            for function in functions
            if (function.module, function.qualname) in plan_lookup
        ]
        has_db_bound_functions = any(
            bool(item["is_db_bound"])
            for item in serialized_functions
        )
        return {
            "project": project,
            "project_root_path": project.root_path.as_posix(),
            "project_source_roots": [path.as_posix() for path in project.source_roots],
            "use_real_db": self.config.use_real_db,
            "modules": module_members,
            "module_imports": self._build_module_imports(module_members),
            "functions": serialized_functions,
            "has_db_bound_functions": has_db_bound_functions,
            "has_mock_targets": any(bool(item["mock_targets"]) for item in serialized_functions),
            "database_modules": self._database_modules(module_members, functions),
        }

    def _build_suite_plan(
        self,
        functions: Sequence[FunctionSchema],
    ) -> tuple[GeneratedTestPlan, ...]:
        ordered_functions = sorted(
            functions,
            key=lambda function: (
                function.file_path.as_posix(),
                function.lineno,
                function.qualname,
            ),
        )
        plans: list[GeneratedTestPlan] = []

        for function in ordered_functions:
            is_db_bound = self._is_db_bound(function)
            mock_targets = self._derive_mock_targets(function)
            plans.append(
                GeneratedTestPlan(
                    test_name=self._build_test_name(function),
                    module=function.module,
                    qualname=function.qualname,
                    mode=GeneratedTestMode.INTEGRATION if is_db_bound else GeneratedTestMode.BEHAVIORAL,
                    uses_real_db=self.config.use_real_db and is_db_bound,
                    mock_targets=mock_targets,
                    expected_return_type=function.return_annotation,
                )
            )

        return tuple(plans)

    def _serialize_function(
        self,
        function: FunctionSchema,
        plan: GeneratedTestPlan,
    ) -> dict[str, Any]:
        return {
            "test_name": plan.test_name,
            "module": function.module,
            "name": function.name,
            "qualname": function.qualname,
            "class_name": function.class_name,
            "is_async": function.is_async,
            "is_db_bound": self._is_db_bound(function),
            "uses_real_db": plan.uses_real_db,
            "requires_async_test": function.is_async or plan.uses_real_db,
            "execution_mode": "skipped" if plan.skip_reason else plan.mode.value,
            "skip_reason": plan.skip_reason,
            "return_annotation": plan.expected_return_type,
            "mock_targets": list(plan.mock_targets),
            "external_calls": list(function.external_calls),
            "arguments": [
                self._serialize_argument(argument)
                for argument in function.arguments
            ],
        }

    @staticmethod
    def _serialize_argument(argument: ArgumentSchema) -> dict[str, Any]:
        return {
            "name": argument.name,
            "kind": argument.kind.value,
            "annotation": argument.annotation,
            "default_value": argument.default_value,
            "required": argument.required,
        }

    def _database_modules(
        self,
        module_members: Mapping[str, Sequence[str]],
        functions: Sequence[FunctionSchema],
    ) -> list[str]:
        candidate_modules: list[str] = []
        db_bound_modules = {
            function.module
            for function in functions
            if self._is_db_bound(function)
        }

        for module_name, members in module_members.items():
            tail = module_name.split(".")[-1]
            if module_name in db_bound_modules:
                candidate_modules.append(module_name)
                continue
            if tail in self.DATABASE_MODULE_HINTS:
                candidate_modules.append(module_name)
                continue
            if any(member in {"create_engine", "create_session_factory"} for member in members):
                candidate_modules.append(module_name)

        return list(dict.fromkeys(candidate_modules))

    @staticmethod
    def _build_module_imports(module_members: Mapping[str, Sequence[str]]) -> list[dict[str, Any]]:
        duplicate_counts: dict[str, int] = {}
        for members in module_members.values():
            for member in members:
                duplicate_counts[member] = duplicate_counts.get(member, 0) + 1

        rendered_imports: list[dict[str, Any]] = []
        for module_name, members in module_members.items():
            imports: list[dict[str, str | None]] = []
            module_alias_prefix = module_name.replace(".", "_")
            for member in members:
                alias = (
                    f"{module_alias_prefix}__{member}"
                    if duplicate_counts.get(member, 0) > 1
                    else None
                )
                rendered = f"{member} as {alias}" if alias is not None else member
                imports.append(
                    {
                        "name": member,
                        "alias": alias,
                        "rendered": rendered,
                    }
                )
            rendered_imports.append(
                {
                    "module": module_name,
                    "imports": imports,
                }
            )
        return rendered_imports

    def _is_db_bound(self, function: FunctionSchema) -> bool:
        if any(dependency.kind is DependencyKind.DATABASE for dependency in function.dependencies):
            return True

        module_tail = function.module.split(".")[-1]
        if module_tail in self.DATABASE_MODULE_HINTS:
            return True

        return any(
            self._root_token(call_name) in self.DATABASE_CALL_ROOTS
            or "session" in call_name.lower()
            for call_name in function.external_calls
        )

    def _derive_mock_targets(self, function: FunctionSchema) -> tuple[str, ...]:
        targets = [
            call_name
            for call_name in function.external_calls
            if call_name in self.HTTP_MOCK_TARGETS
        ]
        return tuple(dict.fromkeys(targets))

    @staticmethod
    def _root_token(value: str) -> str:
        normalized = value.strip()
        if normalized.startswith("from "):
            normalized = normalized[5:].split(" import ", maxsplit=1)[0].lstrip(".")
        else:
            normalized = normalized.split(" as ", maxsplit=1)[0]
        return normalized.split(".", maxsplit=1)[0]

    @staticmethod
    def _build_test_name(function: FunctionSchema) -> str:
        raw_name = f"{function.module}_{function.qualname}"
        sanitized = "".join(
            character if character.isalnum() else "_"
            for character in raw_name
        ).strip("_")
        return f"test_{sanitized.lower() or 'generated'}"

    @staticmethod
    def _resolve_tests_root(output_path: Path) -> Path:
        resolved = output_path.resolve()
        if resolved.name == "tests":
            return resolved
        if resolved.suffix == ".py":
            return resolved.parent
        return resolved

    def _resolve_suite_output(self, output_path: Path) -> Path:
        resolved = output_path.resolve()
        if resolved.suffix == ".py":
            return resolved
        return self._resolve_tests_root(output_path) / "test_generated.py"

    def _write_template(self, template_name: str, output_path: Path, context: Mapping[str, Any]) -> None:
        rendered = self.environment.get_template(template_name).render(**context)
        output_path.write_text(rendered, encoding="utf-8")

    def _cleanup_legacy_generated_suite(self, tests_root: Path, suite_output: Path) -> None:
        legacy_paths = (
            tests_root / "unit" / "test_logic.py",
            tests_root / "integration" / "test_service.py",
        )
        for legacy_path in legacy_paths:
            if legacy_path == suite_output:
                continue
            if legacy_path.exists() and legacy_path.is_file():
                legacy_path.unlink()

        for legacy_directory in (tests_root / "unit", tests_root / "integration"):
            if legacy_directory.is_dir() and not any(legacy_directory.iterdir()):
                legacy_directory.rmdir()

    @staticmethod
    def _ensure_package_marker(path: Path) -> None:
        if not path.exists():
            path.write_text("", encoding="utf-8")

    @classmethod
    def _build_loader(cls, templates_path: Path | None) -> FileSystemLoader | DictLoader:
        if templates_path is not None:
            return FileSystemLoader(str(templates_path.resolve()))

        template_root = resources.files("engine.generator.templates")
        templates = {
            template_name: template_root.joinpath(template_name).read_text(encoding="utf-8")
            for template_name in cls.TEMPLATE_NAMES
        }
        return DictLoader(templates)
