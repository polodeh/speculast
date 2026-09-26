from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from main import (
    build_generated_test_environment,
    build_report_output_path,
    build_report_day_directory_for_timestamp,
    build_speculast_compose_command,
    cleanup_old_reports,
    cleanup_temp_artifacts,
    ensure_report_day_directory,
    ensure_reports_directory,
    migrate_legacy_report_artifacts,
    should_cleanup_temp_artifact,
    stop_speculast_compose_best_effort,
)


def test_ensure_reports_directory_creates_reports_folder(tmp_path) -> None:
    reports_directory = ensure_reports_directory(tmp_path)

    assert reports_directory == (tmp_path / "reports").resolve()
    assert reports_directory.is_dir()


def test_ensure_report_day_directory_creates_nested_date_folder(tmp_path) -> None:
    generated_at = datetime(2026, 5, 14, 13, 15, 30)

    report_day_directory = ensure_report_day_directory(tmp_path, report_date=generated_at)

    assert report_day_directory == (tmp_path / "reports" / "2026-05-14").resolve()
    assert report_day_directory.is_dir()


def test_build_report_day_directory_for_timestamp_uses_formatted_date(tmp_path) -> None:
    generated_at = datetime(2026, 5, 13, 22, 10, 5)
    reports_directory = ensure_reports_directory(tmp_path)

    report_day_directory = build_report_day_directory_for_timestamp(
        generated_at,
        reports_directory=reports_directory,
    )

    assert report_day_directory == (tmp_path / "reports" / "2026-05-13").resolve()
    assert report_day_directory.is_dir()


def test_build_report_output_path_uses_date_folder_time_name_and_suffix(tmp_path) -> None:
    generated_at = datetime(2026, 5, 14, 13, 15, 30)

    first_candidate = build_report_output_path(tmp_path, generated_at=generated_at)
    assert first_candidate == (
        tmp_path / "reports" / "2026-05-14" / "report_131530.html"
    ).resolve()

    first_candidate.write_text("existing", encoding="utf-8")
    second_candidate = build_report_output_path(tmp_path, generated_at=generated_at)

    assert second_candidate == (
        tmp_path / "reports" / "2026-05-14" / "report_131530_01.html"
    ).resolve()


def test_migrate_legacy_report_artifacts_moves_root_files_into_date_folders(tmp_path) -> None:
    reports_directory = ensure_reports_directory(tmp_path)
    legacy_html = tmp_path / "report.html"
    legacy_png = tmp_path / "report-check-en.png"
    untouched = tmp_path / "notes.txt"

    legacy_html.write_text("html", encoding="utf-8")
    legacy_png.write_text("png", encoding="utf-8")
    untouched.write_text("keep", encoding="utf-8")

    html_timestamp = datetime(2026, 5, 14, 15, 8, 16).timestamp()
    png_timestamp = datetime(2026, 5, 3, 2, 17, 5).timestamp()
    os.utime(legacy_html, (html_timestamp, html_timestamp))
    os.utime(legacy_png, (png_timestamp, png_timestamp))

    migrated_paths = migrate_legacy_report_artifacts(tmp_path, reports_directory=reports_directory)

    assert set(migrated_paths) == {
        (tmp_path / "reports" / "2026-05-14" / "report.html").resolve(),
        (tmp_path / "reports" / "2026-05-03" / "report-check-en.png").resolve(),
    }
    assert not legacy_html.exists()
    assert not legacy_png.exists()
    assert untouched.exists()


def test_cleanup_old_reports_recurses_into_date_folders_and_prunes_empty_ones(tmp_path) -> None:
    now = datetime(2026, 5, 14, 13, 15, 30)
    reports_directory = ensure_reports_directory(tmp_path)
    expired_day_directory = reports_directory / "2026-05-01"
    recent_day_directory = reports_directory / "2026-05-13"
    expired_day_directory.mkdir(parents=True, exist_ok=True)
    recent_day_directory.mkdir(parents=True, exist_ok=True)
    expired_report = expired_day_directory / "report_101010.html"
    expired_png = expired_day_directory / "report-check.png"
    recent_report = recent_day_directory / "report_101010.html"
    unrelated_file = reports_directory / "notes.txt"

    expired_report.write_text("old", encoding="utf-8")
    expired_png.write_text("old-png", encoding="utf-8")
    recent_report.write_text("fresh", encoding="utf-8")
    unrelated_file.write_text("keep", encoding="utf-8")

    expired_timestamp = (now - timedelta(days=8)).timestamp()
    recent_timestamp = (now - timedelta(days=2)).timestamp()
    os.utime(expired_report, (expired_timestamp, expired_timestamp))
    os.utime(expired_png, (expired_timestamp, expired_timestamp))
    os.utime(recent_report, (recent_timestamp, recent_timestamp))

    removed_reports = cleanup_old_reports(tmp_path, retention_days=7, now=now)

    assert set(removed_reports) == {expired_report.resolve(), expired_png.resolve()}
    assert not expired_report.exists()
    assert not expired_png.exists()
    assert not expired_day_directory.exists()
    assert recent_report.exists()
    assert recent_day_directory.exists()
    assert unrelated_file.exists()


