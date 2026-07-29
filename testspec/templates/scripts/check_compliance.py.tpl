# -*- coding: utf-8 -*-
"""合规自检脚本：扫描写操作测试用例是否包含数据库校验。

用法：
    python scripts/check_compliance.py

扫描范围：
    testcase/ 下的所有子目录（自动发现，跳过 __pycache__ 等）

识别写操作用例的规则：
    - 测试函数名命中 WRITE_KEYWORDS 之一
      （create/void/transfer/mark/switch/grab/complete/escalate/close/
        cancel/update/delete/assign/confirm/reply/send）
    - 且非 contract/smoke 用例（函数名或文件名含 contract/smoke 则跳过）

{{#IF_HAS_DB}}
检查项（DB 校验）：
    - 该函数所在文件是否 import 了 get_db 或 DbClient
    - 函数体内是否调用了 db.query / query_one / execute
{{/IF_HAS_DB}}

{{#IF_IS_UNIT}}
检查项（单元测试 Mock）：
    - 调用了外部依赖的函数是否使用了 mock.patch / MagicMock / mocker.patch
{{/IF_IS_UNIT}}

{{#IF_IS_E2E}}
检查项（E2E 终态断言）：
    - 端到端流程测试函数是否包含终态 assert 语句（不能只有 step attach，没有断言）
{{/IF_IS_E2E}}

输出：
    - 缺失清单（文件 / 函数名 / 行号 / 缺失项）
    - exit code 0 = 全部通过，1 = 存在缺失
"""

from __future__ import annotations

import ast
import io
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 写操作关键词（函数名含其一则视为写操作用例，需要 DB 校验）
WRITE_KEYWORDS = re.compile(
    r"(create|void|transfer|mark|switch|grab|"
    r"complete|escalate|close|cancel|update|delete|"
    r"assign|confirm|reply|send)",
    re.IGNORECASE,
)

# 跳过模式：contract 和 smoke 类型的用例不需要 DB 校验
SKIP_PATTERNS = re.compile(r"(contract|smoke)", re.IGNORECASE)

