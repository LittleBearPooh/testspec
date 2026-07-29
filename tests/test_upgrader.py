"""TestSpec 升级器测试。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from testspec.upgrader import (
    ProjectUpgrader,
    MANAGED_FILES,
    UpgradeAction,
    _is_managed,
    upgrade_project,
)
from testspec.generator import generate_project
from testspec.exceptions import ConfigError


class TestManagedFiles:

    def test_claude_md_managed(self) -> None:
        assert _is_managed("CLAUDE.md")

    def test_testcase_not_managed(self) -> None:
        assert not _is_managed("testcase/order/test_payment.py")

    def test_specs_not_managed(self) -> None:
        assert not _is_managed("specs/order/payment-spec.md")

    def test_utils_managed(self) -> None:
        assert _is_managed("utils/http_client.py")

    def test_scripts_managed(self) -> None:
        assert _is_managed("scripts/check_compliance.py")

    def test_run_script_managed(self) -> None:
        assert _is_managed("run_order_service_tests.ps1")

    def test_skill_file_managed(self) -> None:
        assert _is_managed(".claude/commands/test-workflow.md")

    def test_variables_override_not_managed(self) -> None:
        assert not _is_managed("variables_override.yaml")

    def test_data_dir_not_managed(self) -> None:
        assert not _is_managed("data/yaml/test_data.yaml")


class TestProjectUpgrader:

    def test_upgrade_restores_corrupted_file(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        # 损坏一个管理文件
        (output / "utils" / "http_client.py").write_text(
            "# CORRUPTED", encoding="utf-8",
        )

        results = upgrade_project(output, templates_dir, dry_run=False)
        updated_paths = {r.path for r in results if r.status == "updated"}
        assert "utils/http_client.py" in updated_paths

        content = (output / "utils" / "http_client.py").read_text(encoding="utf-8")
        assert "# CORRUPTED" not in content

    def test_upgrade_preserves_user_files(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        user_test = output / "testcase" / "order" / "test_custom.py"
        user_test.write_text("def test_my(): pass", encoding="utf-8")

        upgrade_project(output, templates_dir, dry_run=False)
        assert user_test.exists()
        assert user_test.read_text(encoding="utf-8") == "def test_my(): pass"

    def test_upgrade_dry_run_no_changes(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        (output / "utils" / "http_client.py").write_text(
            "# CORRUPTED", encoding="utf-8",
        )

        upgrade_project(output, templates_dir, dry_run=True)
        assert (output / "utils" / "http_client.py").read_text(
            encoding="utf-8",
        ) == "# CORRUPTED"

    def test_upgrade_missing_manifest_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ConfigError, match="testspec.json"):
            upgrade_project(empty, Path("/nonexistent"))

    def test_upgrade_result_types(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        results = upgrade_project(output, templates_dir, dry_run=True)
        for r in results:
            assert r.status in ("updated", "new", "unchanged", "skipped")
            assert isinstance(r.path, str)


class TestPlanApply:
    """plan() / apply() 两阶段升级测试。"""

    def test_plan_returns_actions_with_content(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """plan() 返回的 updated action 应包含 new_content。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        # 损坏一个管理文件以产生 diff
        (output / "utils" / "http_client.py").write_text(
            "# CORRUPTED", encoding="utf-8",
        )

        upgrader = ProjectUpgrader(output, templates_dir)
        actions = upgrader.plan()

        updated = [a for a in actions if a.status == "updated"]
        assert len(updated) > 0
        for a in updated:
            assert a.new_content, f"updated action for {a.path} should have new_content"
            assert "# CORRUPTED" not in a.new_content

    def test_plan_does_not_modify_files(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """plan() 只做 diff 比对，不修改磁盘文件。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        (output / "utils" / "http_client.py").write_text(
            "# CORRUPTED", encoding="utf-8",
        )

        upgrader = ProjectUpgrader(output, templates_dir)
        upgrader.plan()

        # 文件应保持损坏状态
        assert (output / "utils" / "http_client.py").read_text(
            encoding="utf-8",
        ) == "# CORRUPTED"

    def test_apply_writes_cached_content(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """apply() 使用 plan() 缓存的 new_content 写入文件。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        (output / "utils" / "http_client.py").write_text(
            "# CORRUPTED", encoding="utf-8",
        )

        upgrader = ProjectUpgrader(output, templates_dir)
        actions = upgrader.plan()
        upgrader.apply(actions)

        content = (output / "utils" / "http_client.py").read_text(encoding="utf-8")
        assert "# CORRUPTED" not in content
        assert len(content) > 0

    def test_apply_skips_unchanged_and_skipped(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """apply() 只处理 updated/new 状态的 action。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        upgrader = ProjectUpgrader(output, templates_dir)
        actions = upgrader.plan()

        applied = upgrader.apply(actions)
        # 所有项目刚生成，没有 updated/new
        assert len(applied) == 0

    def test_upgrade_equals_plan_plus_apply(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """upgrade() 应等价于 plan() + apply()，结果一致。"""
        # 项目 A: 使用 upgrade()
        out_a = tmp_path / "proj_a"
        ctx_a = {**base_ctx, "OUTPUT_DIR": str(out_a)}
        generate_project(ctx_a, templates_dir)
        (out_a / "utils" / "http_client.py").write_text("# BAD", encoding="utf-8")
        results_a = upgrade_project(out_a, templates_dir, dry_run=False)

        # 项目 B: 使用 plan() + apply()
        out_b = tmp_path / "proj_b"
        ctx_b = {**base_ctx, "OUTPUT_DIR": str(out_b)}
        generate_project(ctx_b, templates_dir)
        (out_b / "utils" / "http_client.py").write_text("# BAD", encoding="utf-8")
        upgrader_b = ProjectUpgrader(out_b, templates_dir)
        plan_b = upgrader_b.plan()
        upgrader_b.apply(plan_b)

        # 两个项目的 http_client.py 应一致
        assert (out_a / "utils" / "http_client.py").read_text(
            encoding="utf-8",
        ) == (out_b / "utils" / "http_client.py").read_text(encoding="utf-8")

    def test_upgrade_action_has_new_content_field(
        self, base_ctx: dict[str, Any], templates_dir: Path, tmp_path: Path,
    ) -> None:
        """UpgradeAction 应包含 new_content 字段（4 元组）。"""
        output = tmp_path / "proj"
        ctx = {**base_ctx, "OUTPUT_DIR": str(output)}
        generate_project(ctx, templates_dir)

        upgrader = ProjectUpgrader(output, templates_dir)
        actions = upgrader.plan()
        for a in actions:
            assert len(a) == 4
            assert isinstance(a.new_content, str)
