"""TestSpec 上下文构建。

将用户输入（交互式或 JSON 配置文件）转换为模板渲染所需的上下文字典。

架构说明：
  - ``ProjectContext`` (TypedDict) 是对外公开的类型，模板引擎和生成器消费
  - ``_ProjectContextModel`` (dataclass) 是内部构建源：字段定义、默认值、
    跨字段一致性校验集中于此，通过 ``to_dict()`` 转换为 plain dict
  - 新增上下文键时需同时更新 TypedDict、dataclass 和对应的 sub-builder
"""

from __future__ import annotations

import dataclasses
import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict, cast

from .constants import (
    TYPE_DESC_MAP,
    DB_PORT_MAP,
    DB_DRIVER_MAP,
    VALID_DATABASES,
    VALID_TEST_TYPES,
    KNOWN_CONFIG_KEYS,
    PROJECT_NAME_PATTERN,
    LANG_FRAMEWORKS,
    REPORT_TOOLS,
    CI_SYSTEMS,
    LANGUAGES,
)
from .exceptions import ConfigError
from .constants import VERSION as _VERSION

__all__ = [
    "build_context_from_config",
    "build_context_from_wizard",
    "ProjectContext",
]

# 从选项字典中提取有效值集合（用于扩展验证）
_VALID_LANGUAGES: frozenset[str] = LANG_FRAMEWORKS.valid_values(0)
_VALID_FRAMEWORKS: frozenset[str] = LANG_FRAMEWORKS.valid_values(1)
_VALID_REPORT_TOOLS: frozenset[str] = REPORT_TOOLS.valid_values(0)
_VALID_CI_SYSTEMS: frozenset[str] = CI_SYSTEMS.valid_values(0)
_VALID_LOCALES: frozenset[str] = LANGUAGES.valid_values(0)

# 业务线名称校验正则（模块级预编译，避免每次调用重新编译）
_BIZ_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

# JSON 配置文件字段类型规则（模块级预建，避免每次调用重新创建）
_CONFIG_FIELD_TYPES: dict[str, type] = {
    "project_name": str,
    "test_types": list,
    "business_lines": list,
    "language": str,
    "framework": str,
    "database": str,
    "report_tool": str,
    "ci_system": str,
    "language_locale": str,
    "output_dir": str,
}


def _validate_config_types(cfg: dict[str, Any]) -> None:
    """校验 JSON 配置字段类型，类型不匹配时抛出 ConfigError。

    只校验 cfg 中存在的键（缺失键由 build_context_from_config 的默认值处理）。
    对 list 类型字段进一步校验元素类型，防止 "test_types": "api" 静默变为字符列表。
    """
    for key, expected_type in _CONFIG_FIELD_TYPES.items():
        if key in cfg and not isinstance(cfg[key], expected_type):
            raise ConfigError(
                f"配置键 '{key}' 类型错误：期望 {expected_type.__name__}，"
                f"实际 {type(cfg[key]).__name__}（值: {cfg[key]!r}）"
            )
    # 列表字段元素类型校验
    for list_key in ("test_types", "business_lines"):
        if list_key in cfg and isinstance(cfg[list_key], list):
            for i, item in enumerate(cfg[list_key]):
                if not isinstance(item, str):
                    raise ConfigError(
                        f"配置键 '{list_key}[{i}]' 类型错误：期望 str，"
                        f"实际 {type(item).__name__}（值: {item!r}）"
                    )


