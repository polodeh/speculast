from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from engine.analyzer.engine import AnalyzerEngine
from engine.core.i18n import MOJIBAKE_HINT_CHARS, tr
from engine.generator.engine import GeneratorEngine
from engine.visualizer.dashboard import DashboardBuilder
from main import build_parser, build_test_output_path, render_analysis_warnings


def _run_generated_suite(project_root: Path, generated_suite: Path) -> subprocess.CompletedProcess[str]:
    repository_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = (
        str(repository_root)
        if not environment.get("PYTHONPATH")
        else str(repository_root) + os.pathsep + environment["PYTHONPATH"]
    )
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(generated_suite)],
        cwd=str(project_root),
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _generate_suite(tmp_path: Path, files: dict[str, str]) -> tuple[Path, str]:
    for relative_path, source in files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")

    analysis = AnalyzerEngine().analyze_project(tmp_path)
    generated_suite = GeneratorEngine().generate(analysis, tmp_path / "tests" / "test_generated_suite.py")
    return generated_suite, generated_suite.read_text(encoding="utf-8")


def test_build_test_output_path_is_unique_for_twin_named_files(tmp_path) -> None:
    app_logic = tmp_path / "app" / "logic.py"
    utils_logic = tmp_path / "utils" / "logic.py"
    app_logic.parent.mkdir(parents=True, exist_ok=True)
    utils_logic.parent.mkdir(parents=True, exist_ok=True)
    app_logic.write_text("def app_value(): return 1\n", encoding="utf-8")
    utils_logic.write_text("def utils_value(): return 2\n", encoding="utf-8")

    assert build_test_output_path(tmp_path, app_logic).name == "test_app_logic.py"
    assert build_test_output_path(tmp_path, utils_logic).name == "test_utils_logic.py"


def test_generator_aliases_duplicate_import_names_from_different_modules(tmp_path) -> None:
    _, suite_text = _generate_suite(
        tmp_path,
        {
            "app/logic.py": 'def run() -> str:\n    return "app"\n',
            "utils/logic.py": 'def run() -> str:\n    return "utils"\n',
        },
    )

    assert "from app.logic import run as app_logic__run" in suite_text
    assert "from utils.logic import run as utils_logic__run" in suite_text


def test_analyzer_skips_syntax_junk_and_emits_warning(tmp_path) -> None:
    (tmp_path / "healthy.py").write_text('def ping() -> str:\n    return "pong"\n', encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(\n    return 1\n", encoding="utf-8")

    analysis = AnalyzerEngine().analyze_project(tmp_path)

    assert [function.qualname for function in analysis.functions] == ["ping"]
    assert len(analysis.project.analysis_warnings) == 1
    warning = analysis.project.analysis_warnings[0]
    assert warning.kind == "syntax_error"
    assert warning.file_path.name == "broken.py"

    console = Console(record=True, width=120)
    render_analysis_warnings(console, analysis.project.analysis_warnings, "ru")
    rendered = console.export_text()

    assert "синтаксическая ошибка" in rendered.lower()
    assert "broken.py" in rendered


def test_generated_suite_handles_nested_classes_with_multiple_inheritance(tmp_path) -> None:
    generated_suite, suite_text = _generate_suite(
        tmp_path,
        {
            "shapes.py": "\n".join(
                [
                    "class BaseA:",
                    "    pass",
                    "",
                    "class BaseB:",
                    "    pass",
                    "",
                    "class Outer:",
                    "    class Service(BaseA, BaseB):",
                    "        def ping(self) -> str:",
                    '            return "ok"',
                ]
            )
            + "\n",
        },
    )

    assert "from shapes import Outer" in suite_text
    assert "test_shapes_outer_service_ping" in suite_text

    completed = _run_generated_suite(tmp_path, generated_suite)

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_russian_i18n_is_readable_for_cli_and_dashboard() -> None:
    parser = build_parser("ru")
    help_text = parser.format_help()
    ui = DashboardBuilder(lang="ru")._build_ui_for("ru")

    assert "Путь к корню Python-проекта" in tr("ru", "cli.path_help")
    assert "Не запускать pytest" in help_text
    assert ui["hero_tag"] == "Панель анализа проекта"
    assert ui["sections"]["functions_title"] == "Реестр функций"

    combined = "\n".join(
        [
            tr("ru", "cli.path_help"),
            help_text,
            ui["hero_tag"],
            ui["sections"]["functions_title"],
        ]
    )
    assert "Рџ" not in combined
    assert not any(character in combined for character in MOJIBAKE_HINT_CHARS)
