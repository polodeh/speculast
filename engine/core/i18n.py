"""Localization helpers for speculast."""

from __future__ import annotations

import locale
import warnings
from collections.abc import Mapping
from typing import Any, Final, Literal, cast

LanguageCode = Literal["ru", "en"]

I18N: Final[dict[LanguageCode, dict[str, Any]]] = {
    "en": {
        "cli": {
            "description": "Autonomous semantic-first generator of tests and reports for Python projects.",
            "path_help": "Path to a Python project root or to a single .py file.",
            "generate_only_help": "Analyze the project, generate tests, compose files and the HTML report without running pytest.",
            "run_all_help": "Run the full autonomous cycle: Docker up, analysis, generation, pytest, report, cleanup.",
            "visualize_help": "Build the visual HTML report without running pytest.",
            "real_db_help": "Force integration mode for DB-bound functions.",
            "lang_help": "Report and terminal language.",
        },
        "terminal": {
            "banner_subtitle": "Autonomous Lifecycle Mode",
            "errors": {
                "title": "Pipeline Failure",
                "unsupported_path": "Unable to analyze path: {path}",
                "no_files_found": "Files for analysis were not found. Write some code, and I will be back!",
                "missing_analysis": "The pipeline finished without an analysis result.",
                "docker_daemon_unavailable": "Docker daemon is unavailable. Start Docker before running the full cycle.",
                "docker_desktop_missing": "Docker Desktop was not found, automatic startup is unavailable.",
                "docker_daemon_timeout": "Docker daemon did not become ready in time.",
                "compose_up_failed": "docker compose up -d failed.",
                "containers_not_ready": "Containers did not become ready in time: {details}",
                "compose_down_failed": "docker compose down failed.",
                "pytest_suite_missing": "Unable to run pytest because the generated test suite is missing.",
            },
            "warnings": {
                "title": "Analysis warnings",
                "syntax_error": "Skipped {path} because of a syntax error on line {line}: {details}",
                "read_error": "Skipped {path} because the file could not be read: {details}",
            },
            "progress": {
                "initializing": "Initializing pipeline",
                "semantic_analysis": "Semantic project analysis",
                "generating_tests": "Generating test suite",
                "preparing_infra": "Preparing infrastructure files",
                "starting_docker": "Starting Docker environment",
                "running_tests": "Running generated tests",
                "building_report": "Building HTML report",
                "stopping_docker": "Stopping Docker environment",
            },
            "final": {
                "success_title": "Pipeline completed",
                "failure_title": "Pipeline completed with errors",
                "tests_not_run": "Tests were not executed.",
                "files_found": "Files analyzed: {count}.",
                "functions_covered": "Functions covered by the test plan: {covered}/{total}.",
                "tests_summary": "Tests: {passed}/{total} passed, errors: {errors}, skipped: {skipped}.",
                "mode": "Mode: {value}",
                "real_db": "Real DB: {value}",
                "real_db_enabled": "enabled",
                "real_db_disabled": "disabled",
                "infrastructure": "Infrastructure: {infra} (index {score}%)",
                "report": "HTML report: {path}",
            },
        },
        "shared": {
            "run_modes": {
                "generate_only": "Generate and report",
                "run_all": "Full autonomous cycle",
                "visualize": "Visual report",
                "default": "Analytical run",
            },
            "service_names": {
                "postgresql": "PostgreSQL",
                "redis": "Redis",
            },
            "module_names": {
                "models": "Models",
                "logic": "Logic",
                "service": "Service",
                "database": "Database",
            },
            "status_words": {
                "healthy": "healthy",
                "running": "running",
                "ready": "ready",
                "planned": "planned",
                "starting": "starting",
                "unavailable": "unavailable",
                "error": "error",
            },
            "function_modes": {
                "sync": "Synchronous",
                "async": "Asynchronous",
            },
            "test_modes": {
                "behavioral": "Behavioral",
                "integration": "Integration",
                "skipped": "Skipped",
            },
            "outcomes": {
                "passed": "Passed",
                "failed": "Failed",
                "skipped": "Skipped",
                "error": "Infrastructure error",
            },
            "infra": {
                "not_required": "Not required",
                "real_db": "Real database",
                "no_mocks": "None required",
            },
            "artifacts": {
                "pytest_suite": "Pytest suite",
                "docker_compose": "Docker Compose file",
                "html_report": "HTML report",
                "pytest_json": "Pytest JSON report",
                "coverage_json": "Coverage JSON report",
                "ready": "Ready",
                "not_created": "Not created",
            },
            "common": {
                "none": "None",
                "dash": "вЂ”",
                "weight": "priority",
                "utc_suffix": "UTC",
                "lang_ru": "RU",
                "lang_en": "EN",
            },
        },
        "report": {
            "html_title": "Architecture and Testing Analysis System",
            "hero_tag": "Project Analysis Dashboard",
            "hero_title": "Architecture and Testing Analysis System",
            "hero_text": (
                "An interface for monitoring code structure, test results, and infrastructure readiness."
            ),
            "hero_project": "Project",
            "hero_mode": "Mode",
            "hero_generated": "Generated",
            "hero_language": "Language",
            "hero_theme": "Theme",
            "theme_dark": "Dark",
            "theme_light": "Light",
            "metrics": {
                "functions_label": "Functions",
                "functions_note": "Total number of discovered functions and methods in the source code.",
                "functions_tooltip": "Total number of discovered functions and methods in the source code.",
                "edges_label": "Links",
                "edges_note": "Number of calls between functions and external libraries.",
                "edges_tooltip": "Number of calls between functions and external libraries.",
                "db_label": "DB nodes",
                "db_note": "Functions that interact with the database and require integration verification.",
                "db_tooltip": "Functions that interact with the database and require integration verification.",
                "readiness_label": "Readiness",
                "readiness_note": "Availability of required services such as the database or cache for running tests.",
                "readiness_tooltip": "Availability of required services such as the database or cache for running tests.",
                "coverage_label": "Coverage",
                "coverage_note": "Percentage of code lines executed during tests.",
                "coverage_tooltip": "Helps assess how completely the application logic was exercised.",
                "tests_label": "Tests",
                "tests_note": "Ratio of successfully passed scenarios to the total number of generated tests.",
                "tests_tooltip": "Ratio of successfully passed scenarios to the total number of generated tests.",
            },
            "sections": {
                "operations_title": "Analysis History",
                "operations_note": "A step-by-step record of project scanning, dependency analysis, test generation and report assembly.",
                "scorecard_title": "Key Maturity Indicators",
                "scorecard_note": "Core indicators that summarize the current state of architecture, tests and infrastructure.",
                "dependency_depth_title": "Dependency depth",
                "dependency_depth_note": "Functions with the densest external call graph.",
                "async_balance_title": "Sync / Async balance",
                "async_balance_note": "Ratio of synchronous and asynchronous execution points.",
                "infra_readiness_title": "Infrastructure readiness",
                "infra_readiness_note": "Current readiness of services required for a real execution flow.",
                "heatmap_title": "Infrastructure Load",
                "heatmap_note": "Components that create the highest load on real infrastructure during test execution.",
                "services_title": "Service state",
                "services_note": "Infrastructure state as reported by the engine.",
                "functions_title": "Function Registry",
                "functions_note": "Interactive table of functions, calls, execution mode and test strategy.",
                "imports_title": "External Dependencies",
                "imports_note": "Libraries and modules used in the project that may require isolation through mocks.",
                "mocks_title": "Mock insight",
                "mocks_note": "Shows what was mocked and what was redirected to a real infrastructure path.",
                "tests_title": "Test Results",
                "tests_note": "Status and diagnostic details for the generated test scenarios.",
                "coverage_title": "Coverage by file",
                "coverage_note": "Coverage table for all measured Python modules.",
                "artifacts_title": "Pipeline artifacts",
                "artifacts_note": "Files and reports produced during the last run.",
                "logs_title": "Technical Log (stdout/stderr)",
                "logs_note": "stdout/stderr data streams for diagnosing the analysis process.",
                "graph_title": "Dependency graph",
                "graph_note": "Interactive vector graph of relationships between functions and discovered external calls.",
            },
            "search": {
                "functions": "Search by function, module or call",
                "imports": "Search by import",
                "mocks": "Search by function or mock",
                "tests": "Search by test name or message",
            },
            "filters": {
                "all_modes": "All modes",
                "sync_only": "Sync only",
                "async_only": "Async only",
                "all_strategies": "All strategies",
                "behavioral_only": "Behavioral only",
                "integration_only": "Integration only",
                "skipped_only": "Skipped only",
                "all_outcomes": "All outcomes",
                "passed_only": "Passed only",
                "failed_only": "Failed only",
                "skipped_tests_only": "Skipped only",
                "infra_errors_only": "Infrastructure errors only",
            },
            "tables": {
                "function": "Function",
                "module": "Module",
                "mode": "Mode",
                "infrastructure": "Infrastructure",
                "strategy": "Strategy",
                "calls": "Calls",
                "mocks_reality": "Mocks / reality",
                "skip_reason": "Skip reason",
                "import": "Import",
                "root": "Root",
                "test": "Test",
                "outcome": "Outcome",
                "duration": "Duration, sec",
                "message": "Message",
                "mocks": "Mocks",
                "file": "File",
                "coverage": "Coverage",
                "covered": "Covered",
                "missing": "Missing",
                "statements": "Statements",
                "artifact": "Artifact",
                "status": "Status",
                "path": "Path",
                "used": "Used",
            },
            "placeholders": {
                "no_data": "No data available.",
                "no_failed_tests": "No failing tests were detected.",
                "stdout_missing": "stdout log is unavailable.",
                "stderr_missing": "stderr log is unavailable.",
                "no_functions": "No functions were detected",
                "no_log_details": "Detailed log is unavailable.",
            },
            "charts": {
                "dependency_dataset": "Link count",
                "sync_label": "Synchronous",
                "async_label": "Asynchronous",
                "readiness_dataset": "Readiness, %",
            },
            "scorecard": {
                "semantic_map": "Semantic map",
                "generation_strategy": "Generation strategy",
                "infrastructure_ready": "Infrastructure readiness",
                "execution_results": "Execution results",
                "autonomy_mode": "Autonomy mode",
            },
            "operations": {
                "step_01_title": "Initialize the analysis perimeter",
                "step_01_details": "Project {project_name} loaded. Run mode: {run_mode}.",
                "step_02_title": "Semantic source scanning",
                "step_02_details": "Files analyzed: {total_files}. Functions and methods detected: {total_functions}.",
                "step_03_title": "Import and call collection",
                "step_03_details": "Top-level imports collected: {import_count}. External links built: {total_edges}.",
                "step_04_title": "Infrastructure requirement assessment",
                "step_04_details": "Required services: {services}.",
                "step_05_title": "Test plan assembly",
                "step_05_details": "Prepared unit scenarios: {unit_count}. Integration scenarios: {integration_count}.",
                "step_06_executed_title": "Pytest execution",
                "step_06_executed_details": "Passed: {passed}/{total}. Errors: {errors}. Coverage: {coverage:.2f}%.",
                "step_06_skipped_title": "Test execution skipped",
                "step_06_skipped_details": "The selected report mode did not run pytest. Visualization was built from analytical data.",
                "step_07_title": "Final report assembly",
                "step_07_details": "The vector graph, tables, metrics and diagnostic blocks were assembled into one autonomous HTML file.",
            },
            "graph_ui": {
                "nav_overview": "Overview",
                "nav_operations": "History",
                "nav_graph": "Graph",
                "nav_functions": "Functions",
                "nav_tests": "Tests",
                "nav_artifacts": "Artifacts",
                "graph_title": "Interactive dependency graph",
                "graph_note": "Only high-level modules are visible by default. Click a module to expand its functions and external calls.",
                "graph_collapse": "Collapse all",
                "graph_expand": "Expand all",
                "graph_reset": "Reset view",
                "graph_details_title": "Node context",
                "graph_details_note": "Hover shows the localized name, while click pins the card with description, mocks and source preview.",
                "graph_details_empty": "Select a module, function or external call in the graph to inspect its localized context.",
                "graph_localized_name": "Localized name",
                "graph_description": "Description",
                "graph_module": "Module",
                "graph_mode": "Mode",
                "graph_infra": "Infrastructure",
                "graph_mock": "Mock insight",
                "graph_calls": "Links",
                "graph_code": "Code preview",
                "graph_hint": "Use the mouse wheel to zoom and drag to pan the scheme.",
                "graph_code_empty": "Source preview is unavailable for this node.",
            },
        },
    },
    "ru": {
        "cli": {
            "description": "РђРІС‚РѕРЅРѕРјРЅС‹Р№ semantic-first РіРµРЅРµСЂР°С‚РѕСЂ С‚РµСЃС‚РѕРІ Рё РѕС‚С‡С‘С‚РѕРІ РґР»СЏ Python-РїСЂРѕРµРєС‚РѕРІ.",
            "path_help": "РџСѓС‚СЊ Рє РєРѕСЂРЅСЋ Python-РїСЂРѕРµРєС‚Р° РёР»Рё Рє РѕС‚РґРµР»СЊРЅРѕРјСѓ .py С„Р°Р№Р»Сѓ.",
            "generate_only_help": "РџСЂРѕРІРµСЃС‚Рё Р°РЅР°Р»РёР·, СЃРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ С‚РµСЃС‚С‹, compose-С„Р°Р№Р»С‹ Рё HTML-РѕС‚С‡С‘С‚ Р±РµР· Р·Р°РїСѓСЃРєР° pytest.",
            "run_all_help": "Р—Р°РїСѓСЃС‚РёС‚СЊ РїРѕР»РЅС‹Р№ Р°РІС‚РѕРЅРѕРјРЅС‹Р№ С†РёРєР»: Docker up, Р°РЅР°Р»РёР·, РіРµРЅРµСЂР°С†РёСЏ, pytest, РѕС‚С‡С‘С‚, РѕС‡РёСЃС‚РєР°.",
            "visualize_help": "РЎРѕР±СЂР°С‚СЊ РІРёР·СѓР°Р»СЊРЅС‹Р№ HTML-РѕС‚С‡С‘С‚ Р±РµР· Р·Р°РїСѓСЃРєР° pytest.",
            "real_db_help": "РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ РІРєР»СЋС‡РёС‚СЊ РёРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹Р№ СЂРµР¶РёРј РґР»СЏ DB-bound С„СѓРЅРєС†РёР№.",
            "lang_help": "РЇР·С‹Рє С‚РµСЂРјРёРЅР°Р»Р° Рё РѕС‚С‡С‘С‚Р°.",
        },
        "terminal": {
            "banner_subtitle": "РђРІС‚РѕРЅРѕРјРЅС‹Р№ Р¶РёР·РЅРµРЅРЅС‹Р№ С†РёРєР»",
            "errors": {
                "title": "РЎР±РѕР№ РїР°Р№РїР»Р°Р№РЅР°",
                "unsupported_path": "РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕР°РЅР°Р»РёР·РёСЂРѕРІР°С‚СЊ РїСѓС‚СЊ: {path}",
                "no_files_found": "\u0424\u0430\u0439\u043b\u044b \u0434\u043b\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b. \u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u043a\u043e\u0434, \u0438 \u044f \u0432\u0435\u0440\u043d\u0443\u0441\u044c!",
                "missing_analysis": "РџР°Р№РїР»Р°Р№РЅ Р·Р°РІРµСЂС€РёР»СЃСЏ Р±РµР· СЂРµР·СѓР»СЊС‚Р°С‚Р° Р°РЅР°Р»РёР·Р°.",
                "docker_daemon_unavailable": "Docker daemon РЅРµРґРѕСЃС‚СѓРїРµРЅ. Р—Р°РїСѓСЃС‚РёС‚Рµ Docker РїРµСЂРµРґ РїРѕР»РЅС‹Рј С†РёРєР»РѕРј.",
                "docker_desktop_missing": "Docker Desktop РЅРµ РЅР°Р№РґРµРЅ, Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРёР№ Р·Р°РїСѓСЃРє РЅРµРґРѕСЃС‚СѓРїРµРЅ.",
                "docker_daemon_timeout": "Docker daemon РЅРµ СѓСЃРїРµР» РїРµСЂРµР№С‚Рё РІ РіРѕС‚РѕРІРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ.",
                "compose_up_failed": "РљРѕРјР°РЅРґР° docker compose up -d Р·Р°РІРµСЂС€РёР»Р°СЃСЊ РѕС€РёР±РєРѕР№.",
                "containers_not_ready": "РљРѕРЅС‚РµР№РЅРµСЂС‹ РЅРµ СѓСЃРїРµР»Рё РїРµСЂРµР№С‚Рё РІ РіРѕС‚РѕРІРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ: {details}",
                "compose_down_failed": "РљРѕРјР°РЅРґР° docker compose down Р·Р°РІРµСЂС€РёР»Р°СЃСЊ РѕС€РёР±РєРѕР№.",
                "pytest_suite_missing": "РќРµРІРѕР·РјРѕР¶РЅРѕ Р·Р°РїСѓСЃС‚РёС‚СЊ pytest: СЃРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ РЅР°Р±РѕСЂ С‚РµСЃС‚РѕРІ РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚.",
            },
            "warnings": {
                "title": "\u041f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430",
                "syntax_error": "\u0424\u0430\u0439\u043b {path} \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d: \u0441\u0438\u043d\u0442\u0430\u043a\u0441\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430 \u0432 \u0441\u0442\u0440\u043e\u043a\u0435 {line}: {details}",
                "read_error": "\u0424\u0430\u0439\u043b {path} \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d: \u043d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0442\u044c \u0444\u0430\u0439\u043b: {details}",
            },
            "progress": {
                "initializing": "РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РїР°Р№РїР»Р°Р№РЅР°",
                "semantic_analysis": "РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ Р°РЅР°Р»РёР· РїСЂРѕРµРєС‚Р°",
                "generating_tests": "Р“РµРЅРµСЂР°С†РёСЏ С‚РµСЃС‚РѕРІРѕРіРѕ РЅР°Р±РѕСЂР°",
                "preparing_infra": "РџРѕРґРіРѕС‚РѕРІРєР° РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂРЅС‹С… С„Р°Р№Р»РѕРІ",
                "starting_docker": "РџРѕРґСЉС‘Рј Docker-РѕРєСЂСѓР¶РµРЅРёСЏ",
                "running_tests": "РџСЂРѕРіРѕРЅ СЃРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹С… С‚РµСЃС‚РѕРІ",
                "building_report": "РЎР±РѕСЂРєР° HTML-РѕС‚С‡С‘С‚Р°",
                "stopping_docker": "РћСЃС‚Р°РЅРѕРІРєР° Docker-РѕРєСЂСѓР¶РµРЅРёСЏ",
            },
            "final": {
                "success_title": "РџР°Р№РїР»Р°Р№РЅ Р·Р°РІРµСЂС€С‘РЅ",
                "failure_title": "РџР°Р№РїР»Р°Р№РЅ Р·Р°РІРµСЂС€С‘РЅ СЃ РѕС€РёР±РєР°РјРё",
                "tests_not_run": "РўРµСЃС‚С‹ РЅРµ Р·Р°РїСѓСЃРєР°Р»РёСЃСЊ.",
                "files_found": "\u0424\u0430\u0439\u043b\u043e\u0432 \u043d\u0430\u0439\u0434\u0435\u043d\u043e: {count}.",
                "functions_covered": "\u0424\u0443\u043d\u043a\u0446\u0438\u0439 \u0432 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u043c \u043f\u043b\u0430\u043d\u0435: {covered}/{total}.",
                "tests_summary": "РўРµСЃС‚С‹: {passed}/{total} СѓСЃРїРµС€РЅС‹, РѕС€РёР±РѕРє: {errors}, РїСЂРѕРїСѓСЃРєРѕРІ: {skipped}.",
                "mode": "Р РµР¶РёРј: {value}",
                "real_db": "Р РµР°Р»СЊРЅР°СЏ Р‘Р”: {value}",
                "real_db_enabled": "РІРєР»СЋС‡РµРЅР°",
                "real_db_disabled": "РІС‹РєР»СЋС‡РµРЅР°",
                "infrastructure": "РРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂР°: {infra} (РёРЅРґРµРєСЃ {score}%)",
                "report": "HTML-РѕС‚С‡С‘С‚: {path}",
            },
        },
        "shared": {
            "run_modes": {
                "generate_only": "Р“РµРЅРµСЂР°С†РёСЏ Рё РѕС‚С‡С‘С‚",
                "run_all": "РџРѕР»РЅС‹Р№ Р°РІС‚РѕРЅРѕРјРЅС‹Р№ С†РёРєР»",
                "visualize": "Р’РёР·СѓР°Р»СЊРЅС‹Р№ РѕС‚С‡С‘С‚",
                "default": "РђРЅР°Р»РёС‚РёС‡РµСЃРєРёР№ Р·Р°РїСѓСЃРє",
            },
            "service_names": {
                "postgresql": "PostgreSQL",
                "redis": "Redis",
            },
            "module_names": {
                "models": "РњРѕРґРµР»Рё",
                "logic": "Р›РѕРіРёРєР°",
                "service": "РЎРµСЂРІРёСЃ",
                "database": "Р‘Р°Р·Р° РґР°РЅРЅС‹С…",
            },
            "status_words": {
                "healthy": "РёСЃРїСЂР°РІРµРЅ",
                "running": "Р·Р°РїСѓС‰РµРЅ",
                "ready": "РіРѕС‚РѕРІ",
                "planned": "Р·Р°РїР»Р°РЅРёСЂРѕРІР°РЅ",
                "starting": "Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ",
                "unavailable": "РЅРµРґРѕСЃС‚СѓРїРµРЅ",
                "error": "РѕС€РёР±РєР°",
            },
            "function_modes": {
                "sync": "РЎРёРЅС…СЂРѕРЅРЅР°СЏ",
                "async": "РђСЃРёРЅС…СЂРѕРЅРЅР°СЏ",
            },
            "test_modes": {
                "behavioral": "РџРѕРІРµРґРµРЅС‡РµСЃРєРёР№",
                "integration": "РРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹Р№",
                "skipped": "РџСЂРѕРїСѓСЃРє",
            },
            "outcomes": {
                "passed": "РЈСЃРїРµС…",
                "failed": "РћС€РёР±РєР°",
                "skipped": "РџСЂРѕРїСѓСЃРє",
                "error": "РћС€РёР±РєР° РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂС‹",
            },
            "infra": {
                "not_required": "РќРµ С‚СЂРµР±СѓРµС‚СЃСЏ",
                "real_db": "Р РµР°Р»СЊРЅР°СЏ Р‘Р”",
                "no_mocks": "РќРµ С‚СЂРµР±СѓСЋС‚СЃСЏ",
            },
            "artifacts": {
                "pytest_suite": "РќР°Р±РѕСЂ pytest",
                "docker_compose": "Р¤Р°Р№Р» Docker Compose",
                "html_report": "HTML-РѕС‚С‡С‘С‚",
                "pytest_json": "JSON-РѕС‚С‡С‘С‚ pytest",
                "coverage_json": "JSON-РѕС‚С‡С‘С‚ coverage",
                "ready": "Р“РѕС‚РѕРІРѕ",
                "not_created": "РќРµ СЃРѕР·РґР°РЅРѕ",
            },
            "common": {
                "none": "РќРµС‚",
                "dash": "вЂ”",
                "weight": "РїСЂРёРѕСЂРёС‚РµС‚",
                "utc_suffix": "UTC",
                "lang_ru": "RU",
                "lang_en": "EN",
            },
        },
        "report": {
            "html_title": "РЎРёСЃС‚РµРјР° Р°РЅР°Р»РёР·Р° Р°СЂС…РёС‚РµРєС‚СѓСЂС‹ Рё С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ",
            "hero_tag": "РџР°РЅРµР»СЊ Р°РЅР°Р»РёР·Р° РїСЂРѕРµРєС‚Р°",
            "hero_title": "РЎРёСЃС‚РµРјР° Р°РЅР°Р»РёР·Р° Р°СЂС…РёС‚РµРєС‚СѓСЂС‹ Рё С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ",
            "hero_text": (
                "РРЅС‚РµСЂС„РµР№СЃ РґР»СЏ РјРѕРЅРёС‚РѕСЂРёРЅРіР° СЃС‚СЂСѓРєС‚СѓСЂС‹ РєРѕРґР°, СЂРµР·СѓР»СЊС‚Р°С‚РѕРІ С‚РµСЃС‚РѕРІ Рё РіРѕС‚РѕРІРЅРѕСЃС‚Рё РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂС‹."
            ),
            "hero_project": "РџСЂРѕРµРєС‚",
            "hero_mode": "Р РµР¶РёРј",
            "hero_generated": "РЎС„РѕСЂРјРёСЂРѕРІР°РЅРѕ",
            "hero_language": "РЇР·С‹Рє",
            "hero_theme": "РўРµРјР°",
            "theme_dark": "РўС‘РјРЅР°СЏ",
            "theme_light": "РЎРІРµС‚Р»Р°СЏ",
            "metrics": {
                "functions_label": "Р¤СѓРЅРєС†РёРё",
                "functions_note": "РћР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РѕР±РЅР°СЂСѓР¶РµРЅРЅС‹С… С„СѓРЅРєС†РёР№ Рё РјРµС‚РѕРґРѕРІ РІ РёСЃС…РѕРґРЅРѕРј РєРѕРґРµ.",
                "functions_tooltip": "РћР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РѕР±РЅР°СЂСѓР¶РµРЅРЅС‹С… С„СѓРЅРєС†РёР№ Рё РјРµС‚РѕРґРѕРІ РІ РёСЃС…РѕРґРЅРѕРј РєРѕРґРµ.",
                "edges_label": "РЎРІСЏР·Рё",
                "edges_note": "РљРѕР»РёС‡РµСЃС‚РІРѕ РІС‹Р·РѕРІРѕРІ РјРµР¶РґСѓ С„СѓРЅРєС†РёСЏРјРё Рё РІРЅРµС€РЅРёРјРё Р±РёР±Р»РёРѕС‚РµРєР°РјРё.",
                "edges_tooltip": "РљРѕР»РёС‡РµСЃС‚РІРѕ РІС‹Р·РѕРІРѕРІ РјРµР¶РґСѓ С„СѓРЅРєС†РёСЏРјРё Рё РІРЅРµС€РЅРёРјРё Р±РёР±Р»РёРѕС‚РµРєР°РјРё.",
                "db_label": "DB-СѓР·Р»С‹",
                "db_note": "Р¤СѓРЅРєС†РёРё, РІР·Р°РёРјРѕРґРµР№СЃС‚РІСѓСЋС‰РёРµ СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С… Рё С‚СЂРµР±СѓСЋС‰РёРµ РёРЅС‚РµРіСЂР°С†РёРѕРЅРЅРѕР№ РїСЂРѕРІРµСЂРєРё.",
                "db_tooltip": "Р¤СѓРЅРєС†РёРё, РІР·Р°РёРјРѕРґРµР№СЃС‚РІСѓСЋС‰РёРµ СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С… Рё С‚СЂРµР±СѓСЋС‰РёРµ РёРЅС‚РµРіСЂР°С†РёРѕРЅРЅРѕР№ РїСЂРѕРІРµСЂРєРё.",
                "readiness_label": "Р“РѕС‚РѕРІРЅРѕСЃС‚СЊ",
                "readiness_note": "РџРѕРєР°Р·Р°С‚РµР»СЊ РґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё РЅРµРѕР±С…РѕРґРёРјС‹С… СЃРµСЂРІРёСЃРѕРІ (Р‘Р”, РєСЌС€) РґР»СЏ Р·Р°РїСѓСЃРєР° С‚РµСЃС‚РѕРІ.",
                "readiness_tooltip": "РџРѕРєР°Р·Р°С‚РµР»СЊ РґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё РЅРµРѕР±С…РѕРґРёРјС‹С… СЃРµСЂРІРёСЃРѕРІ (Р‘Р”, РєСЌС€) РґР»СЏ Р·Р°РїСѓСЃРєР° С‚РµСЃС‚РѕРІ.",
                "coverage_label": "РџРѕРєСЂС‹С‚РёРµ",
                "coverage_note": "РџСЂРѕС†РµРЅС‚ СЃС‚СЂРѕРє РєРѕРґР°, РІС‹РїРѕР»РЅРµРЅРЅС‹С… РІРѕ РІСЂРµРјСЏ С‚РµСЃС‚РѕРІ.",
                "coverage_tooltip": "РџРѕР·РІРѕР»СЏРµС‚ РѕС†РµРЅРёС‚СЊ РїРѕР»РЅРѕС‚Сѓ РїСЂРѕРІРµСЂРєРё Р»РѕРіРёРєРё.",
                "tests_label": "РўРµСЃС‚С‹",
                "tests_note": "РЎРѕРѕС‚РЅРѕС€РµРЅРёРµ СѓСЃРїРµС€РЅРѕ РїСЂРѕР№РґРµРЅРЅС‹С… СЃС†РµРЅР°СЂРёРµРІ Рє РѕР±С‰РµРјСѓ РѕР±СЉС‘РјСѓ СЃРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹С… С‚РµСЃС‚РѕРІ.",
                "tests_tooltip": "РЎРѕРѕС‚РЅРѕС€РµРЅРёРµ СѓСЃРїРµС€РЅРѕ РїСЂРѕР№РґРµРЅРЅС‹С… СЃС†РµРЅР°СЂРёРµРІ Рє РѕР±С‰РµРјСѓ РѕР±СЉС‘РјСѓ СЃРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹С… С‚РµСЃС‚РѕРІ.",
            },
            "sections": {
                "operations_title": "РСЃС‚РѕСЂРёСЏ Р°РЅР°Р»РёР·Р°",
                "operations_note": "РџРѕС€Р°РіРѕРІР°СЏ РёСЃС‚РѕСЂРёСЏ СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ РїСЂРѕРµРєС‚Р°, Р°РЅР°Р»РёР·Р° Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№, РіРµРЅРµСЂР°С†РёРё С‚РµСЃС‚РѕРІ Рё СЃР±РѕСЂРєРё РѕС‚С‡С‘С‚Р°.",
                "scorecard_title": "РљР»СЋС‡РµРІС‹Рµ РїРѕРєР°Р·Р°С‚РµР»Рё Р·СЂРµР»РѕСЃС‚Рё",
                "scorecard_note": "РЎРІРѕРґРЅС‹Рµ РїРѕРєР°Р·Р°С‚РµР»Рё, РѕС‚СЂР°Р¶Р°СЋС‰РёРµ С‚РµРєСѓС‰РµРµ СЃРѕСЃС‚РѕСЏРЅРёРµ Р°СЂС…РёС‚РµРєС‚СѓСЂС‹, С‚РµСЃС‚РѕРІ Рё РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂС‹.",
                "dependency_depth_title": "Р“Р»СѓР±РёРЅР° Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№",
                "dependency_depth_note": "Р¤СѓРЅРєС†РёРё СЃ СЃР°РјС‹Рј РїР»РѕС‚РЅС‹Рј РіСЂР°С„РѕРј РІРЅРµС€РЅРёС… РІС‹Р·РѕРІРѕРІ.",
                "async_balance_title": "Р‘Р°Р»Р°РЅСЃ Sync / Async",
                "async_balance_note": "РЎРѕРѕС‚РЅРѕС€РµРЅРёРµ СЃРёРЅС…СЂРѕРЅРЅС‹С… Рё Р°СЃРёРЅС…СЂРѕРЅРЅС‹С… С‚РѕС‡РµРє РёСЃРїРѕР»РЅРµРЅРёСЏ.",
                "infra_readiness_title": "Р“РѕС‚РѕРІРЅРѕСЃС‚СЊ РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂС‹",
                "infra_readiness_note": "РўРµРєСѓС‰Р°СЏ РіРѕС‚РѕРІРЅРѕСЃС‚СЊ СЃРµСЂРІРёСЃРѕРІ, РЅСѓР¶РЅС‹С… РґР»СЏ СЂРµР°Р»СЊРЅРѕРіРѕ СЃС†РµРЅР°СЂРёСЏ.",
                "heatmap_title": "РќР°РіСЂСѓР·РєР° РЅР° РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂСѓ",
                "heatmap_note": "РљРѕРјРїРѕРЅРµРЅС‚С‹, РєРѕС‚РѕСЂС‹Рµ СЃРѕР·РґР°СЋС‚ РЅР°РёР±РѕР»СЊС€СѓСЋ РЅР°РіСЂСѓР·РєСѓ РЅР° СЂРµР°Р»СЊРЅСѓСЋ РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂСѓ РїСЂРё РІС‹РїРѕР»РЅРµРЅРёРё С‚РµСЃС‚РѕРІ.",
                "services_title": "РЎРѕСЃС‚РѕСЏРЅРёРµ СЃРµСЂРІРёСЃРѕРІ",
                "services_note": "РЎРѕСЃС‚РѕСЏРЅРёРµ РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂС‹ РїРѕ РґР°РЅРЅС‹Рј РґРІРёР¶РєР°.",
                "functions_title": "Р РµРµСЃС‚СЂ С„СѓРЅРєС†РёР№",
                "functions_note": "РРЅС‚РµСЂР°РєС‚РёРІРЅР°СЏ С‚Р°Р±Р»РёС†Р° С„СѓРЅРєС†РёР№, РІС‹Р·РѕРІРѕРІ, СЂРµР¶РёРјР° СЂР°Р±РѕС‚С‹ Рё СЃС‚СЂР°С‚РµРіРёРё С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ.",
                "imports_title": "Р’РЅРµС€РЅРёРµ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё",
                "imports_note": "Р‘РёР±Р»РёРѕС‚РµРєРё Рё РјРѕРґСѓР»Рё, РёСЃРїРѕР»СЊР·СѓРµРјС‹Рµ РІ РїСЂРѕРµРєС‚Рµ Рё С‚СЂРµР±СѓСЋС‰РёРµ РёР·РѕР»СЏС†РёРё (РјРѕРєРѕРІ).",
                "mocks_title": "РљР°СЂС‚Р° РјРѕРєРѕРІ",
                "mocks_note": "РџРѕРєР°Р·С‹РІР°РµС‚, С‡С‚Рѕ Р±С‹Р»Рѕ Р·Р°РјРѕРєР°РЅРѕ, Р° С‡С‚Рѕ СѓС€Р»Рѕ РІ СЂРµР°Р»СЊРЅСѓСЋ РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂСѓ.",
                "tests_title": "Р РµР·СѓР»СЊС‚Р°С‚С‹ С‚РµСЃС‚РѕРІ",
                "tests_note": "РЎС‚Р°С‚СѓСЃС‹ Рё РґРёР°РіРЅРѕСЃС‚РёС‡РµСЃРєРёРµ РґРµС‚Р°Р»Рё РїРѕ СЃРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Рј С‚РµСЃС‚РѕРІС‹Рј СЃС†РµРЅР°СЂРёСЏРј.",
                "coverage_title": "РџРѕРєСЂС‹С‚РёРµ РїРѕ С„Р°Р№Р»Р°Рј",
                "coverage_note": "РўР°Р±Р»РёС†Р° coverage РїРѕ РІСЃРµРј РёР·РјРµСЂРµРЅРЅС‹Рј Python-РјРѕРґСѓР»СЏРј.",
                "artifacts_title": "РђСЂС‚РµС„Р°РєС‚С‹ РєРѕРЅС‚СѓСЂР°",
                "artifacts_note": "РљР°РєРёРµ С„Р°Р№Р»С‹ Рё РѕС‚С‡С‘С‚С‹ Р±С‹Р»Рё СЃС„РѕСЂРјРёСЂРѕРІР°РЅС‹ РІ РїРѕСЃР»РµРґРЅРµРј Р·Р°РїСѓСЃРєРµ.",
                "logs_title": "РўРµС…РЅРёС‡РµСЃРєРёР№ Р»РѕРі (stdout/stderr)",
                "logs_note": "РџРѕС‚РѕРєРё РґР°РЅРЅС‹С… stdout/stderr РґР»СЏ РґРёР°РіРЅРѕСЃС‚РёРєРё РїСЂРѕС†РµСЃСЃР° Р°РЅР°Р»РёР·Р°.",
                "graph_title": "Р“СЂР°С„ Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№",
                "graph_note": "РРЅС‚РµСЂР°РєС‚РёРІРЅС‹Р№ РІРµРєС‚РѕСЂРЅС‹Р№ РіСЂР°С„ СЃРІСЏР·РµР№ РјРµР¶РґСѓ С„СѓРЅРєС†РёСЏРјРё Рё РѕР±РЅР°СЂСѓР¶РµРЅРЅС‹РјРё РІРЅРµС€РЅРёРјРё РІС‹Р·РѕРІР°РјРё.",
            },
            "search": {
                "functions": "РџРѕРёСЃРє РїРѕ С„СѓРЅРєС†РёРё, РјРѕРґСѓР»СЋ РёР»Рё РІС‹Р·РѕРІСѓ",
                "imports": "РџРѕРёСЃРє РїРѕ РёРјРїРѕСЂС‚Сѓ",
                "mocks": "РџРѕРёСЃРє РїРѕ С„СѓРЅРєС†РёРё РёР»Рё РјРѕРєСѓ",
                "tests": "РџРѕРёСЃРє РїРѕ РёРјРµРЅРё С‚РµСЃС‚Р° РёР»Рё СЃРѕРѕР±С‰РµРЅРёСЋ",
            },
            "filters": {
                "all_modes": "Р’СЃРµ СЂРµР¶РёРјС‹",
                "sync_only": "РўРѕР»СЊРєРѕ СЃРёРЅС…СЂРѕРЅРЅС‹Рµ",
                "async_only": "РўРѕР»СЊРєРѕ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Рµ",
                "all_strategies": "Р’СЃРµ СЃС‚СЂР°С‚РµРіРёРё",
                "behavioral_only": "РўРѕР»СЊРєРѕ РїРѕРІРµРґРµРЅС‡РµСЃРєРёРµ",
                "integration_only": "РўРѕР»СЊРєРѕ РёРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹Рµ",
                "skipped_only": "РўРѕР»СЊРєРѕ РїСЂРѕРїСѓС‰РµРЅРЅС‹Рµ",
                "all_outcomes": "Р’СЃРµ РёСЃС…РѕРґС‹",
                "passed_only": "РўРѕР»СЊРєРѕ СѓСЃРїРµС…",
                "failed_only": "РўРѕР»СЊРєРѕ РѕС€РёР±РєРё",
                "skipped_tests_only": "РўРѕР»СЊРєРѕ РїСЂРѕРїСѓСЃРєРё",
                "infra_errors_only": "РўРѕР»СЊРєРѕ РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂРЅС‹Рµ РѕС€РёР±РєРё",
            },
            "tables": {
                "function": "Р¤СѓРЅРєС†РёСЏ",
                "module": "РњРѕРґСѓР»СЊ",
                "mode": "Р РµР¶РёРј",
                "infrastructure": "РРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂР°",
                "strategy": "РЎС‚СЂР°С‚РµРіРёСЏ",
                "calls": "Р’С‹Р·РѕРІС‹",
                "mocks_reality": "РњРѕРєРё / СЂРµР°Р»СЊРЅРѕСЃС‚СЊ",
                "skip_reason": "РџСЂРёС‡РёРЅР° РїСЂРѕРїСѓСЃРєР°",
                "import": "РРјРїРѕСЂС‚",
                "root": "РљРѕСЂРµРЅСЊ",
                "test": "РўРµСЃС‚",
                "outcome": "РСЃС…РѕРґ",
                "duration": "Р’СЂРµРјСЏ, СЃРµРє",
                "message": "РЎРѕРѕР±С‰РµРЅРёРµ",
                "mocks": "РњРѕРєРё",
                "file": "Р¤Р°Р№Р»",
                "coverage": "РџРѕРєСЂС‹С‚РёРµ",
                "covered": "РџРѕРєСЂС‹С‚Рѕ",
                "missing": "РџСЂРѕРїСѓС‰РµРЅРѕ",
                "statements": "РћРїРµСЂР°С‚РѕСЂРѕРІ",
                "artifact": "РђСЂС‚РµС„Р°РєС‚",
                "status": "РЎС‚Р°С‚СѓСЃ",
                "path": "РџСѓС‚СЊ",
                "used": "Р§С‚Рѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅРѕ",
            },
            "placeholders": {
                "no_data": "Р”Р°РЅРЅС‹Рµ РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚.",
                "no_failed_tests": "РџР°РґР°СЋС‰РёС… С‚РµСЃС‚РѕРІ РЅРµ РѕР±РЅР°СЂСѓР¶РµРЅРѕ.",
                "stdout_missing": "Р›РѕРі stdout РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚.",
                "stderr_missing": "Р›РѕРі stderr РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚.",
                "no_functions": "Р¤СѓРЅРєС†РёРё РЅРµ РѕР±РЅР°СЂСѓР¶РµРЅС‹",
                "no_log_details": "РџРѕРґСЂРѕР±РЅС‹Р№ Р»РѕРі РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚.",
            },
            "charts": {
                "dependency_dataset": "РљРѕР»РёС‡РµСЃС‚РІРѕ СЃРІСЏР·РµР№",
                "sync_label": "РЎРёРЅС…СЂРѕРЅРЅС‹Рµ",
                "async_label": "РђСЃРёРЅС…СЂРѕРЅРЅС‹Рµ",
                "readiness_dataset": "Р“РѕС‚РѕРІРЅРѕСЃС‚СЊ, %",
            },
            "scorecard": {
                "semantic_map": "РЎРµРјР°РЅС‚РёС‡РµСЃРєР°СЏ РєР°СЂС‚Р°",
                "generation_strategy": "РЎС‚СЂР°С‚РµРіРёСЏ РіРµРЅРµСЂР°С†РёРё",
                "infrastructure_ready": "РРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂРЅР°СЏ РіРѕС‚РѕРІРЅРѕСЃС‚СЊ",
                "execution_results": "Р РµР·СѓР»СЊС‚Р°С‚С‹ РїСЂРѕРіРѕРЅР°",
                "autonomy_mode": "Р РµР¶РёРј Р°РІС‚РѕРЅРѕРјРЅРѕСЃС‚Рё",
            },
            "operations": {
                "step_01_title": "РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РєРѕРЅС‚СѓСЂР° Р°РЅР°Р»РёР·Р°",
                "step_01_details": "РџСЂРѕРµРєС‚ {project_name} Р·Р°РіСЂСѓР¶РµРЅ. Р РµР¶РёРј Р·Р°РїСѓСЃРєР°: {run_mode}.",
                "step_02_title": "РЎРµРјР°РЅС‚РёС‡РµСЃРєРѕРµ СЃРєР°РЅРёСЂРѕРІР°РЅРёРµ РёСЃС…РѕРґРЅРёРєРѕРІ",
                "step_02_details": "РџСЂРѕР°РЅР°Р»РёР·РёСЂРѕРІР°РЅРѕ С„Р°Р№Р»РѕРІ: {total_files}. Р’С‹СЏРІР»РµРЅРѕ С„СѓРЅРєС†РёР№ Рё РјРµС‚РѕРґРѕРІ: {total_functions}.",
                "step_03_title": "РЎР±РѕСЂ РёРјРїРѕСЂС‚РѕРІ Рё РІС‹Р·РѕРІРѕРІ",
                "step_03_details": "РЎРѕР±СЂР°РЅРѕ РёРјРїРѕСЂС‚РѕРІ РІРµСЂС…РЅРµРіРѕ СѓСЂРѕРІРЅСЏ: {import_count}. РџРѕСЃС‚СЂРѕРµРЅРѕ РІРЅРµС€РЅРёС… СЃРІСЏР·РµР№: {total_edges}.",
                "step_04_title": "РћС†РµРЅРєР° РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂРЅС‹С… С‚СЂРµР±РѕРІР°РЅРёР№",
                "step_04_details": "РўСЂРµР±СѓРµРјС‹Рµ СЃРµСЂРІРёСЃС‹: {services}.",
                "step_05_title": "Р¤РѕСЂРјРёСЂРѕРІР°РЅРёРµ С‚РµСЃС‚РѕРІРѕРіРѕ РїР»Р°РЅР°",
                "step_05_details": "РџРѕРґРіРѕС‚РѕРІР»РµРЅРѕ unit-СЃС†РµРЅР°СЂРёРµРІ: {unit_count}. РРЅС‚РµРіСЂР°С†РёРѕРЅРЅС‹С… СЃС†РµРЅР°СЂРёРµРІ: {integration_count}.",
                "step_06_executed_title": "Р¤Р°РєС‚РёС‡РµСЃРєРёР№ РїСЂРѕРіРѕРЅ pytest",
                "step_06_executed_details": "РЈСЃРїРµС€РЅРѕ: {passed}/{total}. РћС€РёР±РѕРє: {errors}. РџРѕРєСЂС‹С‚РёРµ: {coverage:.2f}%.",
                "step_06_skipped_title": "Р’С‹РїРѕР»РЅРµРЅРёРµ С‚РµСЃС‚РѕРІ РїСЂРѕРїСѓС‰РµРЅРѕ",
                "step_06_skipped_details": "Р’С‹Р±СЂР°РЅРЅС‹Р№ СЂРµР¶РёРј РѕС‚С‡С‘С‚Р° РЅРµ Р·Р°РїСѓСЃРєР°Р» pytest. Р’РёР·СѓР°Р»РёР·Р°С†РёСЏ СЃРѕР±СЂР°РЅР° РїРѕ Р°РЅР°Р»РёС‚РёС‡РµСЃРєРёРј РґР°РЅРЅС‹Рј.",
                "step_07_title": "РЎР±РѕСЂРєР° РёС‚РѕРіРѕРІРѕРіРѕ РІРёР·СѓР°Р»СЊРЅРѕРіРѕ РѕС‚С‡С‘С‚Р°",
                "step_07_details": "Р’РµРєС‚РѕСЂРЅС‹Р№ РіСЂР°С„, С‚Р°Р±Р»РёС†С‹, РјРµС‚СЂРёРєРё Рё РґРёР°РіРЅРѕСЃС‚РёС‡РµСЃРєРёРµ Р±Р»РѕРєРё СЃРѕР±СЂР°РЅС‹ РІ РѕРґРёРЅ Р°РІС‚РѕРЅРѕРјРЅС‹Р№ HTML-С„Р°Р№Р».",
            },
            "graph_ui": {
                "nav_overview": "РћР±Р·РѕСЂ",
                "nav_operations": "РСЃС‚РѕСЂРёСЏ",
                "nav_graph": "Р“СЂР°С„",
                "nav_functions": "Р¤СѓРЅРєС†РёРё",
                "nav_tests": "РўРµСЃС‚С‹",
                "nav_artifacts": "РђСЂС‚РµС„Р°РєС‚С‹",
                "graph_title": "РРЅС‚РµСЂР°РєС‚РёРІРЅС‹Р№ РіСЂР°С„ СЃРІСЏР·РµР№",
                "graph_note": "РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ РїРѕРєР°Р·Р°РЅС‹ С‚РѕР»СЊРєРѕ РІС‹СЃРѕРєРѕСѓСЂРѕРІРЅРµРІС‹Рµ РјРѕРґСѓР»Рё. РќР°Р¶РјРёС‚Рµ РЅР° РјРѕРґСѓР»СЊ, С‡С‚РѕР±С‹ СЂР°Р·РІРµСЂРЅСѓС‚СЊ РµРіРѕ С„СѓРЅРєС†РёРё Рё РІРЅРµС€РЅРёРµ РІС‹Р·РѕРІС‹.",
                "graph_collapse": "РЎРІРµСЂРЅСѓС‚СЊ РІСЃРµ",
                "graph_expand": "Р Р°Р·РІРµСЂРЅСѓС‚СЊ РІСЃРµ",
                "graph_reset": "РЎР±СЂРѕСЃ РІРёРґР°",
                "graph_details_title": "РљРѕРЅС‚РµРєСЃС‚ СѓР·Р»Р°",
                "graph_details_note": "РќР°РІРµРґРµРЅРёРµ РїРѕРєР°Р·С‹РІР°РµС‚ Р»РѕРєР°Р»РёР·РѕРІР°РЅРЅРѕРµ РёРјСЏ, Р° РєР»РёРє С„РёРєСЃРёСЂСѓРµС‚ РєР°СЂС‚РѕС‡РєСѓ СЃ СЂР°СЃС€РёС„СЂРѕРІРєРѕР№, РјРѕРєР°РјРё Рё С„СЂР°РіРјРµРЅС‚РѕРј РєРѕРґР°.",
                "graph_details_empty": "Р’С‹Р±РµСЂРёС‚Рµ РјРѕРґСѓР»СЊ, С„СѓРЅРєС†РёСЋ РёР»Рё РІРЅРµС€РЅРёР№ РІС‹Р·РѕРІ РІ РіСЂР°С„Рµ, С‡С‚РѕР±С‹ СѓРІРёРґРµС‚СЊ Р»РѕРєР°Р»РёР·РѕРІР°РЅРЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚.",
                "graph_localized_name": "Р›РѕРєР°Р»РёР·РѕРІР°РЅРЅРѕРµ РёРјСЏ",
                "graph_description": "РћРїРёСЃР°РЅРёРµ",
                "graph_module": "РњРѕРґСѓР»СЊ",
                "graph_mode": "Р РµР¶РёРј",
                "graph_infra": "РРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂР°",
                "graph_mock": "РљР°СЂС‚Р° РјРѕРєРѕРІ",
                "graph_calls": "РЎРІСЏР·Рё",
                "graph_code": "РљРѕРґРѕРІС‹Р№ С„СЂР°РіРјРµРЅС‚",
                "graph_hint": "РљРѕР»РµСЃРѕ РјС‹С€Рё РјР°СЃС€С‚Р°Р±РёСЂСѓРµС‚, РїРµСЂРµС‚Р°СЃРєРёРІР°РЅРёРµ РґРІРёРіР°РµС‚ СЃС…РµРјСѓ.",
                "graph_code_empty": "Р”Р»СЏ СЌС‚РѕРіРѕ СѓР·Р»Р° РЅРµС‚ РґРѕСЃС‚СѓРїРЅРѕРіРѕ С„СЂР°РіРјРµРЅС‚Р° РёСЃС…РѕРґРЅРѕРіРѕ РєРѕРґР°.",
            },
        },
    },
}


