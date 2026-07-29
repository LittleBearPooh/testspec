"""TestSpec — Spec-First Test Automation Engineering Framework.

规格优先的测试自动化工程化框架。

用法:
    pip install testspec
    testspec init              # 交互式初始化
    testspec init --config x.json  # 非交互式初始化
"""

from .constants import VERSION as __version__
from .exceptions import TestSpecError, ConfigError, TemplateError, GenerationError, ValidationError
from .generator import ProjectGenerator, generate_project, print_results
from .ci_builders import (
    build_requirements,
    build_gitignore,
    build_github_actions_yaml,
    build_gitlab_ci_yaml,
    build_testspec_manifest,
)
from .hooks import HookRegistry
from .plugins import discover_plugins
from .upgrader import ProjectUpgrader, upgrade_project, MANAGED_FILES, UpgradeAction

__all__ = [
    # 版本
    "__version__",
    # 异常
    "TestSpecError",
    "ConfigError",
    "TemplateError",
    "GenerationError",
    "ValidationError",
    # 生成器
    "ProjectGenerator",
    "generate_project",
    "print_results",
    # 内容构建器
    "build_requirements",
    "build_gitignore",
    "build_github_actions_yaml",
    "build_gitlab_ci_yaml",
    "build_testspec_manifest",
    # Hook 机制
    "HookRegistry",
    # 插件机制
    "discover_plugins",
    # 升级器
    "ProjectUpgrader",
    "upgrade_project",
    "MANAGED_FILES",
    "UpgradeAction",
]
