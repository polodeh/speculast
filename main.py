from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
import webbrowser
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.text import Text

from engine.analyzer.engine import AnalyzerEngine
from engine.core.i18n import LanguageCode, repair_text, resolve_language, tr
from engine.core.models import (
    AnalysisResult,
    AnalysisWarningSchema,
    CoverageEntry,
    GeneratedTestPlan,
    GeneratorConfig,
    TestCaseResult,
    TestExecutionResult,
    TestOutcome,
)
from engine.generator.engine import GeneratorEngine
from engine.infra.manager import InfraManager
from engine.parser import derive_module_name, detect_source_root, read_python_source
from engine.visualizer.renderer import VisualReportRenderer

ASCII_LOGO = r"""
                           _           _
 ___ _ __   ___  ___ _   _| | __ _ ___| |_
/ __| '_ \ / _ \/ __| | | | |/ _` / __| __|
\__ \ |_) |  __/ (__| |_| | | (_| \__ \ |_
|___/ .__/ \___|\___|\__,_|_|\__,_|___/\__|
    |_|
"""

BRAND_NAME = "speculast"
BANNER_SUBTITLE = (
    "\u0430\u0432\u0442\u043e\u043d\u043e\u043c\u043d\u044b\u0439 "
    "\u0436\u0438\u0437\u043d\u0435\u043d\u043d\u044b\u0439 "
    "\u0446\u0438\u043a\u043b"
)
IS_WINDOWS = sys.platform.startswith("win")
DOCKER_DESKTOP_CANDIDATES = (
    Path("C:/Program Files/Docker/Docker/Docker Desktop.exe"),
    Path.home() / "AppData" / "Local" / "Docker" / "Docker Desktop.exe",
)
DOCKER_DAEMON_TIMEOUT_SECONDS = 180
CONTAINER_READY_TIMEOUT_SECONDS = 180
CONTAINER_READY_STATES = frozenset({"healthy", "running", "ready"})
SERVICE_STATUS_SCORES: Mapping[str, int] = {
    "healthy": 100,
    "running": 90,
    "ready": 100,
    "planned": 72,
    "starting": 48,
    "unavailable": 18,
    "error": 8,
}
REPORTS_DIRECTORY_NAME = "reports"
REPORT_ARTIFACT_PREFIX = "report"
REPORT_FILE_PREFIX = "report_"
REPORT_FILE_EXTENSION = ".html"
REPORT_DIRECTORY_DATE_FORMAT = "%Y-%m-%d"
REPORT_FILE_TIME_FORMAT = "%H%M%S"
DEFAULT_REPORT_RETENTION_DAYS = 7
@dataclass(slots=True)
class ArtifactBundle:
    generated_test_path: Path | None = None
    compose_path: Path | None = None
    report_path: Path | None = None
    pytest_report_path: Path | None = None
    coverage_path: Path | None = None

    def as_rows(self) -> list[tuple[str, Path | None]]:
        return [
            ("pytest_suite", self.generated_test_path),
            ("docker_compose", self.compose_path),
            ("html_report", self.report_path),
            ("pytest_json", self.pytest_report_path),
            ("coverage_json", self.coverage_path),
        ]


@dataclass(slots=True)
class PipelineOutcome:
    analysis: AnalysisResult
    suite_plan: tuple[GeneratedTestPlan, ...]
    artifacts: ArtifactBundle
    runtime_status: dict[str, str]
    execution_result: TestExecutionResult | None
    use_real_db: bool
    lang: LanguageCode


@dataclass(slots=True, frozen=True)
class CliSettings:
    input_path: Path
    run_tests: bool
    generate_report: bool
    use_real_db: bool
    cleanup_temp: bool
    cleanup_reports: bool
    report_retention_days: int


class NoAnalyzableFilesError(RuntimeError):
    """Raised when the project does not contain analyzable Python source files."""


def detect_requested_language(argv: Sequence[str]) -> LanguageCode:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--lang", choices=["ru", "en"], default=None)
    namespace, _ = bootstrap.parse_known_args(argv)
    return resolve_language(namespace.lang)


def localized_text(language: LanguageCode, *, en: str, ru: str) -> str:
    return repair_text(ru) if language == "ru" else repair_text(en)


