from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from main import (
    build_report_output_path,
    build_report_day_directory_for_timestamp,
    cleanup_old_reports,
    cleanup_temp_artifacts,
    ensure_report_day_directory,
    ensure_reports_directory,
    migrate_legacy_report_artifacts,
    should_cleanup_temp_artifact,
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


def test_should_cleanup_temp_artifact_preserves_known_config_entries(tmp_path) -> None:
    preserved_names = (".git", ".idea", ".venv", ".gitignore", ".env")

    for name in preserved_names:
        candidate = tmp_path / name
        if "." in name[1:]:
            candidate.write_text("keep", encoding="utf-8")
        else:
            candidate.mkdir(parents=True, exist_ok=True)
        assert not should_cleanup_temp_artifact(candidate)


def test_cleanup_temp_artifacts_removes_root_temp_noise_only(tmp_path) -> None:
    removable_directory = tmp_path / ".browser-check-profile"
    removable_tmp_directory = tmp_path / ".tmp_chrome_report_test"
    removable_cache_directory = tmp_path / "__pycache__"
    removable_dot_file = tmp_path / ".coverage"
    removable_artifacts_directory = tmp_path / ".speculast"
    preserved_reports = tmp_path / "reports"
    preserved_engine = tmp_path / "engine"
    preserved_gitignore = tmp_path / ".gitignore"

    removable_directory.mkdir(parents=True, exist_ok=True)
    removable_tmp_directory.mkdir(parents=True, exist_ok=True)
    removable_cache_directory.mkdir(parents=True, exist_ok=True)
    removable_artifacts_directory.mkdir(parents=True, exist_ok=True)
    preserved_reports.mkdir(parents=True, exist_ok=True)
    preserved_engine.mkdir(parents=True, exist_ok=True)
    removable_dot_file.write_text("coverage", encoding="utf-8")
    preserved_gitignore.write_text("keep", encoding="utf-8")

    removed_artifacts = cleanup_temp_artifacts(tmp_path)

    assert set(removed_artifacts) == {
        removable_directory.resolve(),
        removable_tmp_directory.resolve(),
        removable_cache_directory.resolve(),
        removable_dot_file.resolve(),
        removable_artifacts_directory.resolve(),
    }
    assert not removable_directory.exists()
    assert not removable_tmp_directory.exists()
    assert not removable_cache_directory.exists()
    assert not removable_dot_file.exists()
    assert not removable_artifacts_directory.exists()
    assert preserved_reports.exists()
    assert preserved_engine.exists()
    assert preserved_gitignore.exists()
