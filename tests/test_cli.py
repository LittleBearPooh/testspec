"""TestSpec CLI 入口测试。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from testspec.cli import main


class TestCLIVersion:
    """testspec version 子命令测试。"""

    def test_version_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["version"])
        captured = capsys.readouterr().out
        assert "TestSpec v" in captured
        assert "Spec-First" in captured


class TestCLINoCommand:
    """无子命令时显示帮助。"""

    def test_no_command_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([])
        captured = capsys.readouterr().out
        assert "testspec" in captured.lower() or "usage" in captured.lower()


class TestCLIInit:
    """testspec init 子命令测试。"""

    def test_init_with_config(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "test-proj",
            "test_types": ["api"],
            "output_dir": str(tmp_path / "output"),
        }), encoding="utf-8")

        main(["init", "--config", str(config), "-y"])

        output = tmp_path / "output"
        assert output.is_dir()
        assert (output / "requirements.txt").exists()

    def test_init_bad_config_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            main(["init", "--config", str(tmp_path / "nonexistent.json")])

    def test_init_malformed_json_exits(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.json"
        config.write_text("{invalid", encoding="utf-8")
        with pytest.raises(SystemExit):
            main(["init", "--config", str(config)])

    def test_init_dry_run_no_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--dry-run 应预览文件但不创建输出目录。"""
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "dry-proj",
            "test_types": ["api"],
            "output_dir": str(tmp_path / "output"),
        }), encoding="utf-8")

        main(["init", "--config", str(config), "--dry-run"])

        output = tmp_path / "output"
        assert not output.exists()

        captured = capsys.readouterr().out
        assert "DRY-RUN" in captured
        assert "dry-proj" not in captured or "预览" in captured

    def test_init_dry_run_shows_project_config(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--dry-run 输出应包含项目配置摘要。"""
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "my-api-tests",
            "test_types": ["api", "e2e"],
            "language": "python",
            "framework": "pytest",
            "database": "sqlserver",
            "output_dir": str(tmp_path / "output"),
        }), encoding="utf-8")

        main(["init", "--config", str(config), "--dry-run"])

        captured = capsys.readouterr().out
        assert "my-api-tests" in captured
        assert "python" in captured
        assert "sqlserver" in captured
        # 应包含汇总统计
        assert "汇总" in captured
        assert "个文件" in captured

    def test_init_dry_run_shows_file_count_per_section(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--dry-run 输出应显示每个分区的文件数。"""
        config = tmp_path / "config.json"
        config.write_text(json.dumps({
            "project_name": "section-test",
            "test_types": ["api"],
            "output_dir": str(tmp_path / "output"),
        }), encoding="utf-8")

        main(["init", "--config", str(config), "--dry-run"])

        captured = capsys.readouterr().out
        # 应包含至少一个分区的文件计数
        assert "个文件)" in captured
        # 应包含去掉 --dry-run 的提示
        assert "--dry-run" in captured


# ---------------------------------------------------------------------------
# validate 子命令测试
# ---------------------------------------------------------------------------

class TestCLIValidate:
    """testspec validate 子命令测试。"""

    def test_validate_generated_project(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """对已生成项目执行 validate 应通过。"""
        config = tmp_path / "config.json"
        output = tmp_path / "output"
        config.write_text(json.dumps({
            "project_name": "val-proj",
            "test_types": ["api"],
            "output_dir": str(output),
        }), encoding="utf-8")

        # 先生成项目
        main(["init", "--config", str(config), "-y"])

        # 再校验
        main(["validate", str(output)])
        captured = capsys.readouterr().out
        assert "校验结果" in captured
        assert "通过" in captured or "完整" in captured

    def test_validate_empty_directory_exits(
        self, tmp_path: Path,
    ) -> None:
        """空目录校验应失败退出。"""
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(SystemExit):
            main(["validate", str(empty)])

    def test_validate_nonexistent_dir_exits(
        self, tmp_path: Path,
    ) -> None:
        """不存在的目录应退出。"""
        with pytest.raises(SystemExit):
            main(["validate", str(tmp_path / "nonexistent")])

    def test_validate_shows_project_info(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """validate 应显示 testspec.json 中的项目信息。"""
        config = tmp_path / "config.json"
        output = tmp_path / "output"
        config.write_text(json.dumps({
            "project_name": "info-proj",
            "test_types": ["api", "unit"],
            "language": "python",
            "framework": "pytest",
            "output_dir": str(output),
        }), encoding="utf-8")

        main(["init", "--config", str(config), "-y"])
        main(["validate", str(output)])

        captured = capsys.readouterr().out
        assert "info-proj" in captured
        assert "python" in captured


# ---------------------------------------------------------------------------
# upgrade 子命令测试
# ---------------------------------------------------------------------------

class TestCLIUpgrade:
    """testspec upgrade 子命令测试。"""

    def test_upgrade_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """upgrade --dry-run 应预览变更但不修改文件。"""
        config = tmp_path / "config.json"
        output = tmp_path / "output"
        config.write_text(json.dumps({
            "project_name": "upgrade-proj",
            "test_types": ["api"],
            "output_dir": str(output),
        }), encoding="utf-8")

        # 先生成项目
        main(["init", "--config", str(config), "-y"])

        # 记录生成前的文件内容
        manifest_before = (output / "testspec.json").read_text(encoding="utf-8")

        # 执行 upgrade --dry-run
        main(["upgrade", str(output), "--dry-run"])
        captured = capsys.readouterr().out
        assert "预览" in captured or "dry-run" in captured.lower() or "DRY" in captured

        # dry-run 不应修改文件
        manifest_after = (output / "testspec.json").read_text(encoding="utf-8")
        assert manifest_before == manifest_after

    def test_upgrade_nonexistent_dir_exits(self, tmp_path: Path) -> None:
        """不存在的目录应退出。"""
        with pytest.raises(SystemExit):
            main(["upgrade", str(tmp_path / "nonexistent")])

    def test_upgrade_happy_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """upgrade 应重新生成框架管理的文件并保持用户文件不变。"""
        config = tmp_path / "config.json"
        output = tmp_path / "output"
        config.write_text(json.dumps({
            "project_name": "upgrade-proj",
            "test_types": ["api"],
            "output_dir": str(output),
        }), encoding="utf-8")

        # 先生成项目
        main(["init", "--config", str(config), "-y"])

        # 模拟用户修改了框架管理的文件
        (output / "requirements.txt").write_text("# user modified\n", encoding="utf-8")

        # 添加用户自有文件
        user_file = output / "testcase" / "my_test.py"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text("# user test code\n", encoding="utf-8")

        # 执行 upgrade（-y 跳过确认）
        main(["upgrade", str(output), "-y"])
        captured = capsys.readouterr().out
        assert "升级完成" in captured or "CHANGED" in captured

        # 框架管理的文件应被恢复
        req_content = (output / "requirements.txt").read_text(encoding="utf-8")
        assert "# user modified" not in req_content
        assert "pytest" in req_content

        # 用户自有文件应保留
        assert user_file.exists()
        assert (output / "testcase" / "my_test.py").read_text(encoding="utf-8") == "# user test code\n"

    def test_upgrade_already_up_to_date(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """已生成项目立即 upgrade 应显示无需升级。"""
        config = tmp_path / "config.json"
        output = tmp_path / "output"
        config.write_text(json.dumps({
            "project_name": "current-proj",
            "test_types": ["api"],
            "output_dir": str(output),
        }), encoding="utf-8")

        main(["init", "--config", str(config), "-y"])
        main(["upgrade", str(output), "-y"])

        captured = capsys.readouterr().out
        assert "无需升级" in captured or "0 个文件已更新" in captured
