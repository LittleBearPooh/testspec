"""TestSpec 项目完整性校验器。

将验证逻辑从 CLI 层独立出来，使其可被程序化调用
（如 generator 后置校验、升级前校验等场景）。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Literal, NamedTuple

__all__ = [
    "ValidationResult",
    "ProjectValidator",
    "CHECKS",
]


# ---------------------------------------------------------------------------
# 合法的 pip requirements.txt 行前缀（非字母开头但合法的语法）
# ---------------------------------------------------------------------------
_VALID_PIP_LINE_PREFIXES: tuple[str, ...] = (
    "-r ",       # 递归引用其他 requirements 文件
    "-e ",       # 可编辑安装
    "-c ",       # 约束文件
    "--",        # 长选项 (--index-url, --trusted-host, --extra-index-url 等)
    "http://",   # 直接 URL 安装
    "https://",
    "git+",      # VCS 安装
    "svn+",
    "hg+",
    "bzr+",
)


def _is_valid_pip_line(stripped: str) -> bool:
    """判断 requirements.txt 中的一行是否为合法的 pip 语法。"""
    if stripped[0].isalpha():
        return True
    return any(stripped.startswith(p) for p in _VALID_PIP_LINE_PREFIXES)


# ---------------------------------------------------------------------------
# 扫描时排除的目录名（虚拟环境、缓存等）
# ---------------------------------------------------------------------------
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset({
    ".venv", "venv", "env", ".env", "__pycache__", ".git",
    "build", "dist", "node_modules", ".eggs",
})

# 按后缀匹配的排除目录名（如 *.egg-info）
_EXCLUDED_DIR_SUFFIXES: tuple[str, ...] = (".egg-info",)


def _is_excluded_dir(part: str) -> bool:
    """判断路径段是否为应排除的目录（精确匹配 + 后缀匹配）。"""
    if part in _EXCLUDED_DIR_NAMES:
        return True
    return any(part.endswith(suffix) for suffix in _EXCLUDED_DIR_SUFFIXES)


# ---------------------------------------------------------------------------
# 校验清单：(相对路径, 是否必须, 说明)
# ---------------------------------------------------------------------------
CHECKS: list[tuple[str, bool, str]] = [
    ("testspec.json", True, "TestSpec 版本标记文件"),
    ("requirements.txt", True, "Python 依赖清单"),
    ("pytest.ini", True, "pytest 配置"),
    ("conftest.py", True, "根 conftest"),
    ("CLAUDE.md", False, "AI 行为规则（AI 辅助项目）"),
    ("variables.yaml", True, "基础变量配置"),
    ("variables_override.yaml.template", False, "覆盖配置模板"),
    (".gitignore", True, "Git 忽略规则"),
    ("specs/registry.yaml", False, "接口注册表"),
    ("specs/spec-template.md", False, "规格文档模板"),
    ("testcase/conftest.py", True, "测试用例 conftest"),
    ("config/variable_loader.py", False, "配置加载器"),
    ("utils/http_client.py", False, "HTTP 客户端工具"),
    ("utils/logger.py", False, "日志工具"),
    ("scripts/validate_specs.py", False, "规格校验脚本"),
    ("scripts/check_compliance.py", False, "合规检查脚本"),
    ("scripts/mcp_server.py", False, "MCP 服务（AI 工具链）"),
    ("scripts/generate_skeletons.py", False, "测试骨架生成脚本"),
    (".claude/commands", False, "Claude Code 技能目录"),
]


class ValidationResult(NamedTuple):
    """单条校验结果。"""
    status: Literal["ok", "warning", "error"]
    category: Literal["structure", "manifest", "business", "skills", "syntax", "requirements", "json"]
    path: str         # 相对路径或描述
    message: str      # 人类可读的详情


class ProjectValidator:
    """封装所有项目完整性校验逻辑。

    Usage::

        validator = ProjectValidator(Path("./my-project"))
        results = validator.validate()
        passed, warnings, errors = validator.counts
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.resolve()
        self._results: list[ValidationResult] = []

    def validate(self) -> list[ValidationResult]:
        """执行全部校验并返回结果列表。"""
        self._results.clear()
        self._check_file_structure()
        self._check_manifest()
        self._check_business_lines()
        self._check_skill_files()
        self._check_python_syntax()
        self._check_requirements_fmt()
        self._check_json_files()
        return list(self._results)

    @property
    def counts(self) -> tuple[int, int, int]:
        """返回 (passed, warnings, errors) 计数。"""
        passed = sum(1 for r in self._results if r.status == "ok")
        warnings = sum(1 for r in self._results if r.status == "warning")
        errors = sum(1 for r in self._results if r.status == "error")
        return passed, warnings, errors

    def _add(
        self, status: str, category: str, path: str, message: str,
    ) -> None:
        self._results.append(ValidationResult(status, category, path, message))

    # -------------------------------------------------------------------
    # 校验步骤
    # -------------------------------------------------------------------

    def _check_file_structure(self) -> None:
        """检查文件/目录存在性。"""
        for rel_path, required, desc in CHECKS:
            target = self.project_dir / rel_path
            if target.exists():
                self._add("ok", "structure", rel_path, desc)
            elif required:
                self._add("error", "structure", rel_path, f"{desc}（缺失，必需）")
            else:
                self._add("warning", "structure", rel_path, f"{desc}（缺失，可选）")

    def _check_manifest(self) -> None:
        """校验 testspec.json 内容。"""
        manifest_path = self.project_dir / "testspec.json"
        if not manifest_path.exists():
            self._add(
                "error", "manifest", "testspec.json",
                "无法读取项目信息（testspec.json 缺失）",
            )
            return

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            version = data.get("testspec_version", "?")
            name = data.get("project_name", "?")
            types = ", ".join(data.get("test_types", []))
            lang = data.get("language", "?")
            fw = data.get("framework", "?")
            db = data.get("database", "?")
            self._add(
                "ok", "manifest", "testspec.json",
                f"{name} (v{version}) | {types} | {lang}/{fw} | DB: {db}",
            )
        except json.JSONDecodeError as e:
            self._add(
                "error", "manifest", "testspec.json",
                f"内容格式错误: {e}",
            )

    def _check_business_lines(self) -> None:
        """检查 testcase/ 下的业务线子目录。"""
        testcase_dir = self.project_dir / "testcase"
        if not testcase_dir.is_dir():
            return

        biz_dirs = sorted(
            d.name for d in testcase_dir.iterdir()
            if d.is_dir() and not d.name.startswith((".", "__"))
        )
        if biz_dirs:
            self._add(
                "ok", "business", "testcase/",
                f"业务线: {', '.join(biz_dirs)}",
            )
        else:
            self._add("warning", "business", "testcase/", "无业务线子目录")

    def _check_skill_files(self) -> None:
        """检查 .claude/commands/ 下的技能文件。"""
        skills_dir = self.project_dir / ".claude" / "commands"
        if not skills_dir.is_dir():
            return

        skill_files = list(skills_dir.glob("*.md"))
        if skill_files:
            self._add(
                "ok", "skills", ".claude/commands/",
                f"{len(skill_files)} 个技能文件",
            )
        else:
            self._add(
                "warning", "skills", ".claude/commands/",
                "无技能文件",
            )

    def _check_python_syntax(self) -> None:
        """校验所有 .py 文件的语法正确性。"""
        py_files = sorted(
            f for f in self.project_dir.rglob("*.py")
            if not any(_is_excluded_dir(part) for part in f.parts)
        )
        if not py_files:
            return

        py_ok = 0
        for pyf in py_files:
            try:
                ast.parse(
                    pyf.read_text(encoding="utf-8"), filename=str(pyf),
                )
                py_ok += 1
            except SyntaxError as e:
                rel = str(pyf.relative_to(self.project_dir))
                self._add(
                    "error", "syntax", rel,
                    f"Python 语法错误: 行 {e.lineno}: {e.msg}",
                )

        if py_ok == len(py_files):
            self._add(
                "ok", "syntax", "*.py",
                f"{py_ok} 个文件全部通过",
            )
        elif py_ok > 0:
            self._add(
                "error", "syntax", "*.py",
                f"{len(py_files) - py_ok}/{len(py_files)} 个文件有错误",
            )

    def _check_requirements_fmt(self) -> None:
        """校验 requirements.txt 格式。"""
        req_path = self.project_dir / "requirements.txt"
        if not req_path.exists():
            return

        lines = req_path.read_text(encoding="utf-8").splitlines()
        bad_lines: list[str] = []
        dep_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not _is_valid_pip_line(stripped):
                bad_lines.append(stripped)
            else:
                dep_count += 1

        if bad_lines:
            self._add(
                "error", "requirements", "requirements.txt",
                f"格式异常: {bad_lines[:3]}",
            )
        else:
            self._add(
                "ok", "requirements", "requirements.txt",
                f"{dep_count} 个依赖",
            )

    def _check_json_files(self) -> None:
        """校验所有 .json 文件的格式。"""
        json_files = sorted(
            f for f in self.project_dir.rglob("*.json")
            if not any(_is_excluded_dir(part) for part in f.parts)
        )
        if not json_files:
            return

        json_ok = 0
        for jf in json_files:
            try:
                json.loads(jf.read_text(encoding="utf-8"))
                json_ok += 1
            except json.JSONDecodeError as e:
                rel = str(jf.relative_to(self.project_dir))
                self._add("error", "json", rel, f"JSON 格式错误: {e}")

        if json_ok > 0 and json_ok == len(json_files):
            self._add(
                "ok", "json", "*.json",
                f"{json_ok} 个文件全部通过",
            )