class ProjectContext(TypedDict):
    """项目生成上下文 — 模板引擎消费的扁平字典。

    所有 47 个字段由 _build_ctx() 在每次调用时完整填充，无可选键。
    total=True（默认值）确保静态类型检查工具（mypy/pyright）可捕获
    上下文消费方访问未声明键的错误。
    运行时仍然是普通 dict，对模板引擎完全透明。
    """
    # 项目名称变体
    PROJECT_NAME: str
    PROJECT_NAME_SNAKE: str
    PROJECT_NAME_TITLE: str
    PROJECT_NAME_PASCAL: str
    PROJECT_DISPLAY_NAME: str
    # 测试类型
    TEST_TYPES: list[str]
    IS_API: bool
    IS_UNIT: bool
    IS_INTEG: bool
    IS_E2E: bool
    TEST_TYPE_DESCRIPTION: str
    # 语言与框架
    LANGUAGE: str
    TEST_FRAMEWORK: str
    IS_PYTHON: bool
    IS_JAVASCRIPT: bool
    IS_JAVA: bool
    # 数据库
    HAS_DB: bool
    DB_TYPE: str
    DB_SQLSERVER: bool
    DB_MYSQL: bool
    DB_POSTGRESQL: bool
    DB_SQLITE: bool
    DB_DEFAULT_PORT: str
    DB_DRIVER: str
    # 报告
    REPORT_TOOL: str
    HAS_ALLURE: bool
    HAS_HTML_REPORT: bool
    # CI
    CI_SYSTEM: str
    CI_GITHUB: bool
    CI_GITLAB: bool
    HAS_CI: bool
    # 语言
    LANG_ZH: bool
    LANG_EN: bool
    # 业务线
    BUSINESS_LINES_RAW: list[str]
    BUSINESS_LINES: str
    BUSINESS_LINES_LIST: str
    BUSINESS_LINES_DIRS: str
    # 派生值
    OUTPUT_DIR: str
    RUN_SCRIPT_NAME: str
    SKILL_PREFIX: str
    HAS_HTTP: bool
    HAS_EMAIL: bool
    AUTH_MODULE_PATH: str
    CONFIG_CLASS_NAME: str
    API_CLASS_NAME: str
    TESTSPEC_VERSION: str


def _validate_inputs(
    *, test_types: list[str], database: str, project_name: str = "",
    language: str = "", framework: str = "",
    report_tool: str = "", ci_system: str = "",
    language_locale: str = "",
) -> None:
    """统一输入验证。

    校验所有维度的参数合法性，
    由 build_context_from_config 和 build_context_from_wizard 共享。
    """
    invalid_types = set(test_types) - VALID_TEST_TYPES
    if invalid_types:
        raise ConfigError(
            f"无效的测试类型: {invalid_types}。有效值: {sorted(VALID_TEST_TYPES)}"
        )
    if database not in VALID_DATABASES:
        raise ConfigError(
            f"无效的数据库类型: {database!r}。有效值: {sorted(VALID_DATABASES)}"
        )
    if project_name and not PROJECT_NAME_PATTERN.match(project_name):
        raise ConfigError(
            f"项目名称格式无效: {project_name!r}。"
            f"必须以小写字母开头，只含小写字母、数字和连字符。"
        )
    if language and language not in _VALID_LANGUAGES:
        raise ConfigError(
            f"无效的编程语言: {language!r}。有效值: {sorted(_VALID_LANGUAGES)}"
        )
    if framework and framework not in _VALID_FRAMEWORKS:
        raise ConfigError(
            f"无效的测试框架: {framework!r}。有效值: {sorted(_VALID_FRAMEWORKS)}"
        )
    if report_tool and report_tool not in _VALID_REPORT_TOOLS:
        raise ConfigError(
            f"无效的报告工具: {report_tool!r}。有效值: {sorted(_VALID_REPORT_TOOLS)}"
        )
    if ci_system and ci_system not in _VALID_CI_SYSTEMS:
        raise ConfigError(
            f"无效的 CI 系统: {ci_system!r}。有效值: {sorted(_VALID_CI_SYSTEMS)}"
        )
    if language_locale and language_locale not in _VALID_LOCALES:
        raise ConfigError(
            f"无效的文档语言: {language_locale!r}。有效值: {sorted(_VALID_LOCALES)}"
        )