MOJIBAKE_HINT_CHARS: Final[frozenset[str]] = frozenset("ЂЃЉЊЋЏђѓєѕіїјљњћќЎўџҐґЄєЇїІі‚ѓ„…†‡€‰ЌЋЏ™")


def repair_text(value: str) -> str:
    """Repair common UTF-8/CP1251 mojibake fragments without touching healthy text."""

    if not any(character in MOJIBAKE_HINT_CHARS for character in value) and "вЂ" not in value:
        return value
    try:
        repaired = value.encode("cp1251").decode("utf-8")
    except UnicodeError:
        return value
    return repaired


def _repair_value(value: Any) -> Any:
    if isinstance(value, str):
        return repair_text(value)
    if isinstance(value, dict):
        return {key: _repair_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_repair_value(item) for item in value)
    return value


I18N.update(cast(dict[LanguageCode, dict[str, Any]], _repair_value(I18N)))


def _resolve_key(mapping: Mapping[str, Any], dotted_key: str) -> Any:
    value: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise KeyError(dotted_key)
        value = value[part]
    return value


def normalize_language(value: str | None) -> LanguageCode:
    return "ru" if value == "ru" else "en"


def resolve_language(requested: str | None) -> LanguageCode:
    if requested in {"ru", "en"}:
        return cast(LanguageCode, requested)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        system_locale, _ = locale.getdefaultlocale()

    if system_locale and system_locale.lower().startswith("ru"):
        return "ru"
    return "en"


def get_catalog(language: str | None) -> Mapping[str, Any]:
    return I18N[normalize_language(language)]


def tr(language: str | None, dotted_key: str, /, **kwargs: Any) -> str:
    resolved_language = normalize_language(language)
    try:
        template = _resolve_key(I18N[resolved_language], dotted_key)
    except KeyError:
        template = _resolve_key(I18N["en"], dotted_key)

    if not isinstance(template, str):
        raise TypeError(f"Translation key {dotted_key!r} does not point to a string")
    return template.format(**kwargs)


