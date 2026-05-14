from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from engine.analyzer.engine import AnalyzerEngine
from engine.generator.engine import GeneratorEngine


def write_sample_project(project_root: Path) -> None:
    (project_root / "calculator.py").write_text(
        "\n".join(
            [
                "def add(a: int, b: int) -> int:",
                "    return a + b",
                "",
                "class Counter:",
                "    def increment(self, value: int) -> int:",
                "        return value + 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "strings.py").write_text(
        "\n".join(
            [
                "def shout(text: str) -> str:",
                "    return text.upper()",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_generator_uses_dynamic_module_imports_for_any_project(tmp_path) -> None:
    write_sample_project(tmp_path)
    analyzer = AnalyzerEngine()
    generator = GeneratorEngine()
    analysis = analyzer.analyze_project(tmp_path)

    generated_suite = generator.generate(analysis, tmp_path / "tests" / "test_generated_suite.py")
    suite_text = generated_suite.read_text(encoding="utf-8")
    conftest_text = (tmp_path / "tests" / "conftest.py").read_text(encoding="utf-8")

    assert generated_suite.name == "test_generated_suite.py"
    assert "from calculator import add, Counter" in suite_text
    assert "from strings import shout" in suite_text
    assert "demo_shop" not in suite_text
    assert "PROJECT_ROOT = Path(__file__).resolve().parent.parent" in conftest_text
    assert "sys.path.insert(0, str(PROJECT_ROOT))" in conftest_text


def test_generated_suite_executes_for_a_simple_flat_project(tmp_path) -> None:
    write_sample_project(tmp_path)
    analyzer = AnalyzerEngine()
    generator = GeneratorEngine()
    analysis = analyzer.analyze_project(tmp_path)
    generated_suite = generator.generate(analysis, tmp_path / "tests" / "test_generated_suite.py")

    repository_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = (
        str(repository_root)
        if not environment.get("PYTHONPATH")
        else str(repository_root) + os.pathsep + environment["PYTHONPATH"]
    )

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(generated_suite)],
        cwd=str(tmp_path),
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
