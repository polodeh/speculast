from __future__ import annotations

from pathlib import Path

from main import ASCII_LOGO, BANNER_SUBTITLE, build_parser, open_generated_report, resolve_cli_settings


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
            "demo_shop",
        ]
    )
    settings = resolve_cli_settings(args)

    assert settings.input_path == Path("demo_shop").resolve()
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
    assert "автономный жизненный цикл" == BANNER_SUBTITLE