def build_parser(lang: LanguageCode) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speculast",
        description=f"{BRAND_NAME}: {tr(lang, 'cli.description')}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=Path("."),
        type=Path,
        help=localized_text(
            lang,
            en="Path to a Python project root or a single .py file. Defaults to the current directory.",
            ru="Путь к корню Python-проекта или к отдельному .py файлу. По умолчанию используется текущая директория.",
        ),
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help=localized_text(
            lang,
            en="Skip pytest execution and prepare analysis artifacts only.",
            ru="Не запускать pytest и ограничиться анализом с подготовкой артефактов.",
        ),
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help=localized_text(
            lang,
            en="Skip HTML report generation and browser auto-open.",
            ru="Не генерировать HTML-отчёт и не открывать его автоматически в браузере.",
        ),
    )
    parser.add_argument(
        "--no-real-db",
        action="store_true",
        help=localized_text(
            lang,
            en="Disable the default real database mode and stay in mocked execution paths.",
            ru="Отключить режим реальной БД по умолчанию и остаться на мокированных сценариях.",
        ),
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help=localized_text(
            lang,
            en="Keep temporary technical artifacts instead of cleaning them automatically.",
            ru="Не удалять временные технические артефакты автоматически.",
        ),
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--real-db",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--lang",
        choices=["ru", "en"],
        default=lang,
        help=tr(lang, "cli.lang_help"),
    )
    parser.add_argument(
        "--cleanup-reports",
        action="store_true",
        help=f"{BRAND_NAME}: delete HTML reports older than the retention window before generating a new one.",
    )
    parser.add_argument(
        "--report-retention-days",
        type=int,
        default=DEFAULT_REPORT_RETENTION_DAYS,
        help=f"{BRAND_NAME} retention window in days for --cleanup-reports.",
    )
    return parser


def resolve_cli_settings(args: argparse.Namespace) -> CliSettings:
    run_tests = True
    generate_report = True

    if args.generate_only or args.visualize:
        run_tests = False
    if args.run_all:
        run_tests = True
        generate_report = True

    if args.no_tests:
        run_tests = False
    if args.no_viz:
        generate_report = False

    return CliSettings(
        input_path=Path(args.path).resolve(),
        run_tests=run_tests,
        generate_report=generate_report,
        use_real_db=not args.no_real_db,
        cleanup_temp=not args.no_cleanup,
        cleanup_reports=args.cleanup_reports,
        report_retention_days=args.report_retention_days,
    )


def report_run_mode_key(*, run_tests: bool) -> str:
    return "run_all" if run_tests else "visualize"


def format_run_mode(*, run_tests: bool, generate_report: bool, lang: LanguageCode) -> str:
    if run_tests and generate_report:
        return tr(lang, "shared.run_modes.run_all")
    if run_tests:
        return localized_text(
            lang,
            en="Tests without HTML report",
            ru="Тесты без HTML-отчёта",
        )
    if generate_report:
        return tr(lang, "shared.run_modes.visualize")
    return localized_text(
        lang,
        en="Analysis and generation only",
        ru="Только анализ и генерация",
    )


def main() -> int:
    configure_windows_utf8_streams()
    configure_console()
    initial_lang = detect_requested_language(sys.argv[1:])
    args = build_parser(initial_lang).parse_args()
    settings = resolve_cli_settings(args)
    lang = resolve_language(args.lang)
    console = Console()
    render_banner(console, lang)

    try:
        outcome = execute_pipeline(
            console=console,
            input_path=settings.input_path,
            run_tests=settings.run_tests,
            generate_report=settings.generate_report,
            use_real_db=settings.use_real_db,
            cleanup_temp=settings.cleanup_temp,
            cleanup_reports=settings.cleanup_reports,
            report_retention_days=settings.report_retention_days,
            lang=lang,
        )
    except NoAnalyzableFilesError as error:
        console.print(
            Panel(
                Text(str(error), style="bold yellow"),
                title=f"[bold white] {BRAND_NAME} [/bold white]",
                border_style="yellow",
            )
        )
        return 0
    except Exception as error:
        console.print(
            Panel(
                Text(str(error), style="bold red"),
                title=f"{BRAND_NAME} | {tr(lang, 'terminal.errors.title')}",
                border_style="red",
            )
        )
        return 1

    exit_code = 0
    if settings.run_tests and outcome.execution_result is not None:
        exit_code = outcome.execution_result.exit_code

    render_analysis_warnings(console, outcome.analysis.project.analysis_warnings, lang)
    render_final_status(
        console,
        outcome=outcome,
        run_tests=settings.run_tests,
        generate_report=settings.generate_report,
        exit_code=exit_code,
        lang=lang,
    )
    if settings.generate_report:
        open_generated_report(outcome.artifacts.report_path)
    return exit_code


