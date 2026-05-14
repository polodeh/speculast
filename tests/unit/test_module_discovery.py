from __future__ import annotations

from pathlib import Path

from engine.core.models import FunctionSchema
from engine.parser import build_module_members, collect_source_roots, derive_module_name, detect_source_root


def build_function(
    *,
    module: str,
    file_path: Path,
    name: str,
    qualname: str | None = None,
    lineno: int = 1,
    class_name: str | None = None,
) -> FunctionSchema:
    return FunctionSchema(
        name=name,
        qualname=qualname or name,
        module=module,
        file_path=file_path.resolve(),
        lineno=lineno,
        end_lineno=lineno,
        node_hash="0" * 64,
        class_name=class_name,
        is_method=class_name is not None,
    )


def test_derive_module_name_uses_project_relative_import_paths(tmp_path) -> None:
    calculator = tmp_path / "calculator.py"
    nested_package = tmp_path / "services"
    nested_package.mkdir(parents=True, exist_ok=True)
    nested_init = nested_package / "__init__.py"
    nested_module = nested_package / "pricing.py"

    calculator.write_text("def add(a, b): return a + b\n", encoding="utf-8")
    nested_init.write_text("", encoding="utf-8")
    nested_module.write_text("def total(items): return sum(items)\n", encoding="utf-8")

    assert derive_module_name(calculator, tmp_path) == "calculator"
    assert derive_module_name(nested_init, tmp_path) == "services"
    assert derive_module_name(nested_module, tmp_path) == "services.pricing"


def test_build_module_members_groups_top_level_functions_and_classes(tmp_path) -> None:
    calculator_path = tmp_path / "calculator.py"
    strings_path = tmp_path / "strings.py"
    calculator_path.write_text("", encoding="utf-8")
    strings_path.write_text("", encoding="utf-8")

    functions = (
        build_function(module="calculator", file_path=calculator_path, name="add", lineno=1),
        build_function(
            module="calculator",
            file_path=calculator_path,
            name="increment",
            qualname="Counter.increment",
            lineno=10,
            class_name="Counter",
        ),
        build_function(module="strings", file_path=strings_path, name="shout", lineno=1),
    )

    assert build_module_members(functions) == {
        "calculator": ["add", "Counter"],
        "strings": ["shout"],
    }


def test_detect_source_root_prefers_src_layout_for_nested_packages(tmp_path) -> None:
    source_root = tmp_path / "src"
    nested_module = source_root / "myapp" / "utils" / "helper.py"
    nested_module.parent.mkdir(parents=True, exist_ok=True)
    nested_module.write_text("def slugify(value): return value\n", encoding="utf-8")

    assert detect_source_root(nested_module, tmp_path) == source_root.resolve()
    assert derive_module_name(nested_module, source_root) == "myapp.utils.helper"
    assert collect_source_roots((nested_module,), tmp_path) == (source_root.resolve(),)
