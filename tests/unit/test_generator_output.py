from __future__ import annotations

from pathlib import Path

from engine.analyzer.engine import AnalyzerEngine
from engine.generator.engine import GeneratorEngine


def _generate_suite(tmp_path: Path, files: dict[str, str]) -> str:
    for relative_path, source in files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")

    analysis = AnalyzerEngine().analyze_project(tmp_path)
    generated_suite = GeneratorEngine().generate(analysis, tmp_path / "tests" / "test_generated_suite.py")
    return generated_suite.read_text(encoding="utf-8")


def test_generator_output_uses_dynamic_imports_for_my_app(tmp_path) -> None:
    legacy_import_prefix = "from " + "demo" + "_shop"
    suite_text = _generate_suite(
        tmp_path,
        {
            "my_app.py": "\n".join(
                [
                    "def compute_total(value: int) -> int:",
                    "    return value + 1",
                ]
            )
            + "\n",
        },
    )

    assert legacy_import_prefix not in suite_text
    assert "from my_app import compute_total" in suite_text


def test_generator_output_writes_json_fixture_for_json_load_paths(tmp_path) -> None:
    suite_text = _generate_suite(
        tmp_path,
        {
            "config_reader.py": "\n".join(
                [
                    "import json",
                    "",
                    "def read_config(config_path):",
                    '    with open(config_path, encoding="utf-8") as stream:',
                    "        return json.load(stream)",
                ]
            )
            + "\n",
        },
    )

    assert "tmp_path: Path" in suite_text
    assert "_build_json_file" in suite_text
    assert "json.dumps(payload)" in suite_text
    assert "{}" in suite_text


def test_generator_output_uses_nested_package_imports_for_src_layout(tmp_path) -> None:
    suite_text = _generate_suite(
        tmp_path,
        {
            "src/myapp/logic.py": "\n".join(
                [
                    "def compute_total(value: int) -> int:",
                    "    return value + 1",
                ]
            )
            + "\n",
            "src/myapp/utils/helper.py": "\n".join(
                [
                    "def slugify(value: str) -> str:",
                    '    return value.replace(" ", "-")',
                ]
            )
            + "\n",
        },
    )

    assert "from myapp.logic import compute_total" in suite_text
    assert "from myapp.utils.helper import slugify" in suite_text


def test_generator_output_auto_mocks_http_requests(tmp_path) -> None:
    suite_text = _generate_suite(
        tmp_path,
        {
            "http_client.py": "\n".join(
                [
                    "import requests",
                    "",
                    "def fetch_status(url: str) -> int:",
                    "    response = requests.get(url)",
                    "    return response.status_code",
                ]
            )
            + "\n",
        },
    )

    assert "monkeypatch: pytest.MonkeyPatch" in suite_text
    assert "status_code = 200" in suite_text
    assert "requests.get(" not in suite_text