def execute_pipeline(
    *,
    console: Console,
    input_path: Path,
    run_tests: bool,
    generate_report: bool,
    use_real_db: bool,
    cleanup_temp: bool,
    cleanup_reports: bool,
    report_retention_days: int,
    lang: LanguageCode,
) -> PipelineOutcome:
    analyzer = AnalyzerEngine()
    infra_manager = InfraManager()
    visualizer = VisualReportRenderer(lang=lang) if generate_report else None

    project_root: Path | None = None
    artifacts = ArtifactBundle()
    runtime_status: dict[str, str] = {}
    execution_result: TestExecutionResult | None = None
    suite_plan: tuple[GeneratedTestPlan, ...] = ()
    analysis_result: AnalysisResult | None = None
    should_prepare_runtime = run_tests and use_real_db
    docker_cleanup_required = False
    reports_directory: Path | None = None

    with Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task(
            f"[cyan]{tr(lang, 'terminal.progress.initializing')}[/cyan]",
            total=1,
        )

        progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.semantic_analysis')}[/cyan]")
        project_root, initial_analysis = run_analysis(analyzer, input_path, lang)
        reports_directory = ensure_reports_directory(project_root)
        if cleanup_reports:
            cleanup_old_reports(
                project_root,
                retention_days=report_retention_days,
                reports_directory=reports_directory,
            )
        if cleanup_temp:
            cleanup_temp_artifacts(project_root)
        analysis_result = infra_manager.enrich_analysis(initial_analysis)
        progress.advance(task_id)

        should_manage_infra = should_prepare_runtime and bool(analysis_result.required_infra)
        total_steps = 3 + int(run_tests) + int(generate_report) + (2 if should_manage_infra else 0)
        progress.update(task_id, total=total_steps)
        generator = GeneratorEngine(config=GeneratorConfig(use_real_db=use_real_db))

        progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.generating_tests')}[/cyan]")
        artifacts.generated_test_path = generator.generate(
            analysis_result,
            build_test_output_path(project_root, input_path),
        )
        suite_plan = generator.last_suite_plan or generator.build_suite_plan(analysis_result)
        progress.advance(task_id)

        progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.preparing_infra')}[/cyan]")
        artifacts.compose_path = infra_manager.create_compose_file(
            project_root,
            analysis_result.required_infra,
            output_directory=artifacts.generated_test_path.parent.parent,
        )
        progress.advance(task_id)

        try:
            if should_manage_infra:
                docker_cleanup_required = artifacts.compose_path is not None
                progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.starting_docker')}[/cyan]")
                ensure_docker_daemon(lang)
                run_compose_up(project_root, artifacts.compose_path, lang)
                runtime_status = wait_for_services(
                    project_root,
                    artifacts.compose_path,
                    analysis_result.required_infra,
                    infra_manager,
                    lang,
                )
                progress.advance(task_id)

            if run_tests:
                progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.running_tests')}[/cyan]")
                artifacts_root = ensure_artifacts_directory(
                    project_root,
                    run_directory=artifacts.generated_test_path.parent.parent,
                )
                execution_result = run_generated_tests(
                    project_root=project_root,
                    generated_test_path=artifacts.generated_test_path,
                    artifacts_root=artifacts_root,
                    suite_plan=suite_plan,
                    lang=lang,
                )
                artifacts.pytest_report_path = execution_result.report_path
                artifacts.coverage_path = execution_result.coverage_path
                progress.advance(task_id)

            if cleanup_temp:
                removed_temp_artifacts = set(cleanup_temp_artifacts(project_root))
                if artifacts.pytest_report_path in removed_temp_artifacts:
                    artifacts.pytest_report_path = None
                if artifacts.coverage_path in removed_temp_artifacts:
                    artifacts.coverage_path = None
                if execution_result is not None:
                    execution_result = execution_result.model_copy(
                        update={
                            "report_path": artifacts.pytest_report_path,
                            "coverage_path": artifacts.coverage_path,
                        }
                    )

            if generate_report and visualizer is not None:
                progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.building_report')}[/cyan]")
                report_output_path = build_report_output_path(
                    project_root,
                    reports_directory=reports_directory,
                )
                artifacts.report_path = report_output_path
                artifacts.report_path = visualizer.generate(
                    analysis_result,
                    report_output_path,
                    runtime_status=runtime_status,
                    execution_result=execution_result,
                    suite_plan=suite_plan,
                    artifacts=artifacts.as_rows(),
                    run_mode=report_run_mode_key(run_tests=run_tests),
                )
                mark_owned_report(artifacts.report_path)
                progress.advance(task_id)
        finally:
            if should_manage_infra and docker_cleanup_required and artifacts.compose_path is not None:
                progress.update(task_id, description=f"[cyan]{tr(lang, 'terminal.progress.stopping_docker')}[/cyan]")
                run_compose_down(project_root, artifacts.compose_path, lang)
                progress.advance(task_id)

    if analysis_result is None:
        raise RuntimeError(tr(lang, "terminal.errors.missing_analysis"))

    return PipelineOutcome(
        analysis=analysis_result,
        suite_plan=suite_plan,
        artifacts=artifacts,
        runtime_status=runtime_status,
        execution_result=execution_result,
        use_real_db=use_real_db,
        lang=lang,
    )


