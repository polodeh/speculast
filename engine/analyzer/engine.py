"""Coordinator for AST-based project analysis."""

from __future__ import annotations

import ast
import sys
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from .visitors import CallsVisitor, DefinitionsVisitor, FunctionKey, ImportsVisitor
from ..core.models import (
    AnalysisResult,
    FunctionContextSchema,
    FunctionSchema,
    ProjectMetadata,
)
from ..core.protocols import IAnalyzer
from ..parser import derive_module_name, read_python_source


@dataclass(frozen=True, slots=True)
class ModuleAnalysis:
    """Semantic analysis result for a single Python module."""

    imports: list[str]
    functions: tuple[FunctionSchema, ...]


class AnalyzerEngine(IAnalyzer):
    """Default analyzer that orchestrates visitor-based AST traversal."""

    MODULE_LABELS_RU = {
        "models": "Модели данных",
        "logic": "Бизнес-логика",
        "service": "Сервис оформления",
        "database": "Слой данных",
        "generator": "Генерация артефактов",
        "infra": "Инфраструктурный контур",
        "visualizer": "Визуальный контур",
        "core": "Ядро движка",
        "analyzer": "Семантический анализатор",
    }
    SPECIAL_CONTEXT_RU = {
        "demo_shop.database.resolve_database_url": (
            "Разрешение адреса PostgreSQL",
            "Собирает и возвращает итоговый адрес подключения к PostgreSQL для сервисного контура магазина.",
        ),
        "demo_shop.database.create_engine": (
            "Создание асинхронного SQLAlchemy engine",
            "Поднимает асинхронный SQLAlchemy engine для работы сервисов магазина с PostgreSQL.",
        ),
        "demo_shop.database.create_session_factory": (
            "Создание фабрики асинхронных сессий",
            "Формирует session factory, через которую сервисный слой получает асинхронные транзакционные сессии.",
        ),
        "demo_shop.logic.calculate_line_total": (
            "Расчёт суммы позиции заказа",
            "Проверяет корректность количества товара и рассчитывает денежную сумму конкретной позиции заказа.",
        ),
        "demo_shop.logic.calculate_discount": (
            "Применение скидки по промокоду",
            "Определяет величину скидки для заказа, нормализует денежный результат и учитывает промокод клиента.",
        ),
        "demo_shop.logic.calculate_order_total": (
            "Расчёт итоговой суммы заказа",
            "Складывает суммы позиций, проверяет итог и формирует финальную стоимость заказа после всех вычислений.",
        ),
        "demo_shop.logic.validate_stock": (
            "Проверка складских остатков",
            "Сравнивает запрошенное количество с доступным остатком и останавливает оформление заказа при дефиците товара.",
        ),
        "demo_shop.models.normalize_money": (
            "Нормализация денежного значения",
            "Приводит денежные значения к единому формату округления, чтобы расчёты заказа были детерминированными.",
        ),
        "demo_shop.models.Product.validate_unit_price": (
            "Валидация цены товара",
            "Проверяет и нормализует цену товара при создании доменной модели продукта.",
        ),
        "demo_shop.models.OrderCreateRequest.validate_email": (
            "Проверка email покупателя",
            "Проводит базовую проверку и нормализацию email, который приходит в запросе на создание заказа.",
        ),
        "demo_shop.models.OrderLineResult.validate_money": (
            "Проверка суммы строки результата",
            "Нормализует денежную сумму отдельной строки заказа перед возвратом результата пользователю.",
        ),
        "demo_shop.models.OrderResult.validate_money": (
            "Проверка итоговой суммы результата",
            "Приводит итоговую стоимость заказа к единому денежному формату перед публикацией результата.",
        ),
        "demo_shop.service.create_order": (
            "Оформление заказа",
            "Читает товары из базы, проверяет остатки, рассчитывает суммы и сохраняет итоговый заказ в PostgreSQL.",
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

        module_root = self.project_root or resolved_root
        module_analysis = self._analyze_module(
            file_path=resolved_path,
            module_root=module_root,
        )
        project = ProjectMetadata(
            project_name=module_root.name,
            root_path=resolved_root,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            imports=module_analysis.imports,
            source_roots=(module_root,),
            analyzed_files=(resolved_path,),
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

        module_root = self.project_root or resolved_path.parent
        return self._analyze_module(
            file_path=resolved_path,
            module_root=module_root,
        ).functions

    def analyze_project(self, root_path: Path, /) -> AnalysisResult:
        resolved_root = root_path.resolve()
        if not resolved_root.is_dir():
            raise NotADirectoryError(f"Project root not found: {resolved_root}")

        module_root = self.project_root or resolved_root
        analyzed_files = tuple(self._iter_python_files(resolved_root))
        discovered_functions: list[FunctionSchema] = []
        discovered_imports: list[str] = []

        for file_path in analyzed_files:
            module_analysis = self._analyze_module(
                file_path=file_path,
                module_root=module_root,
            )
            discovered_imports.extend(module_analysis.imports)
            discovered_functions.extend(module_analysis.functions)

        project = ProjectMetadata(
            project_name=module_root.name,
            root_path=resolved_root,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            imports=self._deduplicate(discovered_imports),
            source_roots=(module_root,),
            analyzed_files=analyzed_files,
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
        source = read_python_source(file_path)
        tree = ast.parse(source, filename=str(file_path))

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
        label = cls._function_label(function)
        if label in cls.SPECIAL_CONTEXT_RU:
            return cls.SPECIAL_CONTEXT_RU[label][0]

        return cls._verb_phrase_ru(function.name)

    @classmethod
    def _localized_function_description(cls, function: FunctionSchema) -> str:
        label = cls._function_label(function)
        if label in cls.SPECIAL_CONTEXT_RU:
            return cls.SPECIAL_CONTEXT_RU[label][1]

        module_label = cls._module_label_ru(function.module) or function.module
        action = cls._verb_phrase_ru(function.name).lower()
        method_part = (
            f" как метод класса {function.class_name}"
            if function.class_name is not None
            else ""
        )
        return (
            f"Функция {function.qualname} внутри модуля {module_label}"
            f"{method_part} выполняет операцию: {action}."
        )

    @classmethod
    def _module_label_ru(cls, module_name: str) -> str | None:
        tail = module_name.split(".")[-1]
        return cls.MODULE_LABELS_RU.get(tail)

    @staticmethod
    def _function_label(function: FunctionSchema) -> str:
        return f"{function.module}.{function.qualname}"

    @staticmethod
    def _verb_phrase_ru(identifier: str) -> str:
        tokens = [part for part in identifier.replace("__", "_").split("_") if part]
        if not tokens:
            return "Выполняет служебную операцию"

        dictionary = {
            "analyze": "Анализирует",
            "apply": "Применяет",
            "attach": "Присоединяет",
            "build": "Строит",
            "calculate": "Рассчитывает",
            "collect": "Собирает",
            "configure": "Настраивает",
            "create": "Создаёт",
            "derive": "Определяет",
            "detect": "Обнаруживает",
            "enrich": "Обогащает",
            "extract": "Извлекает",
            "generate": "Генерирует",
            "inspect": "Проверяет",
            "load": "Загружает",
            "normalize": "Нормализует",
            "parse": "Разбирает",
            "render": "Отрисовывает",
            "resolve": "Разрешает",
            "run": "Запускает",
            "sanitize": "Очищает",
            "serialize": "Сериализует",
            "summarize": "Суммирует",
            "update": "Обновляет",
            "validate": "Проверяет",
            "visit": "Обходит",
            "wait": "Ожидает",
            "write": "Записывает",
        }
        subject_dictionary = {
            "analysis": "контур анализа",
            "artifact": "артефакт",
            "async": "асинхронный сценарий",
            "call": "вызовы",
            "compose": "compose-конфигурацию",
            "config": "конфигурацию",
            "context": "контекст",
            "coverage": "покрытие",
            "dashboard": "дашборд",
            "database": "подключение к базе данных",
            "dependency": "зависимости",
            "discount": "скидку",
            "engine": "движок",
            "file": "файл",
            "graph": "граф",
            "heatmap": "карту нагрева",
            "import": "импорты",
            "infra": "инфраструктуру",
            "log": "журнал",
            "metadata": "метаданные",
            "mock": "моки",
            "module": "модуль",
            "money": "денежное значение",
            "node": "узел",
            "order": "заказ",
            "path": "путь",
            "price": "цену",
            "project": "проект",
            "readiness": "готовность",
            "report": "отчёт",
            "result": "результат",
            "service": "сервисный сценарий",
            "session": "сессию",
            "stock": "остатки",
            "suite": "набор тестов",
            "test": "тест",
            "total": "итоговую сумму",
            "url": "адрес подключения",
            "visitor": "AST-обход",
        }

        verb = dictionary.get(tokens[0], "Выполняет")
        subject_words = [subject_dictionary.get(token, token.replace(".", " ")) for token in tokens[1:]]
        subject = " ".join(subject_words).strip()
        if not subject:
            return f"{verb} операцию"
        return f"{verb} {subject}"
