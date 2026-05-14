"""Infrastructure dependency registry for speculast."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class DependencyRegistry:
    """Maps imported Python packages to infrastructure requirements."""

    POSTGRESQL_IMPORTS = frozenset({"sqlalchemy", "psycopg2", "asyncpg"})
    REDIS_IMPORTS = frozenset({"redis"})

    INFRA_IMAGES: Mapping[str, str] = {
        "postgresql": "postgres:16-alpine",
        "redis": "redis:7-alpine",
    }

    def detect(self, imports: Sequence[str], /) -> list[str]:
        """Detect required services from normalized import statements."""

        normalized_imports = {self._normalize_import(import_name) for import_name in imports}
        normalized_imports.discard("")

        required_infra: list[str] = []
        if normalized_imports & self.POSTGRESQL_IMPORTS:
            required_infra.append("postgresql")
        if normalized_imports & self.REDIS_IMPORTS:
            required_infra.append("redis")
        return required_infra

    def plan(self, required_infra: Sequence[str], /) -> dict[str, str]:
        """Build a Docker image plan for the requested services."""

        plan: dict[str, str] = {}
        for service_name in required_infra:
            if service_name in self.INFRA_IMAGES:
                plan[service_name] = self.INFRA_IMAGES[service_name]
        return plan

    @staticmethod
    def _normalize_import(import_name: str) -> str:
        import_name = import_name.strip()
        if not import_name:
            return ""

        if import_name.startswith("from "):
            module_part = import_name[5:].split(" import ", maxsplit=1)[0].lstrip(".")
        else:
            module_part = import_name.split(" as ", maxsplit=1)[0]

        return module_part.split(".", maxsplit=1)[0]