def run_analysis(
    analyzer: AnalyzerEngine,
    input_path: Path,
    lang: LanguageCode,
) -> tuple[Path, AnalysisResult]:
    if input_path.is_dir():
        analysis_result = analyzer.analyze_project(input_path)
        ensure_analysis_is_not_empty(analysis_result, lang)
        return input_path, analysis_result

    if input_path.is_file() and input_path.suffix == ".py":
        project_root = infer_project_root_from_file(input_path)
        analysis_result = analyzer.analyze(project_root, input_path)
        ensure_analysis_is_not_empty(analysis_result, lang)
        return project_root, analysis_result

    raise FileNotFoundError(tr(lang, "terminal.errors.unsupported_path", path=input_path))


def infer_project_root_from_file(file_path: Path) -> Path:
    resolved_path = file_path.resolve()
    for ancestor in resolved_path.parents:
        if ancestor.name == "src":
            return ancestor.parent.resolve()

    package_root = resolved_path.parent
    while (package_root / "__init__.py").exists() and package_root.parent != package_root:
        package_root = package_root.parent
    return package_root.resolve()


def ensure_analysis_is_not_empty(analysis_result: AnalysisResult, lang: LanguageCode) -> None:
    if not analysis_result.project.analyzed_files:
        raise NoAnalyzableFilesError(tr(lang, "terminal.errors.no_files_found"))

    if analysis_result.functions:
        return

    if all(not read_python_source(path).strip() for path in analysis_result.project.analyzed_files):
        raise NoAnalyzableFilesError(tr(lang, "terminal.errors.no_files_found"))


def render_analysis_warnings(
    console: Console,
    warnings: Sequence[AnalysisWarningSchema],
    lang: LanguageCode,
) -> None:
    if not warnings:
        return

    body = "\n".join(
        tr(
            lang,
            f"terminal.warnings.{warning.kind}",
            path=warning.file_path,
            line=warning.line_number or "?",
            details=warning.details or tr(lang, "shared.common.none"),
        )
        for warning in warnings
    )
    console.print(
        Panel(
            Text(body, style="bold yellow"),
            title=f"[bold yellow]{tr(lang, 'terminal.warnings.title')}[/bold yellow]",
            border_style="yellow",
        )
    )


def ensure_artifacts_directory(project_root: Path, *, run_directory: Path | None = None) -> Path:
    artifacts_root = (run_directory or project_root / ".speculast").resolve()
    artifacts_root.mkdir(parents=True, exist_ok=True)
    return artifacts_root


def ensure_reports_directory(project_root: Path) -> Path:
    reports_directory = (project_root / REPORTS_DIRECTORY_NAME).resolve()
    os.makedirs(reports_directory, exist_ok=True)
    return reports_directory


def ensure_report_day_directory(
    project_root: Path,
    *,
    report_date: datetime | None = None,
    reports_directory: Path | None = None,
) -> Path:
    resolved_reports_directory = reports_directory or ensure_reports_directory(project_root)
    directory_name = (report_date or datetime.now()).strftime(REPORT_DIRECTORY_DATE_FORMAT)
    report_day_directory = resolved_reports_directory / directory_name
    os.makedirs(report_day_directory, exist_ok=True)
    return report_day_directory.resolve()


