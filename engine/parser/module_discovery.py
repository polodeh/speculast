"""Utilities for reading Python modules and mapping them to imports."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path

from ..core.models import FunctionSchema

KNOWN_SOURCE_ROOT_NAMES = frozenset({"src"})


def read_python_source(file_path: Path) -> str:
    """Read Python source while transparently ignoring a UTF-8 BOM marker."""

    return file_path.read_text(encoding="utf-8-sig")


def detect_source_root(file_path: Path, project_root: Path) -> Path:
    """Resolve the import root for a file, including common src/ layouts."""

    resolved_root = project_root.resolve()
    resolved_file = file_path.resolve()
    try:
        relative_parts = resolved_file.relative_to(resolved_root).parts
    except ValueError:
        return resolved_root

    for index, part in enumerate(relative_parts[:-1]):
        if part in KNOWN_SOURCE_ROOT_NAMES:
            return resolved_root.joinpath(*relative_parts[: index + 1]).resolve()

    return resolved_root


def collect_source_roots(file_paths: Sequence[Path], project_root: Path) -> tuple[Path, ...]:
    """Collect unique source roots for analyzed files."""

    ordered_roots: OrderedDict[Path, None] = OrderedDict()
    for file_path in file_paths:
        ordered_roots.setdefault(detect_source_root(file_path, project_root), None)
    return tuple(ordered_roots)


def derive_module_name(file_path: Path, module_root: Path) -> str:
    """Return the importable module name for a Python file under a project root."""

    try:
        relative_path = file_path.resolve().relative_to(module_root.resolve())
    except ValueError:
        return file_path.stem

    module_parts = list(relative_path.with_suffix("").parts)
    if module_parts and module_parts[-1] == "__init__":
        module_parts.pop()
    return ".".join(module_parts) or module_root.name


def build_module_members(functions: Sequence[FunctionSchema]) -> dict[str, list[str]]:
    """Group discovered functions and owning classes by module for template imports."""

    grouped: OrderedDict[str, list[str]] = OrderedDict()
    ordered_functions = sorted(
        functions,
        key=lambda function: (
            function.file_path.as_posix(),
            function.lineno,
            function.qualname,
        ),
    )

    for function in ordered_functions:
        members = grouped.setdefault(function.module, [])
        member_name = (
            function.qualname.split(".", maxsplit=1)[0]
            if function.class_name is not None
            else function.name
        )
        if member_name not in members:
            members.append(member_name)

    return dict(grouped)
