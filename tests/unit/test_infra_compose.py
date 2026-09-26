from __future__ import annotations

from engine.infra.manager import (
    POSTGRES_HOST_PORT,
    REDIS_HOST_PORT,
    InfraManager,
    speculast_compose_path,
)


def test_create_compose_file_writes_under_speculast_and_leaves_project_compose(tmp_path) -> None:
    project_compose = tmp_path / "docker-compose.yaml"
    project_compose.write_text("services:\n  app:\n    image: demo\n", encoding="utf-8")

    output_path = InfraManager().create_compose_file(tmp_path, ["postgresql", "redis"])

    assert output_path == speculast_compose_path(tmp_path)
    assert output_path is not None
    assert output_path.is_file()
    assert project_compose.read_text(encoding="utf-8") == "services:\n  app:\n    image: demo\n"
    compose_text = output_path.read_text(encoding="utf-8")
    assert f"{POSTGRES_HOST_PORT}:5432" in compose_text
    assert f"{REDIS_HOST_PORT}:6379" in compose_text


def test_create_compose_file_returns_none_without_required_infra(tmp_path) -> None:
    assert InfraManager().create_compose_file(tmp_path, []) is None
    assert not speculast_compose_path(tmp_path).exists()
    assert not (tmp_path / "docker-compose.yaml").exists()
