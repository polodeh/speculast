from __future__ import annotations

from engine.visualizer.dashboard import DashboardBuilder


def test_dashboard_title_uses_speculast_branding() -> None:
    builder = DashboardBuilder(lang="en")

    assert builder._build_ui_for("en")["html_title"] == "speculast dashboard"
    assert builder._build_ui_for("ru")["html_title"] == "speculast dashboard"