def build_report_day_directory_for_timestamp(
    report_timestamp: datetime,
    *,
    reports_directory: Path,
) -> Path:
    report_day_directory = reports_directory / report_timestamp.strftime(REPORT_DIRECTORY_DATE_FORMAT)
    os.makedirs(report_day_directory, exist_ok=True)
    return report_day_directory.resolve()


def build_report_output_path(
    project_root: Path,
    *,
    generated_at: datetime | None = None,
    reports_directory: Path | None = None,
) -> Path:
    report_moment = generated_at or datetime.now()
    report_day_directory = ensure_report_day_directory(
        project_root,
        report_date=report_moment,
        reports_directory=reports_directory,
    )
    report_time = report_moment.strftime(REPORT_FILE_TIME_FORMAT)
    candidate = report_day_directory / f"{REPORT_FILE_PREFIX}{report_time}{REPORT_FILE_EXTENSION}"
    suffix = 1
    while candidate.exists() or report_ownership_path(candidate).exists():
        candidate = report_day_directory / (
            f"{REPORT_FILE_PREFIX}{report_time}_{suffix:02d}{REPORT_FILE_EXTENSION}"
        )
        suffix += 1
    return candidate.resolve()


def migrate_legacy_report_artifacts(
    project_root: Path,
    *,
    reports_directory: Path | None = None,
) -> tuple[Path, ...]:
    """Retain unknown legacy files; their ownership cannot be established."""
    return ()


def report_ownership_path(report_path: Path) -> Path:
    return report_path.with_name(report_path.name + ".speculast-owned")


def mark_owned_report(report_path: Path) -> None:
    digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    with report_ownership_path(report_path).open("x", encoding="ascii") as marker:
        marker.write(digest)


def cleanup_old_reports(
    project_root: Path,
    *,
    retention_days: int = DEFAULT_REPORT_RETENTION_DAYS,
    now: datetime | None = None,
    reports_directory: Path | None = None,
) -> tuple[Path, ...]:
    if retention_days < 0:
        raise ValueError("report_retention_days must be >= 0")

    resolved_reports_directory = reports_directory or ensure_reports_directory(project_root)
    cutoff = (now or datetime.now()) - timedelta(days=retention_days)
    removed_reports: list[Path] = []

    report_pattern = f"{REPORT_FILE_PREFIX}*{REPORT_FILE_EXTENSION}"
    for candidate in resolved_reports_directory.rglob(report_pattern):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        marker = report_ownership_path(candidate)
        if not marker.is_file() or marker.is_symlink():
            continue
        try:
            expected_digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            marker_digest = marker.read_text(encoding="ascii")
        except (OSError, UnicodeError):
            continue
        if marker_digest != expected_digest:
            continue
        modified_at = datetime.fromtimestamp(candidate.stat().st_mtime)
        if modified_at >= cutoff:
            continue
        candidate.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
        removed_reports.append(candidate)
        if not any(candidate.parent.iterdir()):
            candidate.parent.rmdir()

    return tuple(removed_reports)


def cleanup_temp_artifacts(project_root: Path) -> tuple[Path, ...]:
    """Leave untracked temporary files untouched when ownership is unknown."""
    return ()


def should_cleanup_temp_artifact(candidate: Path) -> bool:
    return False


