from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType


REQUIRED_SAMPLE_MODULES = (
    "__init__.py",
    "database.py",
    "logic.py",
    "models.py",
    "service.py",
)


def discover_sample_project_package() -> str:
    repository_root = Path(__file__).resolve().parents[2]

    for candidate in sorted(repository_root.iterdir()):
        if not candidate.is_dir():
            continue
        if all((candidate / required_file).is_file() for required_file in REQUIRED_SAMPLE_MODULES):
            return candidate.name

    raise RuntimeError("Unable to discover the bundled sample project package.")


SAMPLE_PROJECT_PACKAGE = discover_sample_project_package()


def load_sample_module(module_name: str) -> ModuleType:
    return importlib.import_module(f"{SAMPLE_PROJECT_PACKAGE}.{module_name}")