def test_cleanup_old_reports_rejects_negative_retention_days(tmp_path) -> None:
    with pytest.raises(ValueError, match="report_retention_days"):
        cleanup_old_reports(tmp_path, retention_days=-1)


def test_should_cleanup_temp_artifact_only_matches_speculast_directory(tmp_path) -> None:
    preserved_names = (
        ".git",
        ".github",
        ".dockerignore",
        ".pre-commit-config.yaml",
        ".idea",
        ".venv",
        ".gitignore",
        ".env",
        ".coverage",
        "__pycache__",
        "tmp_session.log",
    )

    for name in preserved_names:
        candidate = tmp_path / name
        assert not should_cleanup_temp_artifact(candidate)

    assert should_cleanup_temp_artifact(tmp_path / ".speculast")


def test_cleanup_temp_artifacts_removes_only_speculast_directory(tmp_path) -> None:
    removable_artifacts_directory = tmp_path / ".speculast"
    preserved_github = tmp_path / ".github"
    preserved_dockerignore = tmp_path / ".dockerignore"
    preserved_pre_commit = tmp_path / ".pre-commit-config.yaml"
    preserved_browser_profile = tmp_path / ".browser-check-profile"
    preserved_coverage = tmp_path / ".coverage"
    preserved_tmp_file = tmp_path / "tmp_session.log"
    preserved_reports = tmp_path / "reports"
    preserved_project_compose = tmp_path / "docker-compose.yaml"

    removable_artifacts_directory.mkdir(parents=True, exist_ok=True)
    (removable_artifacts_directory / "pytest-report.json").write_text("{}", encoding="utf-8")
    preserved_github.mkdir(parents=True, exist_ok=True)
    preserved_browser_profile.mkdir(parents=True, exist_ok=True)
    preserved_reports.mkdir(parents=True, exist_ok=True)
    preserved_dockerignore.write_text("keep", encoding="utf-8")
    preserved_pre_commit.write_text("keep", encoding="utf-8")
    preserved_coverage.write_text("coverage", encoding="utf-8")
    preserved_tmp_file.write_text("session", encoding="utf-8")
    preserved_project_compose.write_text("services: {}\n", encoding="utf-8")

    removed_artifacts = cleanup_temp_artifacts(tmp_path)

    assert removed_artifacts == (removable_artifacts_directory.resolve(),)
    assert not removable_artifacts_directory.exists()
    assert preserved_github.exists()
    assert preserved_dockerignore.exists()
    assert preserved_pre_commit.exists()
    assert preserved_browser_profile.exists()
    assert preserved_coverage.exists()
    assert preserved_tmp_file.exists()
    assert preserved_reports.exists()
    assert preserved_project_compose.exists()


def test_build_speculast_compose_command_can_stop_project_without_compose_file(tmp_path) -> None:
    command = build_speculast_compose_command(tmp_path, "down", "--remove-orphans")

    assert command == ["docker", "compose", "-p", "speculast", "down", "--remove-orphans"]


def test_build_speculast_compose_command_uses_isolated_project_and_file(tmp_path) -> None:
    compose_file = tmp_path / ".speculast" / "docker-compose.yaml"
    compose_file.parent.mkdir(parents=True, exist_ok=True)
    compose_file.write_text("services: {}\n", encoding="utf-8")

    command = build_speculast_compose_command(tmp_path, "up", "-d", require_compose_file=True)

    assert command[:4] == ["docker", "compose", "-p", "speculast"]
    assert command[4:6] == ["-f", str(compose_file.resolve())]
    assert command[6:] == ["up", "-d"]


def test_stop_speculast_compose_best_effort_skips_when_docker_is_missing(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("main.shutil.which", lambda _name: None)

    def fail_run_subprocess(*_args, **_kwargs):
        raise AssertionError("docker must not be invoked when it is unavailable")

    monkeypatch.setattr("main.run_subprocess", fail_run_subprocess)
    stop_speculast_compose_best_effort(tmp_path)


def test_build_generated_test_environment_points_coverage_file_at_speculast(tmp_path) -> None:
    artifacts_root = tmp_path / ".speculast"
    artifacts_root.mkdir(parents=True, exist_ok=True)

    environment = build_generated_test_environment(artifacts_root)

    assert environment["COVERAGE_FILE"] == str((artifacts_root / "coverage.db").resolve())
