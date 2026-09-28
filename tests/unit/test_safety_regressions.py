from __future__ import annotations

import subprocess

import pytest

from engine.analyzer.engine import AnalyzerEngine
from engine.generator.engine import GeneratorEngine
from engine.infra.manager import InfraManager
from engine.visualizer.renderer import VisualReportRenderer
from main import (
    build_test_output_path,
    cleanup_temp_artifacts,
    run_compose_down,
    run_compose_up,
)


def test_generator_preserves_existing_project_tests_and_config(tmp_path) -> None:
    (tmp_path / "module.py").write_text("def value(): return 1\n", encoding="utf-8")
    tests_root = tmp_path / "tests"
    (tests_root / "unit").mkdir(parents=True)
    original_files = {
        tests_root / "test_generated_suite.py": "user suite\n",
        tests_root / "conftest.py": "user fixtures\n",
        tests_root / "pyproject.toml": "user config\n",
        tests_root / "unit" / "test_logic.py": "user regression\n",
    }
    for path, content in original_files.items():
        path.write_text(content, encoding="utf-8")

    analysis = AnalyzerEngine().analyze_project(tmp_path)
    with pytest.raises(FileExistsError):
        GeneratorEngine().generate(analysis, tests_root / "test_generated_suite.py")

    for path, content in original_files.items():
        assert path.read_text(encoding="utf-8") == content


def test_cleanup_preserves_unowned_hidden_and_tmp_entries(tmp_path) -> None:
    hidden = tmp_path / ".custom-data"
    hidden.mkdir()
    (hidden / "important.txt").write_text("keep", encoding="utf-8")
    temporary = tmp_path / "tmp_customer_data.txt"
    temporary.write_text("keep", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "important.txt").write_text("keep", encoding="utf-8")

    cleanup_temp_artifacts(tmp_path)

    assert (hidden / "important.txt").read_text(encoding="utf-8") == "keep"
    assert temporary.read_text(encoding="utf-8") == "keep"
    assert (cache / "important.txt").read_text(encoding="utf-8") == "keep"


def test_compose_generation_preserves_project_infrastructure(tmp_path) -> None:
    project_compose = tmp_path / "docker-compose.yaml"
    project_compose.write_text("services:\n  user: {}\n", encoding="utf-8")

    generated = InfraManager().create_compose_file(tmp_path, ["postgresql"])
    second = InfraManager().create_compose_file(tmp_path, ["postgresql"])

    assert project_compose.read_text(encoding="utf-8") == "services:\n  user: {}\n"
    assert generated is not None
    assert generated != project_compose
    assert second is not None and second != generated
    assert generated.read_text(encoding="utf-8").startswith("services:")


def test_generated_suite_path_is_unique_and_outside_project_tests(tmp_path) -> None:
    source = tmp_path / "module.py"
    source.write_text("def value(): return 1\n", encoding="utf-8")

    first = build_test_output_path(tmp_path, source)
    second = build_test_output_path(tmp_path, source)

    assert first != second
    assert first.parent.parent.parent.parent == tmp_path / ".speculast"
    assert first.name == "test_module.py"


def test_compose_commands_use_only_generated_file_and_project(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []

    def capture(command, *, cwd=None, check=False, env=None):
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("main.run_subprocess", capture)
    compose = tmp_path / ".speculast" / "docker-compose.yaml"

    run_compose_up(tmp_path, compose, "en")
    run_compose_down(tmp_path, compose, "en")

    assert len(commands) == 2
    for command in commands:
        assert command[:2] == ["docker", "compose"]
        assert command[2] == "-p"
        assert command[4:6] == ["-f", str(compose)]
        assert "--remove-orphans" not in command
    assert commands[0][-2:] == ["up", "-d"]
    assert commands[1][-1] == "down"


def test_renderer_preserves_existing_report(tmp_path) -> None:
    (tmp_path / "module.py").write_text("def value(): return 1\n", encoding="utf-8")
    output = tmp_path / "report.html"
    output.write_text("user report", encoding="utf-8")
    analysis = AnalyzerEngine().analyze_project(tmp_path)

    with pytest.raises(FileExistsError):
        VisualReportRenderer().generate(analysis, output)

    assert output.read_text(encoding="utf-8") == "user report"