def build_context_from_config(config_path: str | Path) -> ProjectContext:
    """从 JSON 配置文件构建上下文字典（非交互式模式）。

    JSON 格式示例：
    {
        "project_name": "order-service-tests",
        "test_types": ["api", "e2e"],
        "language": "python",
        "framework": "pytest",
        "database": "sqlserver",
        "report_tool": "allure",
        "business_lines": ["order", "payment"],
        "output_dir": "./order-service-tests",
        "ci_system": "github",
        "language_locale": "zh"
    }
    """
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    with path.open(encoding="utf-8") as f:
        try:
            cfg = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件 JSON 格式错误: {e}") from e

    if not isinstance(cfg, dict):
        raise ConfigError(
            f"配置文件根元素必须是 JSON 对象 ({{}})，"
            f"实际类型: {type(cfg).__name__}"
        )

    # 检测可能的拼写错误
    unknown_keys = set(cfg.keys()) - KNOWN_CONFIG_KEYS
    if unknown_keys:
        warnings.warn(
            f"配置文件包含未知键: {sorted(unknown_keys)}，请检查拼写。",
            stacklevel=3,
        )

    # 类型校验（防止 "test_types": "api" 静默变为字符列表等错误）
    _validate_config_types(cfg)

    if "project_name" not in cfg:
        warnings.warn(
            "配置文件缺少 'project_name' 键，将使用默认值 'my-project'。",
            stacklevel=3,
        )
    project_name = cfg.get("project_name") or "my-project"
    test_types = cfg.get("test_types") or ["api"]
    language = cfg.get("language") or "python"
    framework = cfg.get("framework") or "pytest"
    database = cfg.get("database") or "none"
    report_tool = cfg.get("report_tool") or "allure"
    business_lines = cfg.get("business_lines") or ["default"]
    output_dir = cfg.get("output_dir") or f"./{project_name}"
    ci_system = cfg.get("ci_system") or "none"
    language_locale = cfg.get("language_locale") or "zh"

    # 输入校验（所有维度）
    _validate_inputs(
        test_types=test_types, database=database, project_name=project_name,
        language=language, framework=framework,
        report_tool=report_tool, ci_system=ci_system,
        language_locale=language_locale,
    )

    return _build_ctx(
        project_name=project_name,
        test_types=test_types,
        language=language,
        framework=framework,
        database=database,
        report_tool=report_tool,
        business_lines=business_lines,
        output_dir=output_dir,
        ci_system=ci_system,
        language_locale=language_locale,
    )


def build_context_from_wizard(
    project_name: str,
    test_types: list[str],
    language: str,
    framework: str,
    database: str,
    report_tool: str,
    business_lines: list[str],
    output_dir: str,
    ci_system: str = "none",
    language_locale: str = "zh",
) -> ProjectContext:
    """将向导收集的参数构建为上下文字典。

    Note:
        参数由 :func:`run_wizard` 收集后传入，此函数不执行交互式 I/O。
        与 :func:`build_context_from_config` 执行相同的输入验证。
    """
    _validate_inputs(
        test_types=test_types, database=database, project_name=project_name,
        language=language, framework=framework,
        report_tool=report_tool, ci_system=ci_system,
        language_locale=language_locale,
    )
    return _build_ctx(
        project_name=project_name,
        test_types=test_types,
        language=language,
        framework=framework,
        database=database,
        report_tool=report_tool,
        business_lines=business_lines,
        output_dir=output_dir,
        ci_system=ci_system,
        language_locale=language_locale,
    )


