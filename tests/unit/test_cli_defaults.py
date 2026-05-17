from __future__ import annotations

from pathlib import Path

import pytest

from engine.analyzer.engine import AnalyzerEngine
from main import (
    ASCII_LOGO,
    BANNER_SUBTITLE,
    NoAnalyzableFilesError,
    build_parser,
    configure_windows_utf8_streams,
    open_generated_report,
    resolve_cli_settings,
    run_analysis,
)


def test_build_parser_defaults_to_current_directory_and_full_auto(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    parser = build_parser("en")

    args = parser.parse_args([])
    settings = resolve_cli_settings(args)

    assert parser.prog == "speculast"
    assert settings.input_path == tmp_path.resolve()
    assert settings.run_tests is True
    assert settings.generate_report is True
    assert settings.use_real_db is True
    assert settings.cleanup_temp is True
    assert settings.cleanup_reports is False


def test_cli_opt_out_flags_disable_full_auto_features() -> None:
    parser = build_parser("en")

    args = parser.parse_args(
        [
            "--no-tests",
            "--no-viz",
            "--no-real-db",
            "--no-cleanup",
            "--cleanup-reports",
            "--report-retention-days",
            "3",
            "sample_project",
        ]
    )
    settings = resolve_cli_settings(args)

    assert settings.input_path == Path("sample_project").resolve()
    assert settings.run_tests is False
    assert settings.generate_report is False
    assert settings.use_real_db is False
    assert settings.cleanup_temp is False
    assert settings.cleanup_reports is True
    assert settings.report_retention_days == 3


def test_open_generated_report_uses_file_uri(monkeypatch, tmp_path) -> None:
    report_path = (tmp_path / "reports" / "2026-05-14" / "report_101010.html").resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("<html></html>", encoding="utf-8")
    captured: list[str] = []

    def fake_open(target: str) -> bool:
        captured.append(target)
        return True

    monkeypatch.setattr("main.webbrowser.open", fake_open)

    assert open_generated_report(report_path) is True
    assert captured == [report_path.as_uri()]


def test_open_generated_report_returns_false_when_path_is_missing() -> None:
    assert open_generated_report(None) is False


def test_banner_branding_uses_lowercase_speculast() -> None:
    non_empty_lines = [line for line in ASCII_LOGO.strip("\n").splitlines() if line.strip()]

    assert len(non_empty_lines) >= 5
    assert "___ _ __" in ASCII_LOGO
    assert "|___/ .__/" in ASCII_LOGO
    assert "\u0430\u0432\u0442\u043e\u043d\u043e\u043c\u043d\u044b\u0439 \u0436\u0438\u0437\u043d\u0435\u043d\u043d\u044b\u0439 \u0446\u0438\u043a\u043b" == BANNER_SUBTITLE


def test_run_analysis_uses_friendly_message_for_empty_project(tmp_path) -> None:
    with pytest.raises(
        NoAnalyzableFilesError,
        match="\u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u043a\u043e\u0434, \u0438 \u044f \u0432\u0435\u0440\u043d\u0443\u0441\u044c!",
    ):
        run_analysis(AnalyzerEngine(), tmp_path, "ru")


def test_run_analysis_uses_friendly_message_for_blank_python_files(tmp_path) -> None:
    (tmp_path / "empty_module.py").write_text("\n\n", encoding="utf-8")

    with pytest.raises(
        NoAnalyzableFilesError,
        match="\u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u043a\u043e\u0434, \u0438 \u044f \u0432\u0435\u0440\u043d\u0443\u0441\u044c!",
    ):
        run_analysis(AnalyzerEngine(), tmp_path, "ru")


def test_configure_windows_utf8_streams_reconfigures_stdout_and_stderr_on_win32(monkeypatch) -> None:
    class DummyStream:
        def __init__(self) -> None:
            self.calls: list[dict[str, str]] = []

        def reconfigure(self, *, encoding: str) -> None:
            self.calls.append({"encoding": encoding})

    stdout = DummyStream()
    stderr = DummyStream()

    monkeypatch.setattr("main.sys.platform", "win32")
    monkeypatch.setattr("main.sys.stdout", stdout)
    monkeypatch.setattr("main.sys.stderr", stderr)

    configure_windows_utf8_streams()

    assert stdout.calls == [{"encoding": "utf-8"}]
    assert stderr.calls == [{"encoding": "utf-8"}]
