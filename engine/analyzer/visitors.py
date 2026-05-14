"""AST visitors responsible for building semantic models."""

from __future__ import annotations

import ast
import copy
import hashlib
from collections.abc import Iterable
from pathlib import Path

from ..core.models import ArgumentKind, ArgumentSchema, FunctionSchema

type FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef
type FunctionKey = tuple[str, int]


class BaseVisitor(ast.NodeVisitor):
    """Base visitor with shared AST normalization helpers."""

    def __init__(
        self,
        *,
        file_path: Path,
        module_name: str,
        include_private: bool = False,
    ) -> None:
        self.file_path = file_path.resolve()
        self.module_name = module_name
        self.include_private = include_private
        self._class_stack: list[str] = []
        self._function_depth = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._class_stack.pop()

    @staticmethod
    def render_node(node: ast.AST | None) -> str | None:
        if node is None:
            return None
        return ast.unparse(node)

    @staticmethod
    def strip_docstring(statements: list[ast.stmt]) -> list[ast.stmt]:
        if not statements:
            return statements

        first_statement = statements[0]
        if not isinstance(first_statement, ast.Expr):
            return statements
        if not isinstance(first_statement.value, ast.Constant):
            return statements
        if not isinstance(first_statement.value.value, str):
            return statements
        return statements[1:]

    @classmethod
    def build_node_hash(cls, node: FunctionNode) -> str:
        normalized = copy.deepcopy(node)
        normalized.body = cls.strip_docstring(normalized.body)
        ast.fix_missing_locations(normalized)
        normalized_source = ast.unparse(normalized)
        return hashlib.sha256(normalized_source.encode("utf-8")).hexdigest()

    def is_public_definition(self, name: str) -> bool:
        return self.include_private or not name.startswith("_")

    def current_class_name(self) -> str | None:
        if not self._class_stack:
            return None
        return self._class_stack[-1]

    def build_qualname(self, name: str) -> str:
        if not self._class_stack:
            return name
        return ".".join((*self._class_stack, name))

    def build_function_key(self, node: FunctionNode) -> FunctionKey:
        return (self.build_qualname(node.name), node.lineno)

    def build_arguments(self, arguments: ast.arguments) -> tuple[ArgumentSchema, ...]:
        schemas: list[ArgumentSchema] = []
        positional_arguments = [*arguments.posonlyargs, *arguments.args]
        positional_defaults = [None] * (len(positional_arguments) - len(arguments.defaults))
        positional_defaults.extend(arguments.defaults)

        for index, argument in enumerate(arguments.posonlyargs):
            schemas.append(
                self.build_argument_schema(
                    argument=argument,
                    kind=ArgumentKind.POSITIONAL_ONLY,
                    default_node=positional_defaults[index],
                )
            )

        for offset, argument in enumerate(arguments.args, start=len(arguments.posonlyargs)):
            schemas.append(
                self.build_argument_schema(
                    argument=argument,
                    kind=ArgumentKind.POSITIONAL_OR_KEYWORD,
                    default_node=positional_defaults[offset],
                )
            )

        if arguments.vararg is not None:
            schemas.append(
                self.build_argument_schema(
                    argument=arguments.vararg,
                    kind=ArgumentKind.VAR_POSITIONAL,
                    default_node=None,
                )
            )

        for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True):
            schemas.append(
                self.build_argument_schema(
                    argument=argument,
                    kind=ArgumentKind.KEYWORD_ONLY,
                    default_node=default,
                )
            )

        if arguments.kwarg is not None:
            schemas.append(
                self.build_argument_schema(
                    argument=arguments.kwarg,
                    kind=ArgumentKind.VAR_KEYWORD,
                    default_node=None,
                )
            )

        return tuple(schemas)

    def build_argument_schema(
        self,
        *,
        argument: ast.arg,
        kind: ArgumentKind,
        default_node: ast.expr | None,
    ) -> ArgumentSchema:
        return ArgumentSchema(
            name=argument.arg,
            kind=kind,
            annotation=self.render_node(argument.annotation),
            default_value=self.render_node(default_node),
            required=default_node is None and kind not in {
                ArgumentKind.VAR_POSITIONAL,
                ArgumentKind.VAR_KEYWORD,
            },
        )


