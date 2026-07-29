"""TestSpec 数据目录：类型映射表、数据库映射、技能文件列表。

将具体的数据映射从 constants.py 分离出来，
constants.py 只保留枚举、验证集合和真正的常量。
"""

from __future__ import annotations

from typing import NamedTuple

__all__ = [
    "TYPE_DESC_MAP",
    "DB_PORT_MAP",
    "DB_DRIVER_MAP",
    "DB_DEPS",
    "SkillFile",
    "SKILL_FILES",
]

# ---------------------------------------------------------------------------
# 类型描述映射
# ---------------------------------------------------------------------------
TYPE_DESC_MAP: dict[str, str] = {
    "api": "HTTP 接口自动化测试",
    "unit": "单元测试",
    "integ": "集成测试",
    "e2e": "端到端测试",
}

# ---------------------------------------------------------------------------
# 数据库映射表
# ---------------------------------------------------------------------------
DB_PORT_MAP: dict[str, str] = {
    "sqlserver": "1433",
    "mysql": "3306",
    "postgresql": "5432",
    "sqlite": "",
    "none": "",
}

DB_DRIVER_MAP: dict[str, str] = {
    "sqlserver": "pymssql",
    "mysql": "pymysql",
    "postgresql": "psycopg2",
    "sqlite": "sqlite3",
    "none": "",
}

DB_DEPS: dict[str, tuple[str, ...]] = {
    "sqlserver": ("pymssql>=2.3", "dbutils>=3.0.0"),
    "mysql": ("PyMySQL>=1.1", "dbutils>=3.0.0"),
    "postgresql": ("psycopg2-binary>=2.9", "dbutils>=3.0.0"),
}

# 跨模块一致性检查（在模块加载时执行）
if set(DB_PORT_MAP.keys()) != set(DB_DRIVER_MAP.keys()):
    raise RuntimeError("DB_PORT_MAP 和 DB_DRIVER_MAP 的键必须一致")

# ---------------------------------------------------------------------------
# 技能文件列表
# ---------------------------------------------------------------------------

class SkillFile(NamedTuple):
    """技能文件定义：模板文件名和对应的技能名称。"""
    template: str
    name: str


SKILL_FILES: tuple[SkillFile, ...] = (
    SkillFile("00-test-workflow.md.tpl", "test-workflow"),
    SkillFile("01-case-design.md.tpl", "case-design"),
    SkillFile("02-test-data.md.tpl", "test-data"),
    SkillFile("03-write-tests.md.tpl", "write-tests"),
    SkillFile("04-assertion-design.md.tpl", "assertion-design"),
    SkillFile("05-data-verify.md.tpl", "data-verify"),
    SkillFile("06-report-decorate.md.tpl", "report-decorate"),
    SkillFile("07-compliance-check.md.tpl", "compliance-check"),
    SkillFile("08-spec-review.md.tpl", "spec-review"),
    SkillFile("09-mock-setup.md.tpl", "mock-setup"),
    SkillFile("10-contract-test.md.tpl", "contract-test"),
    SkillFile("11-analyze-ci.md.tpl", "analyze-ci-failures"),
    SkillFile("12-spec-diff.md.tpl", "spec-diff"),
    SkillFile("13-automated-testing.md.tpl", "AutomatedTesting"),
    SkillFile("99-debug-failure.md.tpl", "debug-failure"),
)