# ---------------------------------------------------------------------------
# 上下文键分组（文档 + 维护辅助）
# ---------------------------------------------------------------------------
_PROJECT_NAME_KEYS: frozenset[str] = frozenset({
    "PROJECT_NAME", "PROJECT_NAME_SNAKE", "PROJECT_NAME_TITLE",
    "PROJECT_NAME_PASCAL", "PROJECT_DISPLAY_NAME",
})
_TEST_TYPE_KEYS: frozenset[str] = frozenset({
    "TEST_TYPES", "IS_API", "IS_UNIT", "IS_INTEG", "IS_E2E",
    "TEST_TYPE_DESCRIPTION",
})
_LANGUAGE_KEYS: frozenset[str] = frozenset({
    "LANGUAGE", "TEST_FRAMEWORK", "IS_PYTHON", "IS_JAVASCRIPT", "IS_JAVA",
})
_DATABASE_KEYS: frozenset[str] = frozenset({
    "HAS_DB", "DB_TYPE", "DB_SQLSERVER", "DB_MYSQL",
    "DB_POSTGRESQL", "DB_SQLITE", "DB_DEFAULT_PORT", "DB_DRIVER",
})
_REPORT_KEYS: frozenset[str] = frozenset({
    "REPORT_TOOL", "HAS_ALLURE", "HAS_HTML_REPORT",
})
_CI_KEYS: frozenset[str] = frozenset({
    "CI_SYSTEM", "CI_GITHUB", "CI_GITLAB", "HAS_CI",
})
_LOCALE_KEYS: frozenset[str] = frozenset({"LANG_ZH", "LANG_EN"})
_BUSINESS_KEYS: frozenset[str] = frozenset({
    "BUSINESS_LINES_RAW", "BUSINESS_LINES", "BUSINESS_LINES_LIST",
    "BUSINESS_LINES_DIRS",
})
_DERIVED_KEYS: frozenset[str] = frozenset({
    "OUTPUT_DIR", "RUN_SCRIPT_NAME", "SKILL_PREFIX", "HAS_HTTP",
    "HAS_EMAIL", "AUTH_MODULE_PATH", "CONFIG_CLASS_NAME",
    "API_CLASS_NAME", "TESTSPEC_VERSION",
})


# ---------------------------------------------------------------------------
# 运行时校验模型
# ---------------------------------------------------------------------------

@dataclass
class _ProjectContextModel:
    """内部构建模型：字段定义、默认值和跨字段一致性校验的唯一来源。

    由 ``_build_ctx()`` 内部实例化，通过 ``to_dict()`` 转换为 plain dict。
    对外 API 仍然返回普通 dict（保持向后兼容）。
    Python 3.8 兼容：不使用 kw_only / slots。

    新增上下文键时，需同时更新：
    1. 此 dataclass 的字段定义
    2. ``ProjectContext`` TypedDict 的类型声明
    3. 对应的 sub-builder 函数
    4. ``__post_init__``（如需跨字段校验）
    """

    # 项目名称
    PROJECT_NAME: str = ""
    PROJECT_NAME_SNAKE: str = ""
    PROJECT_NAME_TITLE: str = ""
    PROJECT_NAME_PASCAL: str = ""
    PROJECT_DISPLAY_NAME: str = ""
    # 测试类型
    TEST_TYPES: list[str] = field(default_factory=list)
    IS_API: bool = False
    IS_UNIT: bool = False
    IS_INTEG: bool = False
    IS_E2E: bool = False
    TEST_TYPE_DESCRIPTION: str = ""
    # 语言与框架
    LANGUAGE: str = ""
    TEST_FRAMEWORK: str = ""
    IS_PYTHON: bool = False
    IS_JAVASCRIPT: bool = False
    IS_JAVA: bool = False
    # 数据库
    HAS_DB: bool = False
    DB_TYPE: str = "none"
    DB_SQLSERVER: bool = False
    DB_MYSQL: bool = False
    DB_POSTGRESQL: bool = False
    DB_SQLITE: bool = False
    DB_DEFAULT_PORT: str = ""
    DB_DRIVER: str = ""
    # 报告
    REPORT_TOOL: str = ""
    HAS_ALLURE: bool = False
    HAS_HTML_REPORT: bool = False
    # CI
    CI_SYSTEM: str = "none"
    CI_GITHUB: bool = False
    CI_GITLAB: bool = False
    HAS_CI: bool = False
    # 语言
    LANG_ZH: bool = False
    LANG_EN: bool = False
    # 业务线
    BUSINESS_LINES_RAW: list[str] = field(default_factory=list)
    BUSINESS_LINES: str = ""
    BUSINESS_LINES_LIST: str = ""
    BUSINESS_LINES_DIRS: str = ""
    # 派生值
    OUTPUT_DIR: str = ""
    RUN_SCRIPT_NAME: str = ""
    SKILL_PREFIX: str = ""
    HAS_HTTP: bool = False
    HAS_EMAIL: bool = False
    AUTH_MODULE_PATH: str = ""
    CONFIG_CLASS_NAME: str = ""
    API_CLASS_NAME: str = ""
    TESTSPEC_VERSION: str = ""

    def __post_init__(self) -> None:
        errors: list[str] = []
        if not self.PROJECT_NAME:
            errors.append("PROJECT_NAME 不能为空")
        if "-" in self.PROJECT_NAME_SNAKE:
            errors.append("PROJECT_NAME_SNAKE 不应包含连字符")
        # 测试类型与 HAS_HTTP 一致性
        expected_http = self.IS_API or self.IS_E2E or self.IS_INTEG
        if self.HAS_HTTP != expected_http:
            errors.append(
                f"HAS_HTTP={self.HAS_HTTP} 与测试类型不一致"
                f"(IS_API={self.IS_API}, IS_E2E={self.IS_E2E}, IS_INTEG={self.IS_INTEG})"
            )
        # 数据库一致性
        if self.HAS_DB and self.DB_TYPE in ("none", ""):
            errors.append("HAS_DB=True 时 DB_TYPE 不能为 'none' 或空")
        # CI 一致性
        if self.CI_GITHUB and self.CI_SYSTEM != "github":
            errors.append("CI_GITHUB=True 时 CI_SYSTEM 必须为 'github'")
        if self.CI_GITLAB and self.CI_SYSTEM != "gitlab":
            errors.append("CI_GITLAB=True 时 CI_SYSTEM 必须为 'gitlab'")
        # 报告一致性
        if self.HAS_ALLURE and self.REPORT_TOOL not in ("allure", "both"):
            errors.append("HAS_ALLURE=True 时 REPORT_TOOL 必须为 'allure' 或 'both'")
        if errors:
            raise ConfigError("; ".join(errors))

    def to_dict(self) -> dict[str, Any]:
        """转换为 plain dict，适合作为模板上下文消费。

        使用 ``dataclasses.asdict`` 进行深拷贝，
        返回的 dict 与原始模型互不影响。
        """
        return dataclasses.asdict(self)


