"""TestSpec 测试共享 fixture。

集中管理跨测试文件复用的 fixture，避免重复定义。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from testspec.context import build_context_from_wizard, ProjectContext


@pytest.fixture
def base_wizard_params() -> dict[str, Any]:
    """返回一组完整的向导参数默认值。"""
    return dict(
        project_name="order-service",
        test_types=["api", "e2e"],
        language="python",
        framework="pytest",
        database="sqlserver",
        report_tool="allure",
        business_lines=["order", "payment"],
        output_dir="./order-service",
        ci_system="github",
        language_locale="zh",
    )


@pytest.fixture
def base_ctx(base_wizard_params: dict[str, Any]) -> ProjectContext:
    """返回使用默认参数构建的完整上下文。"""
    return build_context_from_wizard(**base_wizard_params)


@pytest.fixture
def templates_dir() -> Path:
    """返回模板目录路径。"""
    from testspec.cli import _find_templates_dir
    return _find_templates_dir()
