from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from engine.analyzer.engine import AnalyzerEngine
from engine.generator.engine import GeneratorEngine


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


def test_analyzer_reads_python_files_with_utf8_bom(tmp_path) -> None:
    module_path = tmp_path / "bom_sample.py"
    module_path.write_text(
        '\ufeffdef ping() -> str:\n    return "pong"\n',
        encoding="utf-8",
    )

    analysis = AnalyzerEngine().analyze_project(tmp_path)

    assert [function.qualname for function in analysis.functions] == ["ping"]
    assert analysis.functions[0].module == "bom_sample"


def test_generated_suite_handles_json_config_paths(tmp_path) -> None:
    (tmp_path / "config_loader.py").write_text(
        "\n".join(
            [
                "import json",
                "",
                "def load_config(config_path) -> dict[str, object]:",
                '    with open(config_path, encoding="utf-8") as stream:',
                "        return json.load(stream)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analyzer = AnalyzerEngine()
    generator = GeneratorEngine()
    analysis = analyzer.analyze_project(tmp_path)
    generated_suite = generator.generate(analysis, tmp_path / "tests" / "test_generated_suite.py")
    suite_text = generated_suite.read_text(encoding="utf-8")

    assert "json.dumps(payload)" in suite_text
    assert "_build_json_file" in suite_text

    completed = _run_generated_suite(tmp_path, generated_suite)

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_generated_suite_auto_mocks_requests_calls(tmp_path) -> None:
    stubs_root = tmp_path / "_stubs"
    stubs_root.mkdir(parents=True, exist_ok=True)
    (stubs_root / "requests.py").write_text(
        "\n".join(
            [
                "def get(url, *args, **kwargs):",
                '    raise RuntimeError(f"real network call attempted: {url}")',
                "",
                "def post(url, *args, **kwargs):",
                '    raise RuntimeError(f"real network call attempted: {url}")',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "http_client.py").write_text(
        "\n".join(
            [
                "import sys",
                "from pathlib import Path",
                "",
                'sys.path.insert(0, str(Path(__file__).resolve().parent / "_stubs"))',
                "import requests",
                "",
                "def fetch_status(url: str) -> int:",
                "    response = requests.get(url)",
                "    return response.status_code",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analyzer = AnalyzerEngine(excluded_directories=AnalyzerEngine.DEFAULT_EXCLUDED_DIRECTORIES | {"_stubs"})
    generator = GeneratorEngine()
    analysis = analyzer.analyze_project(tmp_path)
    generated_suite = generator.generate(analysis, tmp_path / "tests" / "test_generated_suite.py")
    suite_text = generated_suite.read_text(encoding="utf-8")

    assert "requests.get" in suite_text
    assert "status_code = 200" in suite_text
    assert "https://example.com" in suite_text

    completed = _run_generated_suite(tmp_path, generated_suite)

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_analyzer_tolerates_missing_installed_dependencies(tmp_path) -> None:
    (tmp_path / "resilient_module.py").write_text(
        "\n".join(
            [
                "import unknown_lib",
                "",
                "def fallback_value() -> str:",
                '    return "ok"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analysis = AnalyzerEngine().analyze_project(tmp_path)

    assert analysis.project.imports == ["unknown_lib"]
    assert [function.qualname for function in analysis.functions] == ["fallback_value"]


def test_generated_suite_executes_for_async_decorated_functions_without_type_hints(tmp_path) -> None:
    (tmp_path / "modern_module.py").write_text(
        "\n".join(
            [
                "def passthrough(func):",
                "    async def wrapper(*args, **kwargs):",
                "        return await func(*args, **kwargs)",
                "    return wrapper",
                "",
                "@passthrough",
                "async def greet(raw):",
                "    return raw",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analyzer = AnalyzerEngine()
    generator = GeneratorEngine()
    analysis = analyzer.analyze_project(tmp_path)
    generated_suite = generator.generate(analysis, tmp_path / "tests" / "test_generated_suite.py")
    suite_text = generated_suite.read_text(encoding="utf-8")

    assert "generated_str" in suite_text

    completed = _run_generated_suite(tmp_path, generated_suite)

    assert completed.returncode == 0, completed.stdout + completed.stderr