def _build_ctx(
    *,
    project_name: str,
    test_types: list[str],
    language: str,
    framework: str,
    database: str,
    report_tool: str,
    business_lines: list[str],
    output_dir: str,
    ci_system: str,
    language_locale: str,
) -> ProjectContext:
    """核心上下文构建逻辑。

    将各维度的参数委托给独立的子函数构建，最后合并为统一的上下文。
    """
    ctx: dict[str, Any] = {
        **_build_name_ctx(project_name),
        **_build_test_type_ctx(test_types),
        **_build_language_ctx(language, framework),
        **_build_database_ctx(database),
        **_build_report_ctx(report_tool),
        **_build_ci_ctx(ci_system),
        **_build_locale_ctx(language_locale),
        **_build_business_ctx(business_lines),
        "OUTPUT_DIR": output_dir,
    }

    # 跨维度派生值
    ctx.update(_build_derived_ctx(
        snake=ctx["PROJECT_NAME_SNAKE"],
        pascal=ctx["PROJECT_NAME_PASCAL"],
        is_api=ctx["IS_API"],
        is_e2e=ctx["IS_E2E"],
        is_integ=ctx["IS_INTEG"],
    ))

    # 运行时跨字段一致性校验 + 转换为 plain dict
    model = _ProjectContextModel(**ctx)  # 校验 via __post_init__ + 构建
    return cast(ProjectContext, model.to_dict())


def _build_derived_ctx(
    *, snake: str, pascal: str,
    is_api: bool, is_e2e: bool, is_integ: bool,
) -> dict[str, Any]:
    """计算跨维度派生值。

    使用显式参数而非整个 ctx dict，使依赖关系在调用处可见。
    """
    return {
        "RUN_SCRIPT_NAME": f"run_{snake}_tests",
        "SKILL_PREFIX": "",
        "HAS_HTTP": is_api or is_e2e or is_integ,
        "HAS_EMAIL": False,
        "AUTH_MODULE_PATH": f"{snake}/client/auth_store.py",
        "CONFIG_CLASS_NAME": f"{pascal}Config",
        "API_CLASS_NAME": f"{pascal}Api",
        "TESTSPEC_VERSION": _VERSION,
    }