def ensure_docker_daemon(lang: LanguageCode) -> None:
    ready, _ = docker_daemon_status()
    if ready:
        return

    if not IS_WINDOWS:
        raise RuntimeError(tr(lang, "terminal.errors.docker_daemon_unavailable"))

    desktop_path = next((path for path in DOCKER_DESKTOP_CANDIDATES if path.exists()), None)
    if desktop_path is None:
        raise RuntimeError(tr(lang, "terminal.errors.docker_desktop_missing"))

    subprocess.Popen(
        [str(desktop_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + DOCKER_DAEMON_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        ready, _ = docker_daemon_status()
        if ready:
            return
        time.sleep(1)

    raise RuntimeError(tr(lang, "terminal.errors.docker_daemon_timeout"))


def docker_daemon_status() -> tuple[bool, str]:
    completed = run_subprocess(
        ["docker", "info", "--format", "{{json .ServerVersion}}"],
        check=False,
    )
    if completed.returncode == 0:
        return True, completed.stdout.strip()
    return False, completed.stderr.strip() or completed.stdout.strip()


def compose_command(compose_path: Path) -> list[str]:
    digest = hashlib.sha256(str(compose_path.resolve()).encode("utf-8")).hexdigest()[:12]
    return ["docker", "compose", "-p", f"speculast_{digest}", "-f", str(compose_path)]


def run_compose_up(project_root: Path, compose_path: Path, lang: LanguageCode) -> None:
    completed = run_subprocess(
        [*compose_command(compose_path), "up", "-d"],
        cwd=project_root,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or tr(lang, "terminal.errors.compose_up_failed"))


def wait_for_services(
    project_root: Path,
    compose_path: Path,
    required_infra: Sequence[str],
    infra_manager: InfraManager,
    lang: LanguageCode,
) -> dict[str, str]:
    logical_to_compose = {
        service_name: compose_name
        for service_name, compose_name in zip(
            required_infra,
            infra_manager.compose_service_names(required_infra),
            strict=False,
        )
    }
    if not logical_to_compose:
        return {}

    latest_status: dict[str, str] = {service_name: "starting" for service_name in logical_to_compose}
    deadline = time.monotonic() + CONTAINER_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        ready_count = 0
        for logical_name, compose_name in logical_to_compose.items():
            status = inspect_service_status(project_root, compose_path, compose_name)
            latest_status[logical_name] = status
            if status in CONTAINER_READY_STATES:
                ready_count += 1
        if ready_count == len(logical_to_compose):
            return latest_status
        time.sleep(2)

    unresolved = ", ".join(f"{name}={status}" for name, status in latest_status.items())
    raise RuntimeError(tr(lang, "terminal.errors.containers_not_ready", details=unresolved))


def inspect_service_status(
    project_root: Path, compose_path: Path, compose_service_name: str
) -> str:
    id_result = run_subprocess(
        [*compose_command(compose_path), "ps", "-q", compose_service_name],
        cwd=project_root,
        check=False,
    )
    container_id = id_result.stdout.strip()
    if id_result.returncode != 0:
        return "error"
    if not container_id:
        return "starting"

    inspect_result = run_subprocess(
        [
            "docker",
            "inspect",
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
            container_id,
        ],
        cwd=project_root,
        check=False,
    )
    if inspect_result.returncode != 0:
        return "error"
    return inspect_result.stdout.strip().lower() or "starting"


def run_compose_down(project_root: Path, compose_path: Path, lang: LanguageCode) -> None:
    completed = run_subprocess(
        [*compose_command(compose_path), "down"],
        cwd=project_root,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or tr(lang, "terminal.errors.compose_down_failed"))


def run_generated_tests(
    *,
    project_root: Path,
    generated_test_path: Path | None,
    artifacts_root: Path,
    suite_plan: Sequence[GeneratedTestPlan],
    lang: LanguageCode,
) -> TestExecutionResult:
    if generated_test_path is None:
        raise RuntimeError(tr(lang, "terminal.errors.pytest_suite_missing"))

    pytest_report_path = (artifacts_root / "pytest-report.json").resolve()
    coverage_path = (artifacts_root / "coverage.json").resolve()
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(generated_test_path),
        "-q",
        "-p",
        "no:cacheprovider",
        "--disable-warnings",
        "--json-report",
        f"--json-report-file={pytest_report_path}",
        "--cov=.",
        f"--cov-report=json:{coverage_path}",
        "--cov-report=",
    ]
    environment = os.environ.copy()
    environment["COVERAGE_FILE"] = str(artifacts_root / ".coverage")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run_subprocess(command, cwd=project_root, env=environment, check=False)

    report_data = load_json_file(pytest_report_path)
    coverage_data = load_json_file(coverage_path)
    plan_by_test_name = {plan.test_name: plan for plan in suite_plan}

    tests = parse_test_cases(report_data, plan_by_test_name)
    summary = report_data.get("summary", {}) if isinstance(report_data, Mapping) else {}
    totals = coverage_data.get("totals", {}) if isinstance(coverage_data, Mapping) else {}
    coverage_entries = parse_coverage_entries(coverage_data)

    return TestExecutionResult(
        exit_code=max(0, completed.returncode),
        total=int(summary.get("total", len(tests))),
        passed=int(summary.get("passed", 0)),
        failed=int(summary.get("failed", 0)),
        skipped=int(summary.get("skipped", 0)),
        errors=int(summary.get("error", 0)),
        duration=float(report_data.get("duration", 0.0) if isinstance(report_data, Mapping) else 0.0),
        coverage_percent=float(totals.get("percent_covered", 0.0)),
        stdout=completed.stdout,
        stderr=completed.stderr,
        tests=tuple(tests),
        coverage=tuple(coverage_entries),
        report_path=pytest_report_path if pytest_report_path.exists() else None,
        coverage_path=coverage_path if coverage_path.exists() else None,
    )


def parse_test_cases(
    report_data: Mapping[str, Any],
    plan_by_test_name: Mapping[str, GeneratedTestPlan],
) -> list[TestCaseResult]:
    raw_tests = report_data.get("tests", [])
    if not isinstance(raw_tests, Sequence):
        return []

    parsed_tests: list[TestCaseResult] = []
    for raw_test in raw_tests:
        if not isinstance(raw_test, Mapping):
            continue

        nodeid = str(raw_test.get("nodeid", "generated::unknown"))
        test_name = nodeid.split("::")[-1]
        plan = plan_by_test_name.get(test_name)
        call_section = raw_test.get("call", {})
        setup_section = raw_test.get("setup", {})
        teardown_section = raw_test.get("teardown", {})
        outcome_value = str(
            raw_test.get("outcome")
            or (call_section.get("outcome") if isinstance(call_section, Mapping) else "")
            or (setup_section.get("outcome") if isinstance(setup_section, Mapping) else "")
            or "error"
        )
        duration = 0.0
        for section in (setup_section, call_section, teardown_section):
            if isinstance(section, Mapping):
                duration += float(section.get("duration", 0.0) or 0.0)

        longrepr = extract_longrepr(call_section, setup_section, teardown_section)
        parsed_tests.append(
            TestCaseResult(
                nodeid=nodeid,
                outcome=normalize_outcome(outcome_value),
                duration=duration,
                message=extract_message(longrepr),
                longrepr=longrepr,
                mocked_calls=tuple(plan.mock_targets) if plan is not None else (),
            )
        )
    return parsed_tests


def parse_coverage_entries(coverage_data: Mapping[str, Any]) -> list[CoverageEntry]:
    raw_files = coverage_data.get("files", {})
    if not isinstance(raw_files, Mapping):
        return []

    entries: list[CoverageEntry] = []
    for path, payload in raw_files.items():
        if not isinstance(payload, Mapping):
            continue
        summary = payload.get("summary", {})
        if not isinstance(summary, Mapping):
            continue
        entries.append(
            CoverageEntry(
                path=str(path),
                covered_lines=int(summary.get("covered_lines", 0)),
                missing_lines=int(summary.get("missing_lines", 0)),
                num_statements=int(summary.get("num_statements", 0)),
                percent_covered=float(summary.get("percent_covered", 0.0)),
            )
        )
    return entries


def normalize_outcome(value: str) -> TestOutcome:
    normalized = value.strip().lower()
    if normalized == "passed":
        return TestOutcome.PASSED
    if normalized == "failed":
        return TestOutcome.FAILED
    if normalized == "skipped":
        return TestOutcome.SKIPPED
    return TestOutcome.ERROR


def extract_longrepr(*sections: object) -> str | None:
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        longrepr = section.get("longrepr")
        if isinstance(longrepr, str) and longrepr.strip():
            return longrepr
    return None


def extract_message(longrepr: str | None) -> str | None:
    if longrepr is None:
        return None
    for line in longrepr.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:240]
    return None


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def run_subprocess(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def render_banner(console: Console, lang: LanguageCode) -> None:
    console.print(
        Panel.fit(
            Text(ASCII_LOGO, style="bold bright_cyan"),
            title=f"[bold white] {BRAND_NAME} [/bold white]",
            title_align="center",
            subtitle=f"[cyan] {BANNER_SUBTITLE} [/cyan]",
            subtitle_align="center",
            border_style="bright_blue",
            padding=(1, 3),
        )
    )


def render_final_status(
    console: Console,
    *,
    outcome: PipelineOutcome,
    run_tests: bool,
    generate_report: bool,
    exit_code: int,
    lang: LanguageCode,
) -> None:
    if outcome.execution_result is None:
        tests_line = tr(lang, "terminal.final.tests_not_run")
    else:
        tests_line = tr(
            lang,
            "terminal.final.tests_summary",
            passed=outcome.execution_result.passed,
            total=outcome.execution_result.total,
            errors=outcome.execution_result.failed + outcome.execution_result.errors,
            skipped=outcome.execution_result.skipped,
        )

    infra_display = ", ".join(
        tr(lang, f"shared.service_names.{service_name}") if service_name in {"postgresql", "redis"} else service_name
        for service_name in outcome.analysis.required_infra
    ) or tr(lang, "shared.infra.not_required")
    readiness_score = build_infra_score(outcome.analysis.required_infra, outcome.runtime_status)
    status_title = (
        f"{BRAND_NAME} | {tr(lang, 'terminal.final.success_title')}"
        if exit_code == 0
        else f"{BRAND_NAME} | {tr(lang, 'terminal.final.failure_title')}"
    )
    panel_title = f"[bold white] {BRAND_NAME} [/bold white]" if exit_code == 0 else status_title
    border_style = "green" if exit_code == 0 else "red"
    mode_display = format_run_mode(
        run_tests=run_tests,
        generate_report=generate_report,
        lang=lang,
    )
    real_db_display = tr(lang, "terminal.final.real_db_enabled") if outcome.use_real_db else tr(lang, "terminal.final.real_db_disabled")
    report_line = (
        tr(lang, "terminal.final.report", path=outcome.artifacts.report_path)
        if outcome.artifacts.report_path is not None
        else localized_text(
            lang,
            en="HTML report: disabled.",
            ru="HTML-отчёт: отключён.",
        )
    )

    body_lines = [
        tr(lang, "terminal.final.mode", value=mode_display),
        tr(lang, "terminal.final.real_db", value=real_db_display),
        tr(lang, "terminal.final.infrastructure", infra=infra_display, score=readiness_score),
        tr(lang, "terminal.final.files_found", count=len(outcome.analysis.project.analyzed_files)),
        tr(
            lang,
            "terminal.final.functions_covered",
            covered=len(outcome.suite_plan),
            total=len(outcome.analysis.functions),
        ),
        tests_line,
        report_line,
    ]
    if exit_code == 0:
        success_heading = tr(lang, "terminal.final.success_title")
        success_intro = (
            localized_text(
                lang,
                en="Everything is ready, tests passed.",
                ru=(
                    "\u0412\u0441\u0451 \u0433\u043e\u0442\u043e\u0432\u043e, "
                    "\u0442\u0435\u0441\u0442\u044b \u043f\u0440\u043e\u0439\u0434\u0435\u043d\u044b."
                ),
            )
            if outcome.execution_result is not None
            else localized_text(
                lang,
                en="The contour is assembled. Analysis complete and the runway is clear.",
                ru=(
                    "\u041a\u043e\u043d\u0442\u0443\u0440 \u0441\u043e\u0431\u0440\u0430\u043d. "
                    "\u0410\u043d\u0430\u043b\u0438\u0437 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d, "
                    "\u043c\u043e\u0436\u043d\u043e \u0438\u0434\u0442\u0438 \u0434\u0430\u043b\u044c\u0448\u0435."
                ),
            )
        )
        body_lines = [
            success_heading,
            success_intro,
            "",
            *body_lines,
        ]
    body = "\n".join(body_lines)
    console.print(
        Panel(
            Text(body, style="bold white"),
            title=panel_title,
            border_style=border_style,
        )
    )


def open_generated_report(report_path: Path | None) -> bool:
    if report_path is None:
        return False
    try:
        return bool(webbrowser.open(report_path.resolve().as_uri()))
    except Exception:
        return False


def build_infra_score(required_infra: Sequence[str], runtime_status: Mapping[str, str]) -> int:
    if not required_infra:
        return 100
    scores = [
        SERVICE_STATUS_SCORES.get(runtime_status.get(service_name, "planned"), 24)
        for service_name in required_infra
    ]
    return round(sum(scores) / len(scores))


def build_test_output_path(project_root: Path, input_path: Path) -> Path:
    tests_directory = project_root / ".speculast" / "runs" / uuid.uuid4().hex / "tests"
    if input_path.is_file():
        module_root = detect_source_root(input_path, project_root)
        suite_name = sanitize_name(derive_module_name(input_path, module_root).replace(".", "_"))
    else:
        suite_name = f"{sanitize_name(project_root.name)}_generated"
    return tests_directory / f"test_{suite_name}.py"


def configure_console() -> None:
    configure_windows_utf8_streams()


def configure_windows_utf8_streams() -> None:
    if sys.platform != "win32":
        return

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def sanitize_name(value: str) -> str:
    return re.sub(r"\W+", "_", value).strip("_") or "generated"


if __name__ == "__main__":
    configure_windows_utf8_streams()
    raise SystemExit(main())
