"""Coordinator for AST-based project analysis."""

from __future__ import annotations

import ast
import sys
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from .visitors import CallsVisitor, DefinitionsVisitor, FunctionKey, ImportsVisitor
from ..core.i18n import repair_text
from ..core.models import (
    AnalysisResult,
    AnalysisWarningSchema,
    FunctionContextSchema,
    FunctionSchema,
    ProjectMetadata,
)
from ..core.protocols import IAnalyzer
from ..parser import collect_source_roots, derive_module_name, detect_source_root, read_python_source


@dataclass(frozen=True, slots=True)
class ModuleAnalysis:
    """Semantic analysis result for a single Python module."""

    imports: list[str]
    functions: tuple[FunctionSchema, ...]
    warnings: tuple[AnalysisWarningSchema, ...] = ()


class AnalyzerEngine(IAnalyzer):
    """Default analyzer that orchestrates visitor-based AST traversal."""

    MODULE_LABELS_RU = {
        "models": "РњРѕРґРµР»Рё РґР°РЅРЅС‹С…",
        "logic": "Р‘РёР·РЅРµСЃ-Р»РѕРіРёРєР°",
        "service": "РЎРµСЂРІРёСЃ РѕС„РѕСЂРјР»РµРЅРёСЏ",
        "database": "РЎР»РѕР№ РґР°РЅРЅС‹С…",
        "generator": "Р“РµРЅРµСЂР°С†РёСЏ Р°СЂС‚РµС„Р°РєС‚РѕРІ",
        "infra": "РРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂРЅС‹Р№ РєРѕРЅС‚СѓСЂ",
        "visualizer": "Р’РёР·СѓР°Р»СЊРЅС‹Р№ РєРѕРЅС‚СѓСЂ",
        "core": "РЇРґСЂРѕ РґРІРёР¶РєР°",
        "analyzer": "РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ Р°РЅР°Р»РёР·Р°С‚РѕСЂ",
    }
    SPECIAL_CONTEXT_RU = {
        "database.resolve_database_url": (
            "Р Р°Р·СЂРµС€РµРЅРёРµ Р°РґСЂРµСЃР° PostgreSQL",
            "РЎРѕР±РёСЂР°РµС‚ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ РёС‚РѕРіРѕРІС‹Р№ Р°РґСЂРµСЃ РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє PostgreSQL РґР»СЏ СЃРµСЂРІРёСЃРЅРѕРіРѕ РєРѕРЅС‚СѓСЂР° РјР°РіР°Р·РёРЅР°.",
        ),
        "database.create_engine": (
            "РЎРѕР·РґР°РЅРёРµ Р°СЃРёРЅС…СЂРѕРЅРЅРѕРіРѕ SQLAlchemy engine",
            "РџРѕРґРЅРёРјР°РµС‚ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Р№ SQLAlchemy engine РґР»СЏ СЂР°Р±РѕС‚С‹ СЃРµСЂРІРёСЃРѕРІ РјР°РіР°Р·РёРЅР° СЃ PostgreSQL.",
        ),
        "database.create_session_factory": (
            "РЎРѕР·РґР°РЅРёРµ С„Р°Р±СЂРёРєРё Р°СЃРёРЅС…СЂРѕРЅРЅС‹С… СЃРµСЃСЃРёР№",
            "Р¤РѕСЂРјРёСЂСѓРµС‚ session factory, С‡РµСЂРµР· РєРѕС‚РѕСЂСѓСЋ СЃРµСЂРІРёСЃРЅС‹Р№ СЃР»РѕР№ РїРѕР»СѓС‡Р°РµС‚ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Рµ С‚СЂР°РЅР·Р°РєС†РёРѕРЅРЅС‹Рµ СЃРµСЃСЃРёРё.",
        ),
        "logic.calculate_line_total": (
            "Р Р°СЃС‡С‘С‚ СЃСѓРјРјС‹ РїРѕР·РёС†РёРё Р·Р°РєР°Р·Р°",
            "РџСЂРѕРІРµСЂСЏРµС‚ РєРѕСЂСЂРµРєС‚РЅРѕСЃС‚СЊ РєРѕР»РёС‡РµСЃС‚РІР° С‚РѕРІР°СЂР° Рё СЂР°СЃСЃС‡РёС‚С‹РІР°РµС‚ РґРµРЅРµР¶РЅСѓСЋ СЃСѓРјРјСѓ РєРѕРЅРєСЂРµС‚РЅРѕР№ РїРѕР·РёС†РёРё Р·Р°РєР°Р·Р°.",
        ),
        "logic.calculate_discount": (
            "РџСЂРёРјРµРЅРµРЅРёРµ СЃРєРёРґРєРё РїРѕ РїСЂРѕРјРѕРєРѕРґСѓ",
            "РћРїСЂРµРґРµР»СЏРµС‚ РІРµР»РёС‡РёРЅСѓ СЃРєРёРґРєРё РґР»СЏ Р·Р°РєР°Р·Р°, РЅРѕСЂРјР°Р»РёР·СѓРµС‚ РґРµРЅРµР¶РЅС‹Р№ СЂРµР·СѓР»СЊС‚Р°С‚ Рё СѓС‡РёС‚С‹РІР°РµС‚ РїСЂРѕРјРѕРєРѕРґ РєР»РёРµРЅС‚Р°.",
        ),
        "logic.calculate_order_total": (
            "Р Р°СЃС‡С‘С‚ РёС‚РѕРіРѕРІРѕР№ СЃСѓРјРјС‹ Р·Р°РєР°Р·Р°",
            "РЎРєР»Р°РґС‹РІР°РµС‚ СЃСѓРјРјС‹ РїРѕР·РёС†РёР№, РїСЂРѕРІРµСЂСЏРµС‚ РёС‚РѕРі Рё С„РѕСЂРјРёСЂСѓРµС‚ С„РёРЅР°Р»СЊРЅСѓСЋ СЃС‚РѕРёРјРѕСЃС‚СЊ Р·Р°РєР°Р·Р° РїРѕСЃР»Рµ РІСЃРµС… РІС‹С‡РёСЃР»РµРЅРёР№.",
        ),
        "logic.validate_stock": (
            "РџСЂРѕРІРµСЂРєР° СЃРєР»Р°РґСЃРєРёС… РѕСЃС‚Р°С‚РєРѕРІ",
            "РЎСЂР°РІРЅРёРІР°РµС‚ Р·Р°РїСЂРѕС€РµРЅРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СЃ РґРѕСЃС‚СѓРїРЅС‹Рј РѕСЃС‚Р°С‚РєРѕРј Рё РѕСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ РѕС„РѕСЂРјР»РµРЅРёРµ Р·Р°РєР°Р·Р° РїСЂРё РґРµС„РёС†РёС‚Рµ С‚РѕРІР°СЂР°.",
        ),
        "models.normalize_money": (
            "РќРѕСЂРјР°Р»РёР·Р°С†РёСЏ РґРµРЅРµР¶РЅРѕРіРѕ Р·РЅР°С‡РµРЅРёСЏ",
            "РџСЂРёРІРѕРґРёС‚ РґРµРЅРµР¶РЅС‹Рµ Р·РЅР°С‡РµРЅРёСЏ Рє РµРґРёРЅРѕРјСѓ С„РѕСЂРјР°С‚Сѓ РѕРєСЂСѓРіР»РµРЅРёСЏ, С‡С‚РѕР±С‹ СЂР°СЃС‡С‘С‚С‹ Р·Р°РєР°Р·Р° Р±С‹Р»Рё РґРµС‚РµСЂРјРёРЅРёСЂРѕРІР°РЅРЅС‹РјРё.",
        ),
        "models.Product.validate_unit_price": (
            "Р’Р°Р»РёРґР°С†РёСЏ С†РµРЅС‹ С‚РѕРІР°СЂР°",
            "РџСЂРѕРІРµСЂСЏРµС‚ Рё РЅРѕСЂРјР°Р»РёР·СѓРµС‚ С†РµРЅСѓ С‚РѕРІР°СЂР° РїСЂРё СЃРѕР·РґР°РЅРёРё РґРѕРјРµРЅРЅРѕР№ РјРѕРґРµР»Рё РїСЂРѕРґСѓРєС‚Р°.",
        ),
        "models.OrderCreateRequest.validate_email": (
            "РџСЂРѕРІРµСЂРєР° email РїРѕРєСѓРїР°С‚РµР»СЏ",
            "РџСЂРѕРІРѕРґРёС‚ Р±Р°Р·РѕРІСѓСЋ РїСЂРѕРІРµСЂРєСѓ Рё РЅРѕСЂРјР°Р»РёР·Р°С†РёСЋ email, РєРѕС‚РѕСЂС‹Р№ РїСЂРёС…РѕРґРёС‚ РІ Р·Р°РїСЂРѕСЃРµ РЅР° СЃРѕР·РґР°РЅРёРµ Р·Р°РєР°Р·Р°.",
        ),
        "models.OrderLineResult.validate_money": (
            "РџСЂРѕРІРµСЂРєР° СЃСѓРјРјС‹ СЃС‚СЂРѕРєРё СЂРµР·СѓР»СЊС‚Р°С‚Р°",
            "РќРѕСЂРјР°Р»РёР·СѓРµС‚ РґРµРЅРµР¶РЅСѓСЋ СЃСѓРјРјСѓ РѕС‚РґРµР»СЊРЅРѕР№ СЃС‚СЂРѕРєРё Р·Р°РєР°Р·Р° РїРµСЂРµРґ РІРѕР·РІСЂР°С‚РѕРј СЂРµР·СѓР»СЊС‚Р°С‚Р° РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.",
        ),
        "models.OrderResult.validate_money": (
            "РџСЂРѕРІРµСЂРєР° РёС‚РѕРіРѕРІРѕР№ СЃСѓРјРјС‹ СЂРµР·СѓР»СЊС‚Р°С‚Р°",
            "РџСЂРёРІРѕРґРёС‚ РёС‚РѕРіРѕРІСѓСЋ СЃС‚РѕРёРјРѕСЃС‚СЊ Р·Р°РєР°Р·Р° Рє РµРґРёРЅРѕРјСѓ РґРµРЅРµР¶РЅРѕРјСѓ С„РѕСЂРјР°С‚Сѓ РїРµСЂРµРґ РїСѓР±Р»РёРєР°С†РёРµР№ СЂРµР·СѓР»СЊС‚Р°С‚Р°.",
        ),
        "service.create_order": (
            "РћС„РѕСЂРјР»РµРЅРёРµ Р·Р°РєР°Р·Р°",
            "Р§РёС‚Р°РµС‚ С‚РѕРІР°СЂС‹ РёР· Р±Р°Р·С‹, РїСЂРѕРІРµСЂСЏРµС‚ РѕСЃС‚Р°С‚РєРё, СЂР°СЃСЃС‡РёС‚С‹РІР°РµС‚ СЃСѓРјРјС‹ Рё СЃРѕС…СЂР°РЅСЏРµС‚ РёС‚РѕРіРѕРІС‹Р№ Р·Р°РєР°Р· РІ PostgreSQL.",
        ),
    }

    DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
        {
            ".git",
            ".hg",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".tox",
            ".venv",
            "__pycache__",
            "build",
            "dist",
            "tests",
        }
    )

    def __init__(
        self,
        *,
        include_private: bool = False,
        project_root: Path | None = None,
        excluded_directories: Collection[str] | None = None,
    ) -> None:
        self.include_private = include_private
        self.project_root = project_root.resolve() if project_root is not None else None
        self.excluded_directories = frozenset(
            excluded_directories or self.DEFAULT_EXCLUDED_DIRECTORIES
        )

    def analyze(self, project_root: Path, file_path: Path, /) -> AnalysisResult:
        """Analyze a single file and wrap the result in project metadata."""

        resolved_root = project_root.resolve()
        if not resolved_root.is_dir():
            raise NotADirectoryError(f"Project root not found: {resolved_root}")

        resolved_path = file_path.resolve()
        if not resolved_path.is_file():
            raise FileNotFoundError(f"Python file not found: {resolved_path}")

        project_root = self.project_root or resolved_root
        module_root = detect_source_root(resolved_path, project_root)
        module_analysis = self._analyze_module(
            file_path=resolved_path,
            module_root=module_root,
        )
        project = ProjectMetadata(
            project_name=resolved_root.name,
            root_path=resolved_root,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            imports=module_analysis.imports,
            source_roots=(module_root,),
            analyzed_files=(resolved_path,),
            analysis_warnings=module_analysis.warnings,
        )
        return AnalysisResult(
            project=project,
            functions=module_analysis.functions,
            function_context=self._build_function_context(module_analysis.functions),
        )

    def analyze_file(self, file_path: Path, /) -> tuple[FunctionSchema, ...]:
        resolved_path = file_path.resolve()
        if not resolved_path.is_file():
            raise FileNotFoundError(f"Python file not found: {resolved_path}")

        project_root = self.project_root or resolved_path.parent
        module_root = detect_source_root(resolved_path, project_root)
        return self._analyze_module(
            file_path=resolved_path,
            module_root=module_root,
        ).functions

    def analyze_project(self, root_path: Path, /) -> AnalysisResult:
        resolved_root = root_path.resolve()
        if not resolved_root.is_dir():
            raise NotADirectoryError(f"Project root not found: {resolved_root}")

        project_root = self.project_root or resolved_root
        analyzed_files = tuple(self._iter_python_files(resolved_root))
        source_roots = collect_source_roots(analyzed_files, project_root) or (project_root,)
        discovered_functions: list[FunctionSchema] = []
        discovered_imports: list[str] = []
        analysis_warnings: list[AnalysisWarningSchema] = []

        for file_path in analyzed_files:
            module_root = detect_source_root(file_path, project_root)
            module_analysis = self._analyze_module(
                file_path=file_path,
                module_root=module_root,
            )
            discovered_imports.extend(module_analysis.imports)
            discovered_functions.extend(module_analysis.functions)
            analysis_warnings.extend(module_analysis.warnings)

        project = ProjectMetadata(
            project_name=resolved_root.name,
            root_path=resolved_root,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            imports=self._deduplicate(discovered_imports),
            source_roots=source_roots,
            analyzed_files=analyzed_files,
            analysis_warnings=tuple(analysis_warnings),
        )
        functions_tuple = tuple(discovered_functions)
        return AnalysisResult(
            project=project,
            functions=functions_tuple,
            function_context=self._build_function_context(functions_tuple),
        )

    def _analyze_module(
        self,
        *,
        file_path: Path,
        module_root: Path,
    ) -> ModuleAnalysis:
        try:
            source = read_python_source(file_path)
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as error:
            return ModuleAnalysis(
                imports=[],
                functions=(),
                warnings=(
                    AnalysisWarningSchema(
                        file_path=file_path,
                        kind="syntax_error",
                        details=error.msg,
                        line_number=error.lineno or None,
                    ),
                ),
            )
        except OSError as error:
            return ModuleAnalysis(
                imports=[],
                functions=(),
                warnings=(
                    AnalysisWarningSchema(
                        file_path=file_path,
                        kind="read_error",
                        details=str(error),
                    ),
                ),
            )

        imports_visitor = ImportsVisitor(
            file_path=file_path,
            module_name=derive_module_name(file_path, module_root),
            include_private=self.include_private,
        )
        imports_visitor.visit(tree)

        definitions_visitor = DefinitionsVisitor(
            file_path=file_path,
            module_name=derive_module_name(file_path, module_root),
            include_private=self.include_private,
        )
        definitions_visitor.visit(tree)

        calls_visitor = CallsVisitor(
            file_path=file_path,
            module_name=derive_module_name(file_path, module_root),
            include_private=self.include_private,
        )
        calls_visitor.visit(tree)

        functions = self._attach_external_calls(
            functions=definitions_visitor.as_tuple(),
            calls_by_function=calls_visitor.as_mapping(),
        )
        return ModuleAnalysis(
            imports=imports_visitor.as_list(),
            functions=functions,
            warnings=(),
        )

    def _iter_python_files(self, root_path: Path) -> list[Path]:
        candidates: list[Path] = []
        for candidate in root_path.rglob("*.py"):
            if self._should_skip(candidate, root_path):
                continue
            candidates.append(candidate.resolve())
        return sorted(candidates)

    def _should_skip(self, candidate: Path, root_path: Path) -> bool:
        relative_parts = candidate.resolve().relative_to(root_path.resolve()).parts
        return any(part in self.excluded_directories for part in relative_parts)

    @staticmethod
    def _attach_external_calls(
        *,
        functions: tuple[FunctionSchema, ...],
        calls_by_function: dict[FunctionKey, list[str]],
    ) -> tuple[FunctionSchema, ...]:
        enriched_functions: list[FunctionSchema] = []
        for function in functions:
            function_key: FunctionKey = (function.qualname, function.lineno)
            external_calls = calls_by_function.get(function_key, [])
            enriched_functions.append(
                function.model_copy(update={"external_calls": list(external_calls)})
            )
        return tuple(enriched_functions)

    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    def _build_function_context(
        self,
        functions: tuple[FunctionSchema, ...],
    ) -> dict[str, FunctionContextSchema]:
        return {
            self._function_label(function): FunctionContextSchema(
                localized_name=self._localized_function_name(function),
                description_ru=self._localized_function_description(function),
                module_label_ru=self._module_label_ru(function.module),
            )
            for function in functions
        }

    @classmethod
    def _localized_function_name(cls, function: FunctionSchema) -> str:
        context_label = cls._context_label(function)
        if context_label in cls.SPECIAL_CONTEXT_RU:
            return repair_text(cls.SPECIAL_CONTEXT_RU[context_label][0])

        return repair_text(cls._verb_phrase_ru(function.name))

    @classmethod
    def _localized_function_description(cls, function: FunctionSchema) -> str:
        context_label = cls._context_label(function)
        if context_label in cls.SPECIAL_CONTEXT_RU:
            return repair_text(cls.SPECIAL_CONTEXT_RU[context_label][1])

        module_label = cls._module_label_ru(function.module) or function.module
        action = cls._verb_phrase_ru(function.name).lower()
        method_part = (
            f" РєР°Рє РјРµС‚РѕРґ РєР»Р°СЃСЃР° {function.class_name}"
            if function.class_name is not None
            else ""
        )
        return repair_text(
            f"Р¤СѓРЅРєС†РёСЏ {function.qualname} РІРЅСѓС‚СЂРё РјРѕРґСѓР»СЏ {module_label}"
            f"{method_part} РІС‹РїРѕР»РЅСЏРµС‚ РѕРїРµСЂР°С†РёСЋ: {action}."
        )

    @classmethod
    def _module_label_ru(cls, module_name: str) -> str | None:
        tail = module_name.split(".")[-1]
        label = cls.MODULE_LABELS_RU.get(tail)
        return repair_text(label) if label is not None else None

    @staticmethod
    def _function_label(function: FunctionSchema) -> str:
        return f"{function.module}.{function.qualname}"

    @staticmethod
    def _context_label(function: FunctionSchema) -> str:
        return f"{function.module.split('.')[-1]}.{function.qualname}"

    @staticmethod
    def _verb_phrase_ru(identifier: str) -> str:
        tokens = [part for part in identifier.replace("__", "_").split("_") if part]
        if not tokens:
            return repair_text("Р’С‹РїРѕР»РЅСЏРµС‚ СЃР»СѓР¶РµР±РЅСѓСЋ РѕРїРµСЂР°С†РёСЋ")

        dictionary = {
            "analyze": "РђРЅР°Р»РёР·РёСЂСѓРµС‚",
            "apply": "РџСЂРёРјРµРЅСЏРµС‚",
            "attach": "РџСЂРёСЃРѕРµРґРёРЅСЏРµС‚",
            "build": "РЎС‚СЂРѕРёС‚",
            "calculate": "Р Р°СЃСЃС‡РёС‚С‹РІР°РµС‚",
            "collect": "РЎРѕР±РёСЂР°РµС‚",
            "configure": "РќР°СЃС‚СЂР°РёРІР°РµС‚",
            "create": "РЎРѕР·РґР°С‘С‚",
            "derive": "РћРїСЂРµРґРµР»СЏРµС‚",
            "detect": "РћР±РЅР°СЂСѓР¶РёРІР°РµС‚",
            "enrich": "РћР±РѕРіР°С‰Р°РµС‚",
            "extract": "РР·РІР»РµРєР°РµС‚",
            "generate": "Р“РµРЅРµСЂРёСЂСѓРµС‚",
            "inspect": "РџСЂРѕРІРµСЂСЏРµС‚",
            "load": "Р—Р°РіСЂСѓР¶Р°РµС‚",
            "normalize": "РќРѕСЂРјР°Р»РёР·СѓРµС‚",
            "parse": "Р Р°Р·Р±РёСЂР°РµС‚",
            "render": "РћС‚СЂРёСЃРѕРІС‹РІР°РµС‚",
            "resolve": "Р Р°Р·СЂРµС€Р°РµС‚",
            "run": "Р—Р°РїСѓСЃРєР°РµС‚",
            "sanitize": "РћС‡РёС‰Р°РµС‚",
            "serialize": "РЎРµСЂРёР°Р»РёР·СѓРµС‚",
            "summarize": "РЎСѓРјРјРёСЂСѓРµС‚",
            "update": "РћР±РЅРѕРІР»СЏРµС‚",
            "validate": "РџСЂРѕРІРµСЂСЏРµС‚",
            "visit": "РћР±С…РѕРґРёС‚",
            "wait": "РћР¶РёРґР°РµС‚",
            "write": "Р—Р°РїРёСЃС‹РІР°РµС‚",
        }
        subject_dictionary = {
            "analysis": "РєРѕРЅС‚СѓСЂ Р°РЅР°Р»РёР·Р°",
            "artifact": "Р°СЂС‚РµС„Р°РєС‚",
            "async": "Р°СЃРёРЅС…СЂРѕРЅРЅС‹Р№ СЃС†РµРЅР°СЂРёР№",
            "call": "РІС‹Р·РѕРІС‹",
            "compose": "compose-РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ",
            "config": "РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ",
            "context": "РєРѕРЅС‚РµРєСЃС‚",
            "coverage": "РїРѕРєСЂС‹С‚РёРµ",
            "dashboard": "РґР°С€Р±РѕСЂРґ",
            "database": "РїРѕРґРєР»СЋС‡РµРЅРёРµ Рє Р±Р°Р·Рµ РґР°РЅРЅС‹С…",
            "dependency": "Р·Р°РІРёСЃРёРјРѕСЃС‚Рё",
            "discount": "СЃРєРёРґРєСѓ",
            "engine": "РґРІРёР¶РѕРє",
            "file": "С„Р°Р№Р»",
            "graph": "РіСЂР°С„",
            "heatmap": "РєР°СЂС‚Сѓ РЅР°РіСЂРµРІР°",
            "import": "РёРјРїРѕСЂС‚С‹",
            "infra": "РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂСѓ",
            "log": "Р¶СѓСЂРЅР°Р»",
            "metadata": "РјРµС‚Р°РґР°РЅРЅС‹Рµ",
            "mock": "РјРѕРєРё",
            "module": "РјРѕРґСѓР»СЊ",
            "money": "РґРµРЅРµР¶РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ",
            "node": "СѓР·РµР»",
            "order": "Р·Р°РєР°Р·",
            "path": "РїСѓС‚СЊ",
            "price": "С†РµРЅСѓ",
            "project": "РїСЂРѕРµРєС‚",
            "readiness": "РіРѕС‚РѕРІРЅРѕСЃС‚СЊ",
            "report": "РѕС‚С‡С‘С‚",
            "result": "СЂРµР·СѓР»СЊС‚Р°С‚",
            "service": "СЃРµСЂРІРёСЃРЅС‹Р№ СЃС†РµРЅР°СЂРёР№",
            "session": "СЃРµСЃСЃРёСЋ",
            "stock": "РѕСЃС‚Р°С‚РєРё",
            "suite": "РЅР°Р±РѕСЂ С‚РµСЃС‚РѕРІ",
            "test": "С‚РµСЃС‚",
            "total": "РёС‚РѕРіРѕРІСѓСЋ СЃСѓРјРјСѓ",
            "url": "Р°РґСЂРµСЃ РїРѕРґРєР»СЋС‡РµРЅРёСЏ",
            "visitor": "AST-РѕР±С…РѕРґ",
        }

        verb = dictionary.get(tokens[0], "Р’С‹РїРѕР»РЅСЏРµС‚")
        subject_words = [subject_dictionary.get(token, token.replace(".", " ")) for token in tokens[1:]]
        subject = " ".join(subject_words).strip()
        if not subject:
            return repair_text(f"{verb} РѕРїРµСЂР°С†РёСЋ")
        return repair_text(f"{verb} {subject}")

