"""TestSpec 常量定义（精简版）。

向后兼容：所有历史导出名称仍可从此模块直接导入。
拆分后的职责：
  - registry.py  → OptionRegistry 机制
  - catalogs.py  → 数据映射表、技能文件列表
  - constants.py → 版本号、枚举、验证集合、CI/输出常量、注册表实例
"""

from __future__ import annotations

import re
from enum import Enum

# ---------------------------------------------------------------------------
# 向后兼容重导出
# ---------------------------------------------------------------------------
from .registry import OptionRegistry  # noqa: F401
from .catalogs import (  # noqa: F401
    TYPE_DESC_MAP,
    DB_PORT_MAP,
    DB_DRIVER_MAP,
    DB_DEPS,
    SkillFile,
    SKILL_FILES,
)

__all__ = [
    "VERSION",
    "OptionRegistry",
    "TEST_TYPES",
    "LANG_FRAMEWORKS",
    "DB_TYPES",
    "REPORT_TOOLS",
    "CI_SYSTEMS",
    "LANGUAGES",
    "VALID_TEST_TYPES",
    "VALID_DATABASES",
    "KNOWN_CONFIG_KEYS",
    "PROJECT_NAME_PATTERN",
    "TestType",
    "DatabaseType",
    "CISystem",
    "SkillFile",
    "TYPE_DESC_MAP",
    "DB_PORT_MAP",
    "DB_DRIVER_MAP",
    "DB_DEPS",
    "SKILL_FILES",
    "CI_PYTHON_VERSION",
    "CI_COVERAGE_THRESHOLD",
    "CI_FLAKY_THRESHOLD",
    "CI_TEST_RERUNS",
    "CI_RERUNS_DELAY",
    "SEPARATOR_WIDTH",
    "SEPARATOR",
]

VERSION = "1.2.0"


# ---------------------------------------------------------------------------
# 测试类型选项
# ---------------------------------------------------------------------------
TEST_TYPES = OptionRegistry("test_types")
TEST_TYPES.register("1", ("api", "HTTP 接口自动化测试（含 DB 校验）"))
TEST_TYPES.register("2", ("unit", "单元测试（含 Mock 验证）"))
TEST_TYPES.register("3", ("integ", "集成测试（含系统状态验证）"))
TEST_TYPES.register("4", ("e2e", "端到端测试（完整用户旅程）"))

# ---------------------------------------------------------------------------
# 语言与框架选项
# ---------------------------------------------------------------------------
LANG_FRAMEWORKS = OptionRegistry("lang_frameworks")
LANG_FRAMEWORKS.register("1", ("python", "pytest", "Python / pytest（推荐，工具桩完整）"))
LANG_FRAMEWORKS.register("2", ("python", "unittest", "Python / unittest"))
LANG_FRAMEWORKS.register("3", ("javascript", "jest", "JavaScript / Jest（工具桩需手动移植）"))
LANG_FRAMEWORKS.register("4", ("java", "junit5", "Java / JUnit5（工具桩需手动移植）"))

# ---------------------------------------------------------------------------
# 数据库选项
# ---------------------------------------------------------------------------
DB_TYPES = OptionRegistry("db_types")
DB_TYPES.register("1", ("sqlserver", "SQL Server（pymssql）"))
DB_TYPES.register("2", ("mysql", "MySQL（PyMySQL）"))
DB_TYPES.register("3", ("postgresql", "PostgreSQL（psycopg2）"))
DB_TYPES.register("4", ("sqlite", "SQLite（标准库，无需安装驱动）"))
DB_TYPES.register("5", ("none", "暂不配置（后续手动添加）"))

# ---------------------------------------------------------------------------
# 报告工具选项
# ---------------------------------------------------------------------------
REPORT_TOOLS = OptionRegistry("report_tools")
REPORT_TOOLS.register("1", ("allure", "Allure（推荐）"))
REPORT_TOOLS.register("2", ("html", "pytest-html"))
REPORT_TOOLS.register("3", ("both", "Allure + pytest-html"))

# ---------------------------------------------------------------------------
# CI 系统选项
# ---------------------------------------------------------------------------
CI_SYSTEMS = OptionRegistry("ci_systems")
CI_SYSTEMS.register("1", ("github", "GitHub Actions"))
CI_SYSTEMS.register("2", ("gitlab", "GitLab CI"))
CI_SYSTEMS.register("3", ("none", "暂不配置"))

# ---------------------------------------------------------------------------
# 语言选项
# ---------------------------------------------------------------------------
LANGUAGES = OptionRegistry("languages")
LANGUAGES.register("1", ("zh", "中文"))
LANGUAGES.register("2", ("en", "English"))

# ---------------------------------------------------------------------------
# 校验集合（供 context.py 和其他模块复用）
# ---------------------------------------------------------------------------
VALID_TEST_TYPES: frozenset[str] = TEST_TYPES.valid_values()
VALID_DATABASES: frozenset[str] = DB_TYPES.valid_values()

# JSON 配置文件已知键（用于拼写检查）
KNOWN_CONFIG_KEYS: frozenset[str] = frozenset({
    "project_name", "test_types", "language", "framework",
    "database", "report_tool", "business_lines", "output_dir",
    "ci_system", "language_locale",
})

# 项目名称格式校验正则
PROJECT_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9-]*$")

# ---------------------------------------------------------------------------
# 类型安全枚举（继承 str 确保与模板引擎兼容：Enum.API == "api" 为 True）
# ---------------------------------------------------------------------------

class TestType(str, Enum):
    """测试类型枚举。"""
    API = "api"
    UNIT = "unit"
    INTEG = "integ"
    E2E = "e2e"


class DatabaseType(str, Enum):
    """数据库类型枚举。"""
    SQLSERVER = "sqlserver"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    NONE = "none"


class CISystem(str, Enum):
    """CI/CD 系统枚举。"""
    GITHUB = "github"
    GITLAB = "gitlab"
    NONE = "none"

# ---------------------------------------------------------------------------
# CI 生成配置常量
# ---------------------------------------------------------------------------
CI_PYTHON_VERSION: str = "3.11"
CI_COVERAGE_THRESHOLD: int = 70
CI_FLAKY_THRESHOLD: int = 95
CI_TEST_RERUNS: int = 2
CI_RERUNS_DELAY: int = 3

# ---------------------------------------------------------------------------
# 输出格式常量
# ---------------------------------------------------------------------------
SEPARATOR_WIDTH: int = 56
SEPARATOR: str = "=" * SEPARATOR_WIDTH
