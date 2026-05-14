"""HTML dashboard builder for speculast visual reports."""

from __future__ import annotations

from importlib import resources
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import DictLoader, Environment, FileSystemLoader, select_autoescape

from ..core.i18n import LanguageCode, get_catalog, normalize_language, tr


class DashboardBuilder:
    """Render a self-contained industrial dashboard with Cytoscape.js and Chart.js."""

    TEMPLATE_NAME = "report.html"

    def __init__(self, *, lang: str = "en", templates_path: Path | None = None) -> None:
        self.lang: LanguageCode = normalize_language(lang)
        self.environment = Environment(
            loader=self._build_loader(templates_path),
            autoescape=select_autoescape(("html", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, context: Mapping[str, Any], /) -> str:
        """Build the final dashboard HTML."""

        self.lang = normalize_language(str(context.get("lang", self.lang)))
        ui = self._build_ui()
        dynamic_translations = context.get("dynamic_translations", {})
        translation_payload = {
            code: {
                "catalog": get_catalog(code),
                "ui": self._build_ui_for(code),
                "dynamic": dynamic_translations.get(code, {}),
            }
            for code in ("ru", "en")
        }
        template = self.environment.get_template(self.TEMPLATE_NAME)
        return template.render(
            lang=self.lang,
            ui=ui,
            ui_json=json.dumps(ui, ensure_ascii=False),
            translations_json=json.dumps(translation_payload, ensure_ascii=False),
            project_name=str(context["project_name"]),
            generated_at=str(context["generated_at"]),
            run_mode_key=str(context["run_mode_key"]),
            run_mode_label=str(context["run_mode_label"]),
            total_functions=int(context["total_functions"]),
            total_edges=int(context["total_edges"]),
            db_function_count=int(context["db_function_count"]),
            readiness_index=int(context["readiness_index"]),
            coverage_percent=float(context["coverage_percent"]),
            tests_passed=int(context["tests_passed"]),
            tests_total=int(context["tests_total"]),
            sync_count=int(context["sync_count"]),
            async_count=int(context["async_count"]),
            stdout_log=str(context["stdout_log"] or ui["placeholders"]["stdout_missing"]),
            stderr_log=str(context["stderr_log"] or ui["placeholders"]["stderr_missing"]),
            graph_payload_json=json.dumps(context["graph_payload"], ensure_ascii=False),
            function_rows_json=json.dumps(context["function_rows"], ensure_ascii=False),
            import_rows_json=json.dumps(context["import_rows"], ensure_ascii=False),
            test_rows_json=json.dumps(context["test_rows"], ensure_ascii=False),
            failed_tests_json=json.dumps(context["failed_tests"], ensure_ascii=False),
            mock_rows_json=json.dumps(context["mock_rows"], ensure_ascii=False),
            coverage_rows_json=json.dumps(context["coverage_rows"], ensure_ascii=False),
            artifact_rows_json=json.dumps(context["artifacts"], ensure_ascii=False),
            scorecard_rows_json=json.dumps(context["scorecard"], ensure_ascii=False),
            dependency_depth_json=json.dumps(context["dependency_depth"], ensure_ascii=False),
            readiness_entries_json=json.dumps(context["readiness_entries"], ensure_ascii=False),
            heatmap_entries_json=json.dumps(context["heatmap_entries"], ensure_ascii=False),
            operation_rows_json=json.dumps(context["operation_rows"], ensure_ascii=False),
        )

    def _build_ui(self) -> dict[str, Any]:
        return self._build_ui_for(self.lang)

    def _build_ui_for(self, language: str) -> dict[str, Any]:
        normalized = normalize_language(language)
        graph_ui = {
            key: tr(normalized, f"report.graph_ui.{key}")
            for key in (
                "nav_overview",
                "nav_operations",
                "nav_graph",
                "nav_functions",
                "nav_tests",
                "nav_artifacts",
                "graph_title",
                "graph_note",
                "graph_collapse",
                "graph_expand",
                "graph_reset",
                "graph_details_title",
                "graph_details_note",
                "graph_details_empty",
                "graph_localized_name",
                "graph_description",
                "graph_module",
                "graph_mode",
                "graph_infra",
                "graph_mock",
                "graph_calls",
                "graph_code",
                "graph_hint",
                "graph_code_empty",
            )
        }

        return {
            "html_title": "speculast dashboard",
            "hero_tag": tr(normalized, "report.hero_tag"),
            "hero_title": "speculast",
            "hero_text": tr(normalized, "report.hero_text"),
            "hero_project": tr(normalized, "report.hero_project"),
            "hero_mode": tr(normalized, "report.hero_mode"),
            "hero_generated": tr(normalized, "report.hero_generated"),
            "hero_language": tr(normalized, "report.hero_language"),
            "hero_theme": tr(normalized, "report.hero_theme"),
            "theme_dark": tr(normalized, "report.theme_dark"),
            "theme_light": tr(normalized, "report.theme_light"),
            "lang_ru": tr(normalized, "shared.common.lang_ru"),
            "lang_en": tr(normalized, "shared.common.lang_en"),
            "metrics": {
                "functions_label": tr(normalized, "report.metrics.functions_label"),
                "functions_note": tr(normalized, "report.metrics.functions_note"),
                "functions_tooltip": tr(normalized, "report.metrics.functions_tooltip"),
                "edges_label": tr(normalized, "report.metrics.edges_label"),
                "edges_note": tr(normalized, "report.metrics.edges_note"),
                "edges_tooltip": tr(normalized, "report.metrics.edges_tooltip"),
                "db_label": tr(normalized, "report.metrics.db_label"),
                "db_note": tr(normalized, "report.metrics.db_note"),
                "db_tooltip": tr(normalized, "report.metrics.db_tooltip"),
                "readiness_label": tr(normalized, "report.metrics.readiness_label"),
                "readiness_note": tr(normalized, "report.metrics.readiness_note"),
                "readiness_tooltip": tr(normalized, "report.metrics.readiness_tooltip"),
                "coverage_label": tr(normalized, "report.metrics.coverage_label"),
                "coverage_note": tr(normalized, "report.metrics.coverage_note"),
                "coverage_tooltip": tr(normalized, "report.metrics.coverage_tooltip"),
                "tests_label": tr(normalized, "report.metrics.tests_label"),
                "tests_note": tr(normalized, "report.metrics.tests_note"),
                "tests_tooltip": tr(normalized, "report.metrics.tests_tooltip"),
            },
            "sections": {
                "operations_title": tr(normalized, "report.sections.operations_title"),
                "operations_note": tr(normalized, "report.sections.operations_note"),
                "scorecard_title": tr(normalized, "report.sections.scorecard_title"),
                "scorecard_note": tr(normalized, "report.sections.scorecard_note"),
                "dependency_depth_title": tr(normalized, "report.sections.dependency_depth_title"),
                "dependency_depth_note": tr(normalized, "report.sections.dependency_depth_note"),
                "async_balance_title": tr(normalized, "report.sections.async_balance_title"),
                "async_balance_note": tr(normalized, "report.sections.async_balance_note"),
                "infra_readiness_title": tr(normalized, "report.sections.infra_readiness_title"),
                "infra_readiness_note": tr(normalized, "report.sections.infra_readiness_note"),
                "heatmap_title": tr(normalized, "report.sections.heatmap_title"),
                "heatmap_note": tr(normalized, "report.sections.heatmap_note"),
                "services_title": tr(normalized, "report.sections.services_title"),
                "services_note": tr(normalized, "report.sections.services_note"),
                "functions_title": tr(normalized, "report.sections.functions_title"),
                "functions_note": tr(normalized, "report.sections.functions_note"),
                "imports_title": tr(normalized, "report.sections.imports_title"),
                "imports_note": tr(normalized, "report.sections.imports_note"),
                "mocks_title": tr(normalized, "report.sections.mocks_title"),
                "mocks_note": tr(normalized, "report.sections.mocks_note"),
                "tests_title": tr(normalized, "report.sections.tests_title"),
                "tests_note": tr(normalized, "report.sections.tests_note"),
                "coverage_title": tr(normalized, "report.sections.coverage_title"),
                "coverage_note": tr(normalized, "report.sections.coverage_note"),
                "artifacts_title": tr(normalized, "report.sections.artifacts_title"),
                "artifacts_note": tr(normalized, "report.sections.artifacts_note"),
                "logs_title": tr(normalized, "report.sections.logs_title"),
                "logs_note": tr(normalized, "report.sections.logs_note"),
                "graph_title": graph_ui["graph_title"],
                "graph_note": graph_ui["graph_note"],
            },
            "search": {
                "functions": tr(normalized, "report.search.functions"),
                "imports": tr(normalized, "report.search.imports"),
                "mocks": tr(normalized, "report.search.mocks"),
                "tests": tr(normalized, "report.search.tests"),
            },
            "filters": {
                "all_modes": tr(normalized, "report.filters.all_modes"),
                "sync_only": tr(normalized, "report.filters.sync_only"),
                "async_only": tr(normalized, "report.filters.async_only"),
                "all_strategies": tr(normalized, "report.filters.all_strategies"),
                "behavioral_only": tr(normalized, "report.filters.behavioral_only"),
                "integration_only": tr(normalized, "report.filters.integration_only"),
                "skipped_only": tr(normalized, "report.filters.skipped_only"),
                "all_outcomes": tr(normalized, "report.filters.all_outcomes"),
                "passed_only": tr(normalized, "report.filters.passed_only"),
                "failed_only": tr(normalized, "report.filters.failed_only"),
                "skipped_tests_only": tr(normalized, "report.filters.skipped_tests_only"),
                "infra_errors_only": tr(normalized, "report.filters.infra_errors_only"),
            },
            "tables": {
                "function": tr(normalized, "report.tables.function"),
                "module": tr(normalized, "report.tables.module"),
                "mode": tr(normalized, "report.tables.mode"),
                "infrastructure": tr(normalized, "report.tables.infrastructure"),
                "strategy": tr(normalized, "report.tables.strategy"),
                "calls": tr(normalized, "report.tables.calls"),
                "mocks_reality": tr(normalized, "report.tables.mocks_reality"),
                "skip_reason": tr(normalized, "report.tables.skip_reason"),
                "import": tr(normalized, "report.tables.import"),
                "root": tr(normalized, "report.tables.root"),
                "test": tr(normalized, "report.tables.test"),
                "outcome": tr(normalized, "report.tables.outcome"),
                "duration": tr(normalized, "report.tables.duration"),
                "message": tr(normalized, "report.tables.message"),
                "mocks": tr(normalized, "report.tables.mocks"),
                "file": tr(normalized, "report.tables.file"),
                "coverage": tr(normalized, "report.tables.coverage"),
                "covered": tr(normalized, "report.tables.covered"),
                "missing": tr(normalized, "report.tables.missing"),
                "statements": tr(normalized, "report.tables.statements"),
                "artifact": tr(normalized, "report.tables.artifact"),
                "status": tr(normalized, "report.tables.status"),
                "path": tr(normalized, "report.tables.path"),
                "used": tr(normalized, "report.tables.used"),
            },
            "placeholders": {
                "no_data": tr(normalized, "report.placeholders.no_data"),
                "no_failed_tests": tr(normalized, "report.placeholders.no_failed_tests"),
                "stdout_missing": tr(normalized, "report.placeholders.stdout_missing"),
                "stderr_missing": tr(normalized, "report.placeholders.stderr_missing"),
                "no_log_details": tr(normalized, "report.placeholders.no_log_details"),
            },
            "charts": {
                "dependency_dataset": tr(normalized, "report.charts.dependency_dataset"),
                "sync_label": tr(normalized, "report.charts.sync_label"),
                "async_label": tr(normalized, "report.charts.async_label"),
                "readiness_dataset": tr(normalized, "report.charts.readiness_dataset"),
            },
            "common": {
                "dash": tr(normalized, "shared.common.dash"),
                "weight": tr(normalized, "shared.common.weight"),
            },
            "servicePostgreSQL": tr(normalized, "shared.service_names.postgresql"),
            "graph": graph_ui,
        }

    @classmethod
    def _build_loader(cls, templates_path: Path | None) -> FileSystemLoader | DictLoader:
        if templates_path is not None:
            return FileSystemLoader(str(templates_path.resolve()))

        template_root = resources.files("engine.visualizer.templates")
        return DictLoader(
            {
                cls.TEMPLATE_NAME: template_root.joinpath(cls.TEMPLATE_NAME).read_text(
                    encoding="utf-8"
                )
            }
        )