def _build_name_ctx(project_name: str) -> dict[str, Any]:
    """构建项目名称变体键。"""
    title_name = project_name.replace("-", " ").title()
    return {
        "PROJECT_NAME": project_name,
        "PROJECT_NAME_SNAKE": project_name.replace("-", "_"),
        "PROJECT_NAME_TITLE": title_name,
        "PROJECT_NAME_PASCAL": "".join(
            w.capitalize() for w in project_name.split("-")
        ),
        "PROJECT_DISPLAY_NAME": title_name,
    }


def _build_test_type_ctx(test_types: list[str]) -> dict[str, Any]:
    """构建测试类型布尔标志。"""
    types = test_types or ["api"]
    return {
        "TEST_TYPES": types,
        "IS_API": "api" in types,
        "IS_UNIT": "unit" in types,
        "IS_INTEG": "integ" in types,
        "IS_E2E": "e2e" in types,
        "TEST_TYPE_DESCRIPTION": "、".join(
            TYPE_DESC_MAP.get(t, t) for t in types
        ),
    }


def _build_language_ctx(language: str, framework: str) -> dict[str, Any]:
    """构建编程语言与框架标志。"""
    return {
        "LANGUAGE": language,
        "TEST_FRAMEWORK": framework,
        "IS_PYTHON": language == "python",
        "IS_JAVASCRIPT": language == "javascript",
        "IS_JAVA": language == "java",
    }


def _build_database_ctx(database: str) -> dict[str, Any]:
    """构建数据库配置标志。"""
    has_db = database not in ("none", "")
    db_type = database if has_db else "none"
    return {
        "HAS_DB": has_db,
        "DB_TYPE": db_type,
        "DB_SQLSERVER": database == "sqlserver",
        "DB_MYSQL": database == "mysql",
        "DB_POSTGRESQL": database == "postgresql",
        "DB_SQLITE": database == "sqlite",
        "DB_DEFAULT_PORT": DB_PORT_MAP.get(db_type, ""),
        "DB_DRIVER": DB_DRIVER_MAP.get(db_type, ""),
    }


def _build_report_ctx(report_tool: str) -> dict[str, Any]:
    """构建报告工具标志。"""
    return {
        "REPORT_TOOL": report_tool,
        "HAS_ALLURE": report_tool in ("allure", "both"),
        "HAS_HTML_REPORT": report_tool in ("html", "both"),
    }


def _build_ci_ctx(ci_system: str) -> dict[str, Any]:
    """构建 CI/CD 系统标志。"""
    return {
        "CI_SYSTEM": ci_system,
        "CI_GITHUB": ci_system == "github",
        "CI_GITLAB": ci_system == "gitlab",
        "HAS_CI": ci_system != "none",
    }


def _build_locale_ctx(language_locale: str) -> dict[str, Any]:
    """构建文档语言标志。"""
    return {
        "LANG_ZH": language_locale == "zh",
        "LANG_EN": language_locale == "en",
    }


def _build_business_ctx(business_lines: list[str]) -> dict[str, Any]:
    """构建业务线相关键。"""
    if not business_lines:
        business_lines = ["default"]
    for name in business_lines:
        if not _BIZ_NAME_RE.match(name):
            raise ConfigError(
                f"无效的业务线名称: {name!r}。"
                f"只允许小写字母开头，包含字母、数字、连字符、下划线。"
            )
    # 保持原始顺序去重
    seen: set[str] = set()
    ordered_unique: list[str] = []
    for b in business_lines:
        if b not in seen:
            seen.add(b)
            ordered_unique.append(b)
    sorted_unique = sorted(set(ordered_unique))
    return {
        "BUSINESS_LINES_RAW": ordered_unique,
        "BUSINESS_LINES": ", ".join(ordered_unique),
        "BUSINESS_LINES_LIST": (
            "{" + ", ".join(repr(b) for b in sorted_unique) + "}"
        ),
        "BUSINESS_LINES_DIRS": ", ".join(
            f"testcase/{b}/" for b in sorted_unique
        ),
    }
