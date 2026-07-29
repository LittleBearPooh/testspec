"""TestSpec 项目升级器。

读取已生成项目的 testspec.json，重新生成框架管理的文件，
保留用户自有文件（testcase/, specs/, data/, variables_override.yaml 等）。
"""

from __future__ import annotations

import difflib
import json
import tempfile
from pathlib import Path
from typing import Any, Literal, NamedTuple

from .constants import VERSION, SKILL_FILES  # noqa: F401 — SKILL_FILES 保留向后兼容
from .context import ProjectContext, build_context_from_wizard
from .generator import generate_project
from .exceptions import ConfigError
from .sections import ALL_SECTION_CLASSES

__all__ = [
    "ProjectUpgrader",
    "upgrade_project",
    "MANAGED_FILES",
    "UpgradeAction",
]


# ---------------------------------------------------------------------------
# 框架管理的文件集合（从 Section Renderers 动态推导）
# ---------------------------------------------------------------------------

def _derive_managed_files() -> frozenset[str]:
    """从所有 SectionRenderer 类推导框架管理的文件集合。

    替代硬编码的 ``_MANAGED_FIXED``，新增 section 时只需在对应类中
    声明 ``managed_files()``，升级器会自动感知。
    """
    result: set[str] = set()
    for cls in ALL_SECTION_CLASSES:
        result.update(cls.managed_files())
    return frozenset(result)


MANAGED_FILES: frozenset[str] = _derive_managed_files()


def _is_managed(rel_path: str) -> bool:
    """判断相对路径是否由 TestSpec 框架管理。"""
    normalized = rel_path.replace("\\", "/")
    if normalized in MANAGED_FILES:
        return True
    # 运行脚本：根级 .ps1 和 .sh 文件
    parts = normalized.split("/")
    if len(parts) == 1 and (normalized.endswith(".ps1") or normalized.endswith(".sh")):
        return True
    return False


# ---------------------------------------------------------------------------
# UpgradeAction 结果类型
# ---------------------------------------------------------------------------

class UpgradeAction(NamedTuple):
    """升级操作结果。"""
    status: Literal["updated", "new", "unchanged", "skipped"]
    path: str         # 相对路径
    diff: str         # unified diff（仅 updated 时有值）
    new_content: str  # 新文件内容（供 apply 阶段写入，仅 updated/new 时有值）


# ---------------------------------------------------------------------------
# ProjectUpgrader
# ---------------------------------------------------------------------------

class ProjectUpgrader:
    """选择性重新生成框架管理的文件，保留用户测试代码。"""

    def __init__(
        self,
        project_dir: Path,
        templates_dir: Path,
        *,
        dry_run: bool = False,
    ) -> None:
        self.project_dir = project_dir.resolve()
        self.templates_dir = templates_dir
        self.dry_run = dry_run

    def upgrade(self) -> list[UpgradeAction]:
        """执行升级（向后兼容的一步到位入口）。

        等价于先调用 :meth:`plan` 再调用 :meth:`apply`。

        Returns:
            UpgradeAction 列表，每个元素描述一个文件的操作。
        """
        actions = self.plan()
        if not self.dry_run:
            return self.apply(actions)
        return actions

    def plan(self) -> list[UpgradeAction]:
        """阶段 1：只做 diff 比对，返回 UpgradeAction 列表。

        每个 ``updated`` / ``new`` 状态的 action 会缓存新文件内容到
        ``new_content`` 字段，供 :meth:`apply` 写入时使用，避免重复生成。

        Returns:
            UpgradeAction 列表。
        """
        manifest = self._read_manifest()
        ctx = self._rebuild_context(manifest)
        results: list[UpgradeAction] = []

        with tempfile.TemporaryDirectory(prefix="testspec_upgrade_") as tmp_out:
            tmp_ctx: dict[str, Any] = {**ctx, "OUTPUT_DIR": tmp_out}
            generate_project(tmp_ctx, self.templates_dir)
            tmp_path = Path(tmp_out)

            for generated_file in sorted(tmp_path.rglob("*")):
                if not generated_file.is_file():
                    continue
                rel = generated_file.relative_to(tmp_path)
                rel_str = str(rel).replace("\\", "/")

                if not _is_managed(rel_str):
                    results.append(UpgradeAction("skipped", rel_str, "", ""))
                    continue

                target = self.project_dir / rel
                new_content = generated_file.read_text(encoding="utf-8")

                if target.exists():
                    old_content = target.read_text(encoding="utf-8")
                    if old_content == new_content:
                        results.append(UpgradeAction("unchanged", rel_str, "", ""))
                        continue
                    diff = _compute_diff(old_content, new_content, rel_str)
                    results.append(UpgradeAction("updated", rel_str, diff, new_content))
                else:
                    results.append(UpgradeAction("new", rel_str, "", new_content))

        return results

    def apply(self, actions: list[UpgradeAction]) -> list[UpgradeAction]:
        """阶段 2：根据 :meth:`plan` 的结果写入磁盘。

        只处理 ``updated`` 和 ``new`` 状态的 action，使用缓存的
        ``new_content`` 写入文件，无需重新生成项目。

        Args:
            actions: :meth:`plan` 返回的 UpgradeAction 列表。

        Returns:
            实际写入的 UpgradeAction 列表（过滤掉 unchanged/skipped）。
        """
        applied: list[UpgradeAction] = []
        for action in actions:
            if action.status not in ("updated", "new"):
                continue
            target = self.project_dir / action.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(action.new_content, encoding="utf-8")
            applied.append(action)
        return applied

    def _read_manifest(self) -> dict[str, Any]:
        """读取 testspec.json 清单文件。"""
        manifest_path = self.project_dir / "testspec.json"
        if not manifest_path.exists():
            raise ConfigError(
                f"找不到 testspec.json：{manifest_path}\n"
                f"请确认目标目录是由 testspec init 生成的项目。"
            )
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ConfigError(f"testspec.json 格式错误: {e}") from e

    def _rebuild_context(self, manifest: dict[str, Any]) -> ProjectContext:
        """从清单文件重建上下文，旧清单缺失字段使用安全默认值。"""
        project_name = manifest.get("project_name")
        if not project_name:
            raise ConfigError(
                "testspec.json 缺少必需字段 'project_name'。\n"
                "文件可能是由旧版本生成的，请手动添加该字段后重试。"
            )
        return build_context_from_wizard(
            project_name=project_name,
            test_types=manifest.get("test_types", ["api"]),
            language=manifest.get("language", "python"),
            framework=manifest.get("framework", "pytest"),
            database=manifest.get("database", "none"),
            report_tool=manifest.get("report_tool", "allure"),
            business_lines=manifest.get("business_lines", ["default"]),
            output_dir=str(self.project_dir),
            ci_system=manifest.get("ci_system", "none"),
            language_locale=manifest.get("language_locale", "zh"),
        )


def _compute_diff(old: str, new: str, path: str) -> str:
    """生成 unified diff。"""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{path}", tofile=f"b/{path}",
        n=3,
    ))
    return "".join(diff)


def upgrade_project(
    project_dir: Path,
    templates_dir: Path,
    *,
    dry_run: bool = False,
) -> list[UpgradeAction]:
    """模块级入口（向后兼容的便捷函数）。"""
    return ProjectUpgrader(project_dir, templates_dir, dry_run=dry_run).upgrade()