{{#IF_HAS_DB}}
# DB 工具 import 检测
DB_IMPORT_RE = re.compile(
    r"(from\s+utils\.db_client\s+import|import\s+.*DbClient|from\s+.*\s+import\s+.*get_db)",
)

# DB 调用检测
DB_CALL_RE = re.compile(
    r"\bdb\.(query|query_one|execute)\s*\("
)
{{/IF_HAS_DB}}

{{#IF_IS_UNIT}}
# Mock 使用检测（单元测试场景）
MOCK_IMPORT_RE = re.compile(
    r"(from\s+unittest\s+import\s+mock|import\s+unittest\.mock|"
    r"from\s+unittest\.mock\s+import|pytest_mock|mocker)",
)

MOCK_CALL_RE = re.compile(
    r"(mock\.patch|MagicMock|patch\(|mocker\.patch|monkeypatch\.setattr)",
)
{{/IF_IS_UNIT}}

{{#IF_IS_E2E}}
# E2E 终态断言检测（函数体内是否有 assert 语句）
E2E_ASSERT_RE = re.compile(
    r"^\s+assert\s",
)
{{/IF_IS_E2E}}

TEST_FUNC_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(",
)

# 扫描 testcase/ 下所有子目录（自动发现，惰性求值避免 import 时崩溃）
def _get_scan_dirs() -> list[Path]:
    """获取 testcase/ 下的所有业务线子目录。"""
    testcase_dir = PROJECT_ROOT / "testcase"
    if not testcase_dir.exists():
        return []
    return sorted(
        d for d in testcase_dir.iterdir()
        if d.is_dir() and not d.name.startswith("__")
    )


def _file_has_db_import(lines: list[str]) -> bool:
    """检查文件是否 import 了 DB 工具。"""
    {{#IF_HAS_DB}}
    return any(DB_IMPORT_RE.search(line) for line in lines)
    {{/IF_HAS_DB}}
    {{#IF_NOT_HAS_DB}}
    return True  # DB 校验未启用时默认通过
    {{/IF_NOT_HAS_DB}}


def _func_body_has_db_call(lines: list[str], start: int, end: int) -> bool:
    """检查函数体是否包含 DB 调用。"""
    {{#IF_HAS_DB}}
    for i in range(start, min(end, len(lines))):
        if DB_CALL_RE.search(lines[i]):
            return True
    return False
    {{/IF_HAS_DB}}
    {{#IF_NOT_HAS_DB}}
    return True  # DB 校验未启用时默认通过
    {{/IF_NOT_HAS_DB}}


{{#IF_IS_UNIT}}
def _func_body_has_mock(lines: list[str], start: int, end: int) -> bool:
    """检查函数体是否使用了 Mock（单元测试）。"""
    for i in range(start, min(end, len(lines))):
        if MOCK_CALL_RE.search(lines[i]):
            return True
    return False
{{/IF_IS_UNIT}}


{{#IF_IS_E2E}}
def _func_body_has_terminal_assert(lines: list[str], start: int, end: int) -> bool:
    """检查 E2E 函数体是否包含终态 assert 语句。"""
    for i in range(start, min(end, len(lines))):
        if E2E_ASSERT_RE.search(lines[i]):
            return True
    return False
{{/IF_IS_E2E}}


def _find_func_end(lines: list[str], start: int) -> int:
    """通过缩进变化确定函数结束行。"""
    if start >= len(lines):
        return len(lines)
    def_line = lines[start]
    def_indent = len(def_line) - len(def_line.lstrip())
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= def_indent and (
            line.strip().startswith("def ")
            or line.strip().startswith("class ")
            or line.strip().startswith("async def ")
            or line.strip().startswith("@")
        ):
            return i
    return len(lines)


{{#IF_HAS_DB}}
def _func_body_has_db_call_ast(source: str, func_name: str) -> bool:
    """使用 AST 精确检测函数是否调用了 db.query/query_one/execute。

    比正则更准确：能处理多行调用、注释中的伪调用、字符串中的调用名等。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if (isinstance(func, ast.Attribute)
                                and isinstance(func.value, ast.Name)
                                and func.value.id == "db"
                                and func.attr in ("query", "query_one", "execute")):
                            return True
    return False
{{/IF_HAS_DB}}


def scan_file(filepath: Path) -> list[dict]:
    """扫描单个测试文件，返回合规问题清单。"""
    findings: list[dict] = []
    filename = filepath.name

    # 跳过 contract 文件（文件名含 _contract）
    if "_contract" in filename or "_smoke" in filename or filename.startswith("smoke_"):
        return findings

    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return findings

    {{#IF_HAS_DB}}
    has_db_import = _file_has_db_import(lines)
    {{/IF_HAS_DB}}

    {{#IF_IS_UNIT}}
    has_mock_import = any(MOCK_IMPORT_RE.search(line) for line in lines)
    {{/IF_IS_UNIT}}

    for line_idx, line in enumerate(lines):
        match = TEST_FUNC_RE.match(line)
        if not match:
            continue

        func_name = match.group(1)

        # 跳过 contract/smoke 函数
        if SKIP_PATTERNS.search(func_name):
            continue

        # 只检查写操作函数
        if not WRITE_KEYWORDS.search(func_name):
            continue

        func_end = _find_func_end(lines, line_idx)
        missing_items: list[str] = []

        {{#IF_HAS_DB}}
        # 优先 AST 精确检测，回退正则
        full_source = filepath.read_text(encoding="utf-8")
        try:
            has_db_call = _func_body_has_db_call_ast(full_source, func_name)
        except Exception:
            has_db_call = _func_body_has_db_call(lines, line_idx, func_end)
        if not has_db_import or not has_db_call:
            missing_items.append("DB 校验" + ("" if has_db_import else "（文件未 import db_client）"))
        {{/IF_HAS_DB}}

        {{#IF_IS_UNIT}}
        if not has_mock_import or not _func_body_has_mock(lines, line_idx, func_end):
            missing_items.append("Mock 隔离" + ("" if has_mock_import else "（文件未 import mock）"))
        {{/IF_IS_UNIT}}

        {{#IF_IS_E2E}}
        if not _func_body_has_terminal_assert(lines, line_idx, func_end):
            missing_items.append("终态 assert 断言")
        {{/IF_IS_E2E}}

        if missing_items:
            findings.append({
                "file": str(filepath.relative_to(PROJECT_ROOT)),
                "function": func_name,
                "line": line_idx + 1,
                "missing": "、".join(missing_items),
            })

    return findings


def main() -> None:
    # 确保 Windows stdout 能正常输出 Unicode
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    all_findings: list[dict] = []

    for scan_dir in _get_scan_dirs():
        if not scan_dir.exists():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            if py_file.name.startswith("__"):
                continue
            all_findings.extend(scan_file(py_file))

    if not all_findings:
        print("[OK] 合规自检通过：所有写操作用例均满足合规要求。")
        sys.exit(0)

    print(f"[WARN] 发现 {len(all_findings)} 个写操作用例存在合规问题：\n")
    print(f"{'文件':<60} {'函数名':<45} {'行号':>5}  {'缺失项'}")
    print("-" * 140)
    for f in all_findings:
        print(f"{f['file']:<60} {f['function']:<45} {f['line']:>5}  {f['missing']}")

    print(f"\n共 {len(all_findings)} 项缺失，请补全对应校验后重新运行本脚本。")
    sys.exit(1)


if __name__ == "__main__":
    main()
