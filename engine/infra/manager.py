"""Infrastructure planning layer for speculast."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..core.models import AnalysisResult, DependencySchema
from ..core.protocols import IInfraManager
from .registry import DependencyRegistry


class InfraManager(IInfraManager):
    """Small infrastructure manager that turns imports into container requirements."""

    COMPOSE_SERVICE_NAMES: Mapping[str, str] = {
        "postgresql": "db",
        "redis": "cache",
    }

    def __init__(self, *, registry: DependencyRegistry | None = None) -> None:
        self.registry = registry or DependencyRegistry()

    def detect_required_infra(self, analysis: AnalysisResult, /) -> list[str]:
        """Detect required infrastructure services from project imports."""

        return self.registry.detect(analysis.project.imports)

    def enrich_analysis(self, analysis: AnalysisResult, /) -> AnalysisResult:
        """Return analysis metadata with required infrastructure attached."""

        required_infra = self.detect_required_infra(analysis)
        return analysis.model_copy(update={"required_infra": required_infra})

    def resolve_dependency(self, dependency: DependencySchema, /) -> DependencySchema:
        """Return dependency metadata unchanged in the initial implementation."""

        return dependency

    def plan_environment(self, required_infra: Sequence[str], /) -> Mapping[str, str]:
        """Map service identifiers to Docker images."""

        return self.registry.plan(required_infra)

    def create_compose_file(self, project_root: Path, required_infra: Sequence[str], /) -> Path | None:
        """Create docker-compose.yaml in the project root for detected services."""

        resolved_root = project_root.resolve()
        compose_content = self._build_compose_content(required_infra)
        if compose_content is None:
            return None

        output_path = resolved_root / "docker-compose.yaml"
        output_path.write_text(compose_content, encoding="utf-8")
        return output_path

    @classmethod
    def compose_service_names(cls, required_infra: Sequence[str], /) -> list[str]:
        """Return compose service names that correspond to the detected infrastructure."""

        service_names: list[str] = []
        for service_name in required_infra:
            compose_name = cls.COMPOSE_SERVICE_NAMES.get(service_name)
            if compose_name is not None:
                service_names.append(compose_name)
        return list(dict.fromkeys(service_names))

    @staticmethod
    def _build_compose_content(required_infra: Sequence[str]) -> str | None:
        normalized_services = list(dict.fromkeys(required_infra))
        if not normalized_services:
            return None

        lines: list[str] = ["services:"]

        if "postgresql" in normalized_services:
            lines.extend(
                [
                    "  db:",
                    "    image: postgres:16-alpine",
                    "    environment:",
                    "      POSTGRES_DB: app",
                    "      POSTGRES_USER: app",
                    "      POSTGRES_PASSWORD: app",
                    "      POSTGRES_HOST_AUTH_METHOD: trust",
                    "    ports:",
                    '      - "55432:5432"',
                    "    healthcheck:",
                    '      test: ["CMD-SHELL", "pg_isready -U app -d app"]',
                    "      interval: 5s",
                    "      timeout: 5s",
                    "      retries: 5",
                ]
            )

        if "redis" in normalized_services:
            lines.extend(
                [
                    "  cache:",
                    "    image: redis:7-alpine",
                    "    ports:",
                    '      - "6379:6379"',
                    "    healthcheck:",
                    '      test: ["CMD", "redis-cli", "ping"]',
                    "      interval: 5s",
                    "      timeout: 3s",
                    "      retries: 10",
                ]
            )

        return "\n".join(lines) + "\n"
