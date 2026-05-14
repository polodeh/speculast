"""Visual report renderer for speculast."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..analyzer.visitors import ImportsVisitor
from ..core.i18n import LanguageCode, normalize_language, repair_text, tr
from ..core.models import (
    AnalysisResult,
    FunctionContextSchema,
    FunctionSchema,
    GeneratedTestPlan,
    TestExecutionResult,
)
from ..infra.registry import DependencyRegistry
from ..parser import read_python_source
from .dashboard import DashboardBuilder


class VisualReportRenderer:
    """Build a self-contained visual report from semantic analysis results."""

    DATABASE_IMPORTS = frozenset(DependencyRegistry.POSTGRESQL_IMPORTS)
    STATUS_SCORES: Mapping[str, int] = {
        "healthy": 100,
        "running": 88,
        "ready": 100,
        "planned": 72,
        "starting": 48,
        "unavailable": 18,
        "error": 8,
    }
    MODULE_ORDER = ("models", "logic", "service", "database")
    MODULE_LABELS_RU: Mapping[str, str] = {
        "models": "Модели",
        "logic": "Логика",
        "service": "Сервис",
        "database": "База данных",
    }
    MODULE_LABELS_EN: Mapping[str, str] = {
        "models": "Models",
        "logic": "Logic",
        "service": "Service",
        "database": "Database",
    }
    LEGACY_ARTIFACT_KEYS: Mapping[str, str] = {
        "Р СњР В°Р В±Р С•РЎР‚ pytest": "pytest_suite",
        "РќР°Р±РѕСЂ pytest": "pytest_suite",
        "Р В¤Р В°Р в„–Р В» Docker Compose": "docker_compose",
        "Р¤Р°Р№Р» Docker Compose": "docker_compose",
        "HTML-Р С•РЎвЂљРЎвЂЎРЎвЂРЎвЂљ": "html_report",
        "HTML-РѕС‚С‡С‘С‚": "html_report",
        "JSON-Р С•РЎвЂљРЎвЂЎРЎвЂРЎвЂљ pytest": "pytest_json",
        "JSON-РѕС‚С‡С‘С‚ pytest": "pytest_json",
        "JSON-Р С•РЎвЂљРЎвЂЎРЎвЂРЎвЂљ coverage": "coverage_json",
        "JSON-РѕС‚С‡С‘С‚ coverage": "coverage_json",
    }

    def __init__(
        self,
        *,
        lang: str = "en",
        dashboard_builder: DashboardBuilder | None = None,
    ) -> None:
        self.lang: LanguageCode = normalize_language(lang)
        self.dashboard_builder = dashboard_builder or DashboardBuilder(lang=self.lang)
        self.dashboard_builder.lang = self.lang

    def generate(
        self,
        analysis: AnalysisResult,
        output_path: Path,
        /,
        *,
        runtime_status: Mapping[str, str] | None = None,
        execution_result: TestExecutionResult | None = None,
        suite_plan: Sequence[GeneratedTestPlan] = (),
        artifacts: Sequence[tuple[str, Path | None]] = (),
        run_mode: str = "default",
    ) -> Path:
        """Render the visual report to an HTML file."""

        resolved_output = output_path.resolve()
        context = self._build_context(
            analysis,
            runtime_status=runtime_status,
            execution_result=execution_result,
            suite_plan=suite_plan,
            artifacts=artifacts,
            run_mode=run_mode,
        )
        context["artifacts"] = self._inject_report_artifact(context["artifacts"], resolved_output)
        html = self.dashboard_builder.render(context)
        resolved_output.write_text(html, encoding="utf-8")
        return resolved_output

    def _build_context(
        self,
        analysis: AnalysisResult,
        *,
        runtime_status: Mapping[str, str] | None,
        execution_result: TestExecutionResult | None,
        suite_plan: Sequence[GeneratedTestPlan],
        artifacts: Sequence[tuple[str, Path | None]],
        run_mode: str,
    ) -> dict[str, Any]:
        focused_functions = self._focus_functions(analysis.functions)
        focused_suite_plan = self._focus_suite_plan(suite_plan, focused_functions)
        file_imports = self._collect_file_imports(focused_functions)
        plan_lookup = self._build_plan_lookup(focused_suite_plan)
        function_context = self._focus_function_context(analysis.function_context, focused_functions)
        function_view = self._build_function_view(
            focused_functions,
            file_imports,
            plan_lookup,
            function_context,
        )
        readiness_entries = self._build_readiness_entries(
            analysis.required_infra,
            runtime_status=runtime_status,
        )
        readiness_index = round(
            sum(int(entry["score"]) for entry in readiness_entries) / len(readiness_entries)
        )
        test_rows = self._build_test_rows(execution_result)
        heatmap_entries = self._build_heatmap_entries(function_view)
        graph_payload = self._build_graph_payload(function_view)
        function_rows = self._build_function_rows(function_view)
        import_rows = self._build_import_rows(self._focus_imports(analysis.project.imports))
        mock_rows = self._build_mock_rows(function_view)
        coverage_rows = self._build_coverage_rows(execution_result)
        artifact_rows = self._build_artifact_rows(artifacts)
        scorecard = self._build_scorecard(
            analysis=analysis,
            function_view=function_view,
            readiness_index=readiness_index,
            execution_result=execution_result,
            suite_plan=focused_suite_plan,
            run_mode=run_mode,
        )
        operation_rows = self._build_operation_rows(
            analysis=analysis,
            function_view=function_view,
            suite_plan=focused_suite_plan,
            execution_result=execution_result,
            run_mode=run_mode,
        )
        dynamic_translations = self._build_dynamic_translations(
            analysis=analysis,
            function_view=function_view,
            graph_payload=graph_payload,
            readiness_entries=readiness_entries,
            heatmap_entries=heatmap_entries,
            function_rows=function_rows,
            mock_rows=mock_rows,
            scorecard=scorecard,
            operation_rows=operation_rows,
            execution_result=execution_result,
            run_mode=run_mode,
        )

        return {
            "lang": self.lang,
            "project_name": analysis.project.project_name,
            "generated_at": datetime.now(timezone.utc).strftime(
                f"%d.%m.%Y %H:%M {tr(self.lang, 'shared.common.utc_suffix')}"
            ),
            "run_mode_key": run_mode,
            "run_mode_label": self._run_mode_label(run_mode),
            "required_infra": list(analysis.required_infra),
            "sync_count": sum(1 for function in focused_functions if not function.is_async),
            "async_count": sum(1 for function in focused_functions if function.is_async),
            "total_functions": len(focused_functions),
            "total_edges": sum(int(item["call_count"]) for item in function_view),
            "db_function_count": sum(1 for item in function_view if bool(item["requires_database"])),
            "readiness_index": readiness_index,
            "coverage_percent": float(execution_result.coverage_percent if execution_result is not None else 0.0),
            "tests_total": len(test_rows),
            "tests_passed": sum(1 for row in test_rows if row["outcome_key"] == "passed"),
            "tests_failed": sum(1 for row in test_rows if row["outcome_key"] in {"failed", "error"}),
            "dependency_depth": self._build_dependency_depth(function_view),
            "heatmap_entries": heatmap_entries,
            "readiness_entries": readiness_entries,
            "graph_payload": graph_payload,
            "function_rows": function_rows,
            "import_rows": import_rows,
            "test_rows": test_rows,
            "failed_tests": self._build_failed_tests(test_rows),
            "mock_rows": mock_rows,
            "coverage_rows": coverage_rows,
            "artifacts": artifact_rows,
            "scorecard": scorecard,
            "operation_rows": operation_rows,
            "dynamic_translations": dynamic_translations,
            "stdout_log": execution_result.stdout if execution_result is not None else "",
            "stderr_log": execution_result.stderr if execution_result is not None else "",
        }

    def _focus_functions(
        self,
        functions: tuple[FunctionSchema, ...],
    ) -> tuple[FunctionSchema, ...]:
        return tuple(functions)

    def _focus_suite_plan(
        self,
        suite_plan: Sequence[GeneratedTestPlan],
        functions: Sequence[FunctionSchema],
    ) -> tuple[GeneratedTestPlan, ...]:
        if not functions:
            return tuple(suite_plan)
        allowed_modules = {function.module for function in functions}
        focused_plan = tuple(
            plan
            for plan in suite_plan
            if plan.module in allowed_modules
        )
        return focused_plan or tuple(suite_plan)

    def _focus_imports(self, imports: Sequence[str]) -> list[str]:
        return list(imports)

    def _focus_function_context(
        self,
        function_context: Mapping[str, FunctionContextSchema],
        functions: Sequence[FunctionSchema],
    ) -> dict[str, FunctionContextSchema]:
        if not functions:
            return dict(function_context)
        allowed_labels = {self._function_label(function) for function in functions}
        return {
            label: payload
            for label, payload in function_context.items()
            if label in allowed_labels
        }

    def _collect_file_imports(
        self,
        functions: tuple[FunctionSchema, ...],
    ) -> dict[Path, list[str]]:
        module_by_path: dict[Path, str] = {}
        for function in functions:
            module_by_path.setdefault(function.file_path, function.module)

        imports_by_path: dict[Path, list[str]] = {}
        for file_path, module_name in module_by_path.items():
            try:
                tree = ast.parse(read_python_source(file_path), filename=str(file_path))
            except (OSError, SyntaxError):
                imports_by_path[file_path] = []
                continue

            visitor = ImportsVisitor(
                file_path=file_path,
                module_name=module_name,
                include_private=True,
            )
            visitor.visit(tree)
            imports_by_path[file_path] = visitor.as_list()
        return imports_by_path

    @staticmethod
    def _build_plan_lookup(
        suite_plan: Sequence[GeneratedTestPlan],
    ) -> dict[tuple[str, str], GeneratedTestPlan]:
        return {
            (plan.module, plan.qualname): plan
            for plan in suite_plan
        }

    def _build_function_view(
        self,
        functions: tuple[FunctionSchema, ...],
        file_imports: dict[Path, list[str]],
        plan_lookup: dict[tuple[str, str], GeneratedTestPlan],
        function_context: Mapping[str, FunctionContextSchema],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for function in functions:
            imports_for_file = file_imports.get(function.file_path, [])
            database_score = self._database_score(function, imports_for_file)
            external_calls = list(dict.fromkeys(function.external_calls))
            plan = plan_lookup.get((function.module, function.qualname))
            label = self._function_label(function)
            context = function_context.get(label)
            localized_name_map = self._localized_name_map(label, function, context)
            description_map = self._description_map(
                label,
                function,
                context,
                external_calls=external_calls,
                database_score=database_score,
            )
            items.append(
                {
                    "id": self._sanitize_identifier(label),
                    "label": label,
                    "module": function.module,
                    "module_key": self._module_key(function.module),
                    "module_label_ru": self._module_label(function.module, "ru"),
                    "module_label_en": self._module_label(function.module, "en"),
                    "name": function.name,
                    "qualname": function.qualname,
                    "is_async": function.is_async,
                    "requires_database": database_score > 0,
                    "database_score": database_score,
                    "external_calls": external_calls,
                    "call_count": len(external_calls) + database_score,
                    "source_snippet": self._source_snippet(function),
                    "test_mode": plan.mode.value if plan is not None else "behavioral",
                    "mock_targets": list(plan.mock_targets) if plan is not None else [],
                    "skip_reason": plan.skip_reason if plan is not None else None,
                    "uses_real_db": bool(plan.uses_real_db) if plan is not None else False,
                    "localized_name": str(localized_name_map[self.lang]),
                    "localized_name_map": localized_name_map,
                    "description_ru": str(description_map["ru"]),
                    "description_map": description_map,
                }
            )
        return items

    def _build_function_rows(self, function_view: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in function_view:
            rows.append(
                {
                    "id": str(item["id"]),
                    "function": str(item["qualname"]),
                    "module": str(item["module"]),
                    "mode": tr(self.lang, f"shared.function_modes.{'async' if bool(item['is_async']) else 'sync'}"),
                    "mode_key": "async" if bool(item["is_async"]) else "sync",
                    "infra": self._infra_label(item),
                    "infra_key": "postgresql" if bool(item["requires_database"]) else "not_required",
                    "strategy": tr(self.lang, f"shared.test_modes.{item['test_mode']}"),
                    "strategy_key": str(item["test_mode"]),
                    "calls": len(item["external_calls"]),
                    "external_calls": ", ".join(str(value) for value in item["external_calls"]) or tr(self.lang, "shared.common.none"),
                    "mocks": self._mock_label(item),
                    "mocks_key": self._mock_key(item),
                    "skip_reason": str(item["skip_reason"] or ""),
                    "localized_name": str(item["localized_name"]),
                    "description_ru": str(item["description_ru"]),
                    "module_label_ru": str(item["module_label_ru"]),
                    "module_label_en": str(item["module_label_en"]),
                    "source_snippet": str(item["source_snippet"]),
                }
            )
        return rows

    def _build_graph_payload(self, function_view: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not function_view:
            return {
                "nodes": [
                    {
                        "data": {
                            "id": "module_empty",
                            "label": tr(self.lang, "report.placeholders.no_functions"),
                            "kind": "module",
                            "moduleKey": "empty",
                            "localizedName": tr(self.lang, "report.placeholders.no_functions"),
                            "description": tr(self.lang, "report.placeholders.no_functions"),
                            "callCount": 0,
                            "functionCount": 0,
                            "mockInsight": tr(self.lang, "shared.common.none"),
                        }
                    }
                ],
                "edges": [],
                "defaultExpandedModules": [],
            }

        modules = self._module_rows(function_view)
        local_targets = self._build_local_call_lookup(function_view)
        call_usage: dict[str, list[str]] = defaultdict(list)
        summary_edges: dict[tuple[str, str], int] = defaultdict(int)
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for module_key, module_row in modules.items():
            nodes.append(
                {
                    "data": {
                        "id": f"module_{module_key}",
                        "label": str(module_row["label"]),
                        "kind": "module",
                        "moduleKey": module_key,
                        "localizedName": str(module_row["label"]),
                        "description": str(module_row["description"]),
                        "callCount": int(module_row["call_count"]),
                        "functionCount": int(module_row["function_count"]),
                        "mockInsight": str(module_row["summary"]),
                    }
                }
            )

        for item in function_view:
            function_id = f"function_{item['id']}"
            module_key = str(item["module_key"])
            nodes.append(
                {
                    "data": {
                        "id": function_id,
                        "label": str(item["label"]),
                        "kind": "function",
                        "moduleKey": module_key,
                        "localizedName": str(item["localized_name"]),
                        "description": str(item["description_ru"]),
                        "callCount": int(item["call_count"]),
                        "functionCount": 0,
                        "mockInsight": self._mock_label(item),
                        "isAsync": bool(item["is_async"]),
                        "requiresDatabase": bool(item["requires_database"]),
                    }
                }
            )
            edges.append(
                {
                    "data": {
                        "id": f"edge_module_{module_key}_{item['id']}",
                        "source": f"module_{module_key}",
                        "target": function_id,
                        "kind": "detail",
                        "moduleKey": module_key,
                    }
                }
            )
            for external_call in item["external_calls"]:
                call_key = str(external_call)
                call_id = f"call_{self._sanitize_identifier(call_key)}"
                if not any(node["data"]["id"] == call_id for node in nodes):
                    nodes.append(
                        {
                            "data": {
                                "id": call_id,
                                "label": call_key,
                                "kind": "call",
                                "moduleKey": module_key,
                                "localizedName": call_key,
                                "description": self._call_description(call_key),
                                "callCount": 0,
                                "functionCount": 0,
                                "mockInsight": tr(self.lang, "shared.common.none"),
                            }
                        }
                    )
                edges.append(
                    {
                        "data": {
                            "id": f"edge_{item['id']}_{self._sanitize_identifier(call_key)}",
                            "source": function_id,
                            "target": call_id,
                            "kind": "detail",
                            "moduleKey": module_key,
                        }
                    }
                )
                call_usage[module_key].append(call_key)
                target_label = local_targets.get(call_key)
                if target_label is None:
                    continue
                target_module = self._module_key(target_label.split(".", maxsplit=2)[1] if target_label.count(".") >= 2 else target_label)
                summary_edges[(module_key, target_module)] += 1

        for (source_module, target_module), weight in summary_edges.items():
            if source_module == target_module:
                continue
            edges.append(
                {
                    "data": {
                        "id": f"summary_{source_module}_{target_module}",
                        "source": f"module_{source_module}",
                        "target": f"module_{target_module}",
                        "kind": "summary",
                        "moduleKey": source_module,
                        "weight": weight,
                    }
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "defaultExpandedModules": [],
        }

    def _module_rows(self, function_view: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for item in function_view:
            grouped[str(item["module_key"])].append(item)

        ordered_keys = sorted(
            grouped,
            key=lambda key: (
                self.MODULE_ORDER.index(key) if key in self.MODULE_ORDER else len(self.MODULE_ORDER),
                key,
            ),
        )
        rows: dict[str, dict[str, Any]] = {}
        for module_key in ordered_keys:
            items = grouped[module_key]
            label = repair_text(self.MODULE_LABELS_RU.get(module_key, module_key.capitalize()))
            rows[module_key] = {
                "label": label,
                "description": repair_text(
                    f"{label}: {len(items)} функций, {sum(len(item['external_calls']) for item in items)} внешних вызовов."
                ),
                "function_count": len(items),
                "call_count": sum(int(item["call_count"]) for item in items),
                "summary": ", ".join(sorted({str(item['name']) for item in items})) or tr(self.lang, "shared.common.none"),
            }
        return rows

    @staticmethod
    def _build_local_call_lookup(
        function_view: Sequence[Mapping[str, Any]],
    ) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for item in function_view:
            label = str(item["label"])
            lookup[label] = label
            lookup[str(item["qualname"])] = label
            lookup[str(item["name"])] = label
        return lookup

    def _build_heatmap_entries(self, function_view: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        candidates = [item for item in function_view if bool(item["requires_database"])]
        if not candidates:
            return []

        max_score = max(int(item["database_score"]) for item in candidates) or 1
        rows: list[dict[str, Any]] = []
        for item in sorted(
            candidates,
            key=lambda entry: (-int(entry["database_score"]), str(entry["label"])),
        ):
            score = int(item["database_score"])
            rows.append(
                {
                    "id": str(item["id"]),
                    "label": str(item["localized_name"]),
                    "module": str(item["module_label_ru"]),
                    "score": score,
                    "width_percent": round(score / max_score * 100, 2),
                    "technical_label": str(item["label"]),
                }
            )
        return rows[:12]

    def _build_dependency_depth(self, function_view: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        ranked = sorted(
            function_view,
            key=lambda item: (-int(item["call_count"]), str(item["label"])),
        )
        if not ranked:
            return [{"label": tr(self.lang, "report.placeholders.no_functions"), "value": 0}]

        return [
            {
                "label": str(item["label"]),
                "value": int(item["call_count"]),
            }
            for item in ranked[:8]
        ]

    def _build_readiness_entries(
        self,
        required_infra: list[str],
        *,
        runtime_status: Mapping[str, str] | None,
    ) -> list[dict[str, Any]]:
        if not required_infra:
            return [
                {
                    "id": "not_required",
                    "service_key": "not_required",
                    "status_key": "ready",
                    "label": tr(self.lang, "shared.infra.not_required"),
                    "status": tr(self.lang, "shared.status_words.ready"),
                    "score": 100,
                }
            ]

        runtime_status = runtime_status or {}
        rows: list[dict[str, Any]] = []
        for service_name in required_infra:
            status_key = str(runtime_status.get(service_name, "planned"))
            rows.append(
                {
                    "id": service_name,
                    "service_key": service_name,
                    "status_key": status_key,
                    "label": tr(self.lang, f"shared.service_names.{service_name}"),
                    "status": tr(self.lang, f"shared.status_words.{status_key}"),
                    "score": int(self.STATUS_SCORES.get(status_key, 24)),
                }
            )
        return rows

    def _build_import_rows(self, imports: Sequence[str]) -> list[dict[str, str]]:
        return [
            {
                "import": import_name,
                "root": self._root_token(import_name),
            }
            for import_name in sorted(dict.fromkeys(imports))
        ]

    def _build_test_rows(
        self,
        execution_result: TestExecutionResult | None,
    ) -> list[dict[str, Any]]:
        if execution_result is None:
            return []

        return [
            {
                "nodeid": test_case.nodeid,
                "outcome": tr(self.lang, f"shared.outcomes.{test_case.outcome.value}"),
                "outcome_key": test_case.outcome.value,
                "duration": round(float(test_case.duration), 3),
                "message": test_case.message or "",
                "log": test_case.longrepr or "",
                "mocked_calls": ", ".join(test_case.mocked_calls) or tr(self.lang, "shared.common.none"),
            }
            for test_case in execution_result.tests
        ]

    @staticmethod
    def _build_failed_tests(test_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        return [
            {
                "nodeid": str(test_row["nodeid"]),
                "outcome": str(test_row["outcome"]),
                "outcome_key": str(test_row["outcome_key"]),
                "message": str(test_row["message"]),
                "log": str(test_row["log"]),
            }
            for test_row in test_rows
            if str(test_row["outcome_key"]) in {"failed", "error"}
        ]

    @staticmethod
    def _build_coverage_rows(
        execution_result: TestExecutionResult | None,
    ) -> list[dict[str, Any]]:
        if execution_result is None:
            return []

        rows = [
            {
                "path": coverage_entry.path,
                "covered_lines": coverage_entry.covered_lines,
                "missing_lines": coverage_entry.missing_lines,
                "num_statements": coverage_entry.num_statements,
                "percent_covered": round(float(coverage_entry.percent_covered), 2),
            }
            for coverage_entry in execution_result.coverage
        ]
        return sorted(rows, key=lambda row: (-float(row["percent_covered"]), str(row["path"])))

    def _build_mock_rows(self, function_view: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for item in function_view:
            rows.append(
                {
                    "id": str(item["id"]),
                    "function": str(item["qualname"]),
                    "module": str(item["module"]),
                    "strategy": tr(self.lang, f"shared.test_modes.{item['test_mode']}"),
                    "strategy_key": str(item["test_mode"]),
                    "mocks": self._mock_label(item),
                    "mocks_key": self._mock_key(item),
                    "localized_name": str(item["localized_name"]),
                }
            )
        return rows

    def _build_artifact_rows(
        self,
        artifacts: Sequence[tuple[str, Path | None]],
    ) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for artifact_key, path in artifacts:
            normalized_key = self.LEGACY_ARTIFACT_KEYS.get(artifact_key, artifact_key)
            rows.append(
                {
                    "label": tr(self.lang, f"shared.artifacts.{normalized_key}"),
                    "key": normalized_key,
                    "path": str(path) if path is not None else tr(self.lang, "shared.artifacts.not_created"),
                    "status": tr(self.lang, "shared.artifacts.ready") if path is not None else tr(self.lang, "shared.artifacts.not_created"),
                    "status_key": "ready" if path is not None else "not_created",
                }
            )
        return rows

    def _build_scorecard(
        self,
        *,
        analysis: AnalysisResult,
        function_view: Sequence[Mapping[str, Any]],
        readiness_index: int,
        execution_result: TestExecutionResult | None,
        suite_plan: Sequence[GeneratedTestPlan],
        run_mode: str,
    ) -> list[dict[str, Any]]:
        semantic_total = len(function_view)
        semantic_current = semantic_total
        skipped_plans = sum(1 for plan in suite_plan if plan.mode.value == "skipped")
        generation_total = len(suite_plan)
        generation_current = max(generation_total - skipped_plans, 0)
        execution_total = execution_result.total if execution_result is not None else 0
        execution_current = execution_result.passed if execution_result is not None else 0
        autonomy_total = 5
        autonomy_current = 5 if run_mode == "run_all" else 4 if run_mode in {"generate_only", "visualize"} else 0

        semantic_score, semantic_display_current, semantic_display_total = self._ratio_metrics(
            semantic_current,
            semantic_total,
        )
        generation_score, generation_display_current, generation_display_total = self._ratio_metrics(
            generation_current,
            generation_total,
        )
        infra_score, infra_display_current, infra_display_total = self._ratio_metrics(
            readiness_index,
            100,
        )
        execution_score, execution_display_current, execution_display_total = self._ratio_metrics(
            execution_current,
            execution_total,
        )
        autonomy_score, autonomy_display_current, autonomy_display_total = self._ratio_metrics(
            autonomy_current,
            autonomy_total,
        )

        return [
            {
                "id": "semantic_map",
                "label": tr(self.lang, "report.scorecard.semantic_map"),
                "label_key": "report.scorecard.semantic_map",
                "score": semantic_score,
                "description": f"{semantic_display_current} / {semantic_display_total}",
            },
            {
                "id": "generation_strategy",
                "label": tr(self.lang, "report.scorecard.generation_strategy"),
                "label_key": "report.scorecard.generation_strategy",
                "score": generation_score,
                "description": f"{generation_display_current} / {generation_display_total}",
            },
            {
                "id": "infrastructure_ready",
                "label": tr(self.lang, "report.scorecard.infrastructure_ready"),
                "label_key": "report.scorecard.infrastructure_ready",
                "score": infra_score,
                "description": f"{infra_display_current} / {infra_display_total}",
            },
            {
                "id": "execution_results",
                "label": tr(self.lang, "report.scorecard.execution_results"),
                "label_key": "report.scorecard.execution_results",
                "score": execution_score,
                "description": f"{execution_display_current} / {execution_display_total}",
            },
            {
                "id": "autonomy_mode",
                "label": tr(self.lang, "report.scorecard.autonomy_mode"),
                "label_key": "report.scorecard.autonomy_mode",
                "score": autonomy_score,
                "description": f"{autonomy_display_current} / {autonomy_display_total}",
            },
        ]

    def _build_operation_rows(
        self,
        *,
        analysis: AnalysisResult,
        function_view: Sequence[Mapping[str, Any]],
        suite_plan: Sequence[GeneratedTestPlan],
        execution_result: TestExecutionResult | None,
        run_mode: str,
    ) -> list[dict[str, str]]:
        import_count = len(self._focus_imports(analysis.project.imports))
        total_files = len(analysis.project.analyzed_files)
        total_edges = sum(int(item["call_count"]) for item in function_view)
        unit_count = sum(1 for plan in suite_plan if plan.mode.value == "behavioral")
        integration_count = sum(1 for plan in suite_plan if plan.mode.value == "integration")
        services = ", ".join(
            tr(self.lang, f"shared.service_names.{service_name}") if service_name in {"postgresql", "redis"} else service_name
            for service_name in analysis.required_infra
        ) or tr(self.lang, "shared.infra.not_required")

        rows = [
            {
                "id": "step_01",
                "step": "01",
                "title": tr(self.lang, "report.operations.step_01_title"),
                "details": tr(
                    self.lang,
                    "report.operations.step_01_details",
                    project_name=analysis.project.project_name,
                    run_mode=self._run_mode_label(run_mode),
                ),
            },
            {
                "id": "step_02",
                "step": "02",
                "title": tr(self.lang, "report.operations.step_02_title"),
                "details": tr(
                    self.lang,
                    "report.operations.step_02_details",
                    total_files=total_files,
                    total_functions=len(function_view),
                ),
            },
            {
                "id": "step_03",
                "step": "03",
                "title": tr(self.lang, "report.operations.step_03_title"),
                "details": tr(
                    self.lang,
                    "report.operations.step_03_details",
                    import_count=import_count,
                    total_edges=total_edges,
                ),
            },
            {
                "id": "step_04",
                "step": "04",
                "title": tr(self.lang, "report.operations.step_04_title"),
                "details": tr(
                    self.lang,
                    "report.operations.step_04_details",
                    services=services,
                ),
            },
            {
                "id": "step_05",
                "step": "05",
                "title": tr(self.lang, "report.operations.step_05_title"),
                "details": tr(
                    self.lang,
                    "report.operations.step_05_details",
                    unit_count=unit_count,
                    integration_count=integration_count,
                ),
            },
        ]

        if execution_result is not None:
            rows.append(
                {
                    "id": "step_06",
                    "step": "06",
                    "title": tr(self.lang, "report.operations.step_06_executed_title"),
                    "details": tr(
                        self.lang,
                        "report.operations.step_06_executed_details",
                        passed=execution_result.passed,
                        total=execution_result.total,
                        errors=execution_result.failed + execution_result.errors,
                        coverage=execution_result.coverage_percent,
                    ),
                }
            )
        else:
            rows.append(
                {
                    "id": "step_06",
                    "step": "06",
                    "title": tr(self.lang, "report.operations.step_06_skipped_title"),
                    "details": tr(self.lang, "report.operations.step_06_skipped_details"),
                }
            )

        rows.append(
            {
                "id": "step_07",
                "step": "07",
                "title": tr(self.lang, "report.operations.step_07_title"),
                "details": (
                    "Интерактивный векторный граф, таблицы, метрики и диагностические блоки собраны в один автономный HTML-файл."
                    if self.lang == "ru"
                    else "The interactive vector graph, tables, metrics and diagnostic blocks were assembled into one autonomous HTML file."
                ),
            }
        )
        return rows

    def _build_dynamic_translations(
        self,
        *,
        analysis: AnalysisResult,
        function_view: Sequence[Mapping[str, Any]],
        graph_payload: Mapping[str, Any],
        readiness_entries: Sequence[Mapping[str, Any]],
        heatmap_entries: Sequence[Mapping[str, Any]],
        function_rows: Sequence[Mapping[str, Any]],
        mock_rows: Sequence[Mapping[str, Any]],
        scorecard: Sequence[Mapping[str, Any]],
        operation_rows: Sequence[Mapping[str, Any]],
        execution_result: TestExecutionResult | None,
        run_mode: str,
    ) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
        languages: tuple[LanguageCode, ...] = ("ru", "en")
        dynamic: dict[str, dict[str, dict[str, dict[str, str]]]] = {
            language: {
                "operations": {},
                "heatmap": {},
                "scorecard": {},
                "readiness": {},
                "functions": {},
                "mocks": {},
                "graph": {},
            }
            for language in languages
        }

        function_lookup = {str(item["id"]): item for item in function_view}
        readiness_lookup = {str(item["id"]): item for item in readiness_entries}
        graph_nodes = {
            str(node["data"]["id"]): node["data"]
            for node in graph_payload.get("nodes", [])
            if isinstance(node, Mapping) and isinstance(node.get("data"), Mapping)
        }

        for language in languages:
            for row in operation_rows:
                row_id = str(row["id"])
                dynamic[language]["operations"][row_id] = {
                    "title": self._operation_title(
                        row_id,
                        language,
                        executed=execution_result is not None,
                    ),
                    "details": self._operation_details(
                        row_id,
                        analysis=analysis,
                        function_view=function_view,
                        execution_result=execution_result,
                        run_mode=run_mode,
                        language=language,
                    ),
                }

            for row in scorecard:
                row_id = str(row["id"])
                dynamic[language]["scorecard"][row_id] = {
                    "description": self._scorecard_description(
                        row_id,
                        row=row,
                        analysis=analysis,
                        execution_result=execution_result,
                        run_mode=run_mode,
                        language=language,
                    ),
                }

            for row in readiness_entries:
                row_id = str(row["id"])
                dynamic[language]["readiness"][row_id] = {
                    "label": self._readiness_label(readiness_lookup[row_id], language),
                    "status": self._readiness_status(readiness_lookup[row_id], language),
                }

            for row in heatmap_entries:
                row_id = str(row["id"])
                source = function_lookup.get(row_id)
                if source is None:
                    continue
                dynamic[language]["heatmap"][row_id] = {
                    "label": self._localized_name(language, source),
                    "module": self._module_label(str(source["module"]), language),
                }

            for row in function_rows:
                row_id = str(row["id"])
                source = function_lookup.get(row_id)
                if source is None:
                    continue
                dynamic[language]["functions"][row_id] = {
                    "localized_name": self._localized_name(language, source),
                    "description": self._description(language, source),
                    "module_label": self._module_label(str(source["module"]), language),
                    "mocks": self._mock_label_for_language(source, language),
                    "code": str(source.get("source_snippet", "")),
                }

            for row in mock_rows:
                row_id = str(row["id"])
                source = function_lookup.get(row_id)
                if source is None:
                    continue
                dynamic[language]["mocks"][row_id] = {
                    "localized_name": self._localized_name(language, source),
                    "mocks": self._mock_label_for_language(source, language),
                    "code": str(source.get("source_snippet", "")),
                }

            for node_id, data in graph_nodes.items():
                dynamic[language]["graph"][node_id] = self._graph_node_translation(
                    node_id,
                    data=data,
                    function_lookup=function_lookup,
                    language=language,
                )

        return dynamic

    def _inject_report_artifact(
        self,
        artifact_rows: Sequence[Mapping[str, str]],
        report_path: Path,
    ) -> list[dict[str, str]]:
        rows = [dict(row) for row in artifact_rows]
        report_key = "html_report"
        report_label = tr(self.lang, "shared.artifacts.html_report")
        ready_label = tr(self.lang, "shared.artifacts.ready")
        for row in rows:
            if row.get("key") == report_key or row.get("label") == report_label:
                row["key"] = report_key
                row["label"] = report_label
                row["path"] = str(report_path)
                row["status"] = ready_label
                return rows

        rows.append(
            {
                "key": report_key,
                "label": report_label,
                "path": str(report_path),
                "status": ready_label,
            }
        )
        return rows

    def _database_score(self, function: FunctionSchema, imports_for_file: Sequence[str]) -> int:
        score = sum(
            1
            for external_call in function.external_calls
            if self._root_token(external_call) in self.DATABASE_IMPORTS
        )
        if score > 0:
            return score

        file_roots = {self._root_token(import_name) for import_name in imports_for_file}
        if file_roots & self.DATABASE_IMPORTS:
            return 1
        return 0

    @staticmethod
    def _root_token(value: str) -> str:
        normalized = value.strip()
        if normalized.startswith("from "):
            normalized = normalized[5:].split(" import ", maxsplit=1)[0].lstrip(".")
        else:
            normalized = normalized.split(" as ", maxsplit=1)[0]
        return normalized.split(".", maxsplit=1)[0]

    def _run_mode_label(self, run_mode: str) -> str:
        if run_mode in {"generate_only", "run_all", "visualize"}:
            return tr(self.lang, f"shared.run_modes.{run_mode}")
        return tr(self.lang, "shared.run_modes.default")

    @staticmethod
    def _sanitize_identifier(value: str) -> str:
        return "".join(character if character.isalnum() else "_" for character in value).strip("_") or "node"

    @staticmethod
    def _function_label(function: FunctionSchema) -> str:
        return f"{function.module}.{function.qualname}"

    @classmethod
    def _module_key(cls, module_name: str) -> str:
        return module_name.split(".")[-1]

    @classmethod
    def _module_label(cls, module_name: str, language: LanguageCode) -> str:
        module_key = cls._module_key(module_name)
        try:
            return tr(language, f"shared.module_names.{module_key}")
        except KeyError:
            labels = cls.MODULE_LABELS_RU if language == "ru" else cls.MODULE_LABELS_EN
            label = labels.get(module_key, cls._humanize_identifier(module_key))
            return repair_text(label) if language == "ru" else label

    @staticmethod
    def _humanize_identifier(value: str) -> str:
        words = [word for word in value.replace(".", "_").split("_") if word]
        if not words:
            return value
        return " ".join(word.capitalize() for word in words)

    def _localized_name_map(
        self,
        label: str,
        function: FunctionSchema,
        context: FunctionContextSchema | None,
    ) -> dict[str, str]:
        return {
            "ru": context.localized_name if context is not None else label,
            "en": self._humanize_identifier(function.qualname.replace(".", "_")) or label,
        }

    def _description_map(
        self,
        label: str,
        function: FunctionSchema,
        context: FunctionContextSchema | None,
        *,
        external_calls: Sequence[str],
        database_score: int,
    ) -> dict[str, str]:
        if context is not None:
            ru_description = context.description_ru
        else:
            ru_description = repair_text(
                f"Функция {label} анализируется без дополнительного описания."
            )

        if database_score > 0:
            en_description = (
                f"Function {label} participates in the database-backed execution path "
                f"and raises integration readiness requirements."
            )
        elif external_calls:
            en_description = (
                f"Function {label} issues {len(external_calls)} external call(s) and shapes "
                "the dependency topology of the service."
            )
        elif function.is_async:
            en_description = (
                f"Async function {label} has no external calls but remains part of the "
                "semantic execution chain."
            )
        else:
            en_description = f"Function {label} is a deterministic semantic unit without external calls."

        return {
            "ru": ru_description,
            "en": en_description,
        }

    def _localized_name(self, language: LanguageCode, item: Mapping[str, Any]) -> str:
        localized_name_map = item.get("localized_name_map")
        if isinstance(localized_name_map, Mapping):
            return str(localized_name_map.get(language) or localized_name_map.get("en") or item["label"])
        return str(item["localized_name"])

    def _description(self, language: LanguageCode, item: Mapping[str, Any]) -> str:
        description_map = item.get("description_map")
        if isinstance(description_map, Mapping):
            return str(description_map.get(language) or description_map.get("en") or item["label"])
        return str(item["description_ru"])

    def _source_snippet(self, function: FunctionSchema) -> str:
        try:
            lines = read_python_source(function.file_path).splitlines()
        except OSError:
            return ""
        start = max(function.lineno - 1, 0)
        end = max(function.end_lineno, function.lineno)
        return "\n".join(lines[start:end]).strip()

    def _call_description(self, call_name: str, language: LanguageCode | None = None) -> str:
        resolved_language = language or self.lang
        root = self._root_token(call_name)
        if root in self.DATABASE_IMPORTS or "session" in call_name.lower():
            return (
                repair_text("Вызов связан с контуром базы данных и влияет на интеграционный сценарий.")
                if resolved_language == "ru"
                else "The call touches the database layer and affects integration readiness."
            )
        return (
            repair_text(f"Внешний вызов {call_name}, который был извлечён из AST тела функции.")
            if resolved_language == "ru"
            else f"External call {call_name} extracted from the function body AST."
        )

    def _infra_label(self, item: Mapping[str, Any]) -> str:
        if bool(item["requires_database"]):
            return tr(self.lang, "shared.service_names.postgresql")
        return tr(self.lang, "shared.infra.not_required")

    def _mock_label(self, item: Mapping[str, Any]) -> str:
        if item["mock_targets"]:
            return ", ".join(str(value) for value in item["mock_targets"])
        if bool(item["uses_real_db"]):
            return tr(self.lang, "shared.infra.real_db")
        return tr(self.lang, "shared.infra.no_mocks")

    def _mock_label_for_language(self, item: Mapping[str, Any], language: LanguageCode) -> str:
        if item["mock_targets"]:
            return ", ".join(str(value) for value in item["mock_targets"])
        if bool(item["uses_real_db"]):
            return tr(language, "shared.infra.real_db")
        return tr(language, "shared.infra.no_mocks")

    def _readiness_label(self, row: Mapping[str, Any], language: LanguageCode) -> str:
        service_key = str(row.get("service_key", ""))
        if service_key == "not_required":
            return tr(language, "shared.infra.not_required")
        return tr(language, f"shared.service_names.{service_key}")

    def _readiness_status(self, row: Mapping[str, Any], language: LanguageCode) -> str:
        status_key = str(row.get("status_key", "ready"))
        return tr(language, f"shared.status_words.{status_key}")

    def _scorecard_description(
        self,
        row_id: str,
        *,
        row: Mapping[str, Any],
        analysis: AnalysisResult,
        execution_result: TestExecutionResult | None,
        run_mode: str,
        language: LanguageCode,
    ) -> str:
        return str(row["description"])

    def _operation_title(self, row_id: str, language: LanguageCode, *, executed: bool) -> str:
        if row_id == "step_06":
            key = "report.operations.step_06_executed_title" if executed else "report.operations.step_06_skipped_title"
            return tr(language, key)
        key = row_id.replace("step_", "report.operations.step_") + "_title"
        return tr(language, key)

    def _operation_details(
        self,
        row_id: str,
        *,
        analysis: AnalysisResult,
        function_view: Sequence[Mapping[str, Any]],
        execution_result: TestExecutionResult | None,
        run_mode: str,
        language: LanguageCode,
    ) -> str:
        import_count = len(self._focus_imports(analysis.project.imports))
        total_files = len(analysis.project.analyzed_files)
        total_edges = sum(int(item["call_count"]) for item in function_view)
        unit_count = sum(1 for item in function_view if str(item["test_mode"]) == "behavioral")
        integration_count = sum(1 for item in function_view if str(item["test_mode"]) == "integration")
        services = ", ".join(
            tr(language, f"shared.service_names.{service_name}") if service_name in {"postgresql", "redis"} else service_name
            for service_name in analysis.required_infra
        ) or tr(language, "shared.infra.not_required")

        if row_id == "step_01":
            return tr(
                language,
                "report.operations.step_01_details",
                project_name=analysis.project.project_name,
                run_mode=self._run_mode_label_for_language(run_mode, language),
            )
        if row_id == "step_02":
            return tr(
                language,
                "report.operations.step_02_details",
                total_files=total_files,
                total_functions=len(function_view),
            )
        if row_id == "step_03":
            return tr(
                language,
                "report.operations.step_03_details",
                import_count=import_count,
                total_edges=total_edges,
            )
        if row_id == "step_04":
            return tr(language, "report.operations.step_04_details", services=services)
        if row_id == "step_05":
            return tr(
                language,
                "report.operations.step_05_details",
                unit_count=unit_count,
                integration_count=integration_count,
            )
        if row_id == "step_06":
            if execution_result is None:
                return tr(language, "report.operations.step_06_skipped_details")
            return tr(
                language,
                "report.operations.step_06_executed_details",
                passed=execution_result.passed,
                total=execution_result.total,
                errors=execution_result.failed + execution_result.errors,
                coverage=execution_result.coverage_percent,
            )
        return tr(language, "report.operations.step_07_details")

    def _run_mode_label_for_language(self, run_mode: str, language: LanguageCode) -> str:
        if run_mode in {"generate_only", "run_all", "visualize"}:
            return tr(language, f"shared.run_modes.{run_mode}")
        return tr(language, "shared.run_modes.default")

    @staticmethod
    def _ratio_metrics(current: int | float, total: int | float) -> tuple[int, int, int]:
        normalized_total = max(int(round(total)), 0)
        if normalized_total == 0:
            return 0, 0, 0

        normalized_current = max(int(round(current)), 0)
        display_current = min(normalized_current, normalized_total)
        score = round(display_current / normalized_total * 100)
        return min(score, 100), display_current, normalized_total

    def _graph_node_translation(
        self,
        node_id: str,
        *,
        data: Mapping[str, Any],
        function_lookup: Mapping[str, Mapping[str, Any]],
        language: LanguageCode,
    ) -> dict[str, str]:
        kind = str(data.get("kind", "function"))
        if kind == "module":
            module_key = str(data.get("moduleKey", ""))
            label = self._module_label(module_key, language)
            description = (
                f"{label}: {int(data.get('functionCount', 0))} function(s), {int(data.get('callCount', 0))} link(s)."
                if language == "en"
                else f"{label}: {int(data.get('functionCount', 0))} функций, {int(data.get('callCount', 0))} связей."
            )
            return {
                "label": label,
                "localized_name": label,
                "description": description,
                "mock_insight": str(data.get("mockInsight", tr(language, "shared.common.none"))),
                "module_label": label,
                "code": "",
            }

        source = function_lookup.get(node_id.replace("function_", ""))
        if kind == "function" and source is not None:
            return {
                "label": str(data.get("label", source["label"])),
                "localized_name": self._localized_name(language, source),
                "description": self._description(language, source),
                "mock_insight": self._mock_label_for_language(source, language),
                "module_label": self._module_label(str(source["module"]), language),
                "code": str(source.get("source_snippet", "")),
            }

        technical_label = str(data.get("label", node_id))
        return {
            "label": technical_label,
            "localized_name": technical_label,
            "description": self._call_description(technical_label, language),
            "mock_insight": tr(language, "shared.common.none"),
            "module_label": self._module_label(str(data.get("moduleKey", "")), language),
            "code": "",
        }

    @staticmethod
    def _mock_key(item: Mapping[str, Any]) -> str | None:
        if item["mock_targets"]:
            return None
        if bool(item["uses_real_db"]):
            return "real_db"
        return "no_mocks"
