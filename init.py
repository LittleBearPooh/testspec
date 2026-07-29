#!/usr/bin/env python3
"""
TestSpec 框架脚手架脚本 v1.0.0
规格优先的测试自动化工程化框架

用法:
  python init.py                        # 交互式初始化（向后兼容）
  testspec init                         # 推荐方式（pip install 后）
  testspec init --config project.json   # 非交互式初始化

要求:  Python 3.9+
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """向后兼容入口：委托给 testspec.cli。"""
    try:
        from testspec.cli import main as cli_main
        cli_main(["init"])
    except ImportError:
        # 如果 testspec 包未安装，尝试将项目根目录加入 sys.path 后直接导入
        _legacy_main()


def _legacy_main() -> None:
    """内置的回退入口：当 testspec 包未通过 pip 安装时，
    将项目根目录加入 sys.path 以便直接 import testspec 子模块。

    这避免了在 init.py 中内联复制全部逻辑导致的维护负担。
    """
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from testspec.cli import main as cli_main
    except ImportError:
        print("[ERROR] testspec 包不可用。")
        print("请运行以下命令之一进行安装：")
        print("  pip install -e .        # 开发模式安装")
        print("  pip install .           # 正式安装")
        print("或直接使用: testspec init")
        sys.exit(1)

    cli_main(["init"])


if __name__ == "__main__":
    main()