class ImportsVisitor(BaseVisitor):
    """Collects import statements discovered in a module AST."""

    def __init__(
        self,
        *,
        file_path: Path,
        module_name: str,
        include_private: bool = False,
    ) -> None:
        super().__init__(
            file_path=file_path,
            module_name=module_name,
            include_private=include_private,
        )
        self._imports: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        self._imports.extend(self._render_import_aliases(node.names))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name = f"{'.' * node.level}{node.module or ''}" or "."
        for alias in node.names:
            rendered_alias = self._render_alias(alias)
            self._imports.append(f"from {module_name} import {rendered_alias}")

    def as_list(self) -> list[str]:
        return list(dict.fromkeys(self._imports))

    @staticmethod
    def _render_import_aliases(aliases: Iterable[ast.alias]) -> list[str]:
        return [ImportsVisitor._render_alias(alias) for alias in aliases]

    @staticmethod
    def _render_alias(alias: ast.alias) -> str:
        if alias.asname is None:
            return alias.name
        return f"{alias.name} as {alias.asname}"


class DefinitionsVisitor(BaseVisitor):
    """Collects top-level functions and class methods from a module AST."""

    def __init__(
        self,
        *,
        file_path: Path,
        module_name: str,
        include_private: bool = False,
    ) -> None:
        super().__init__(
            file_path=file_path,
            module_name=module_name,
            include_private=include_private,
        )
        self._functions: list[FunctionSchema] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition(node)

    def as_tuple(self) -> tuple[FunctionSchema, ...]:
        return tuple(self._functions)

    def _visit_definition(self, node: FunctionNode) -> None:
        should_collect = self._function_depth == 0 and self.is_public_definition(node.name)
        if should_collect:
            self._functions.append(self._build_function_schema(node))

        self._function_depth += 1
        try:
            self.generic_visit(node)
        finally:
            self._function_depth -= 1

    def _build_function_schema(self, node: FunctionNode) -> FunctionSchema:
        class_name = self.current_class_name()
        return FunctionSchema(
            name=node.name,
            qualname=self.build_qualname(node.name),
            module=self.module_name,
            file_path=self.file_path,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            arguments=self.build_arguments(node.args),
            return_annotation=self.render_node(node.returns),
            decorators=tuple(ast.unparse(decorator) for decorator in node.decorator_list),
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=class_name is not None,
            class_name=class_name,
            node_hash=self.build_node_hash(node),
        )


class CallsVisitor(BaseVisitor):
    """Collects function and method calls inside top-level function bodies."""

    def __init__(
        self,
        *,
        file_path: Path,
        module_name: str,
        include_private: bool = False,
    ) -> None:
        super().__init__(
            file_path=file_path,
            module_name=module_name,
            include_private=include_private,
        )
        self._active_function_keys: list[FunctionKey] = []
        self._calls_by_function: dict[FunctionKey, list[str]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._active_function_keys and self._function_depth == 1:
            current_function = self._active_function_keys[-1]
            self._calls_by_function.setdefault(current_function, []).append(ast.unparse(node.func))
        self.generic_visit(node)

    def as_mapping(self) -> dict[FunctionKey, list[str]]:
        return {
            function_key: list(dict.fromkeys(calls))
            for function_key, calls in self._calls_by_function.items()
        }

    def _visit_definition(self, node: FunctionNode) -> None:
        should_collect = self._function_depth == 0 and self.is_public_definition(node.name)
        function_key = self.build_function_key(node) if should_collect else None

        if function_key is not None:
            self._active_function_keys.append(function_key)
            self._calls_by_function.setdefault(function_key, [])

        self._function_depth += 1
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self._function_depth -= 1
            if function_key is not None:
                self._active_function_keys.pop()
