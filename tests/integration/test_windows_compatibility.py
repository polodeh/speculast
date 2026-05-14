from __future__ import annotations

from engine.analyzer.engine import AnalyzerEngine


def test_analyzer_accepts_python_files_with_utf8_bom(tmp_path) -> None:
    source_path = tmp_path / "windows_bom_module.py"
    source_path.write_text(
        '\ufeffdef normalize() -> str:\n    return "ok"\n',
        encoding="utf-8",
    )

    analysis = AnalyzerEngine().analyze_project(tmp_path)

    assert len(analysis.functions) == 1
    assert analysis.functions[0].module == "windows_bom_module"
    assert analysis.functions[0].qualname == "normalize"
