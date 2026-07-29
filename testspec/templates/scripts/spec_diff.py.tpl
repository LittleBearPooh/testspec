# -*- coding: utf-8 -*-
"""Spec 变更影响分析工具。

对比 spec 变更，分析影响的测试用例。

用法:
    python scripts/spec_diff.py                   # 对比工作区未提交的变更
    python scripts/spec_diff.py --staged           # 对比已暂存的变更
    python scripts/spec_diff.py --branch main      # 对比指定分支

工作方式:
    1. 通过 git diff 获取 specs/ 目录的变更文件列表
    2. 对比 registry.yaml 的变更（新增/删除/修改参数或响应码）
    3. 扫描 testcase/ 中引用受影响 spec 的测试文件
    4. 输出受影响测试清单和建议操作

退出码:
    0 = 无变更或分析完成
    1 = 分析出错
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "specs" / "registry.yaml"
TESTCASE_DIR = PROJECT_ROOT / "testcase"

SPEC_REF_RE = re.compile(r"spec:\s*(specs/\S+\.md)")


def git_diff_files(mode: str, branch: str | None) -> list[str]:
    """获取 specs/ 目录下的变更文件列表。"""
    cmd = ["git", "diff", "--name-only"]
    if mode == "staged":
        cmd.append("--cached")
    elif branch:
        cmd.extend([f"{branch}...HEAD"])
    cmd.append("specs/")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
        )
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def git_diff_registry(mode: str, branch: str | None) -> str:
    """获取 registry.yaml 的 diff 内容。"""
    cmd = ["git", "diff"]
    if mode == "staged":
        cmd.append("--cached")
    elif branch:
        cmd.extend([f"{branch}...HEAD"])
    cmd.append("specs/registry.yaml")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def load_registry() -> dict[str, dict]:
    """加载 registry，返回 {spec_file: spec_dict} 映射。"""
    if not REGISTRY_PATH.exists():
        return {}
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    specs = data.get("specs", [])
    return {s["file"]: s for s in specs if "file" in s}


def find_tests_referencing(spec_file: str) -> list[dict]:
    """找到引用指定 spec 文件的测试函数。"""
    results = []
    if not TESTCASE_DIR.exists():
        return results

    for py_file in TESTCASE_DIR.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for i, line in enumerate(lines):
            if SPEC_REF_RE.search(line) and spec_file in line:
                # 向上查找函数定义
                func_name = None
                for j in range(i, max(-1, i - 100), -1):
                    m = re.match(r"\s*def\s+(test_\w+)", lines[j])
                    if m:
                        func_name = m.group(1)
                        break

                results.append({
                    "file": str(py_file.relative_to(PROJECT_ROOT)),
                    "line": i + 1,
                    "function": func_name or "(unknown)",
                })

    return results


def parse_registry_diff(diff_text: str) -> list[str]:
    """从 registry.yaml 的 diff 中提取变更类型。"""
    changes = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            stripped = line[1:].strip()
            if re.match(r'^\s*-\s*name:\s', stripped) or re.match(r'^name:\s', stripped):
                changes.append(f"新增参数: {stripped}")
            elif "codes:" in stripped or "code:" in stripped:
                changes.append(f"变更响应码: {stripped}")
            elif "table:" in stripped:
                changes.append(f"变更 DB 影响: {stripped}")
            elif "- id:" in stripped or "id:" in stripped:
                changes.append(f"新增/修改 spec: {stripped}")
    return changes


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Spec 变更影响分析")
    parser.add_argument("--staged", action="store_true", help="对比已暂存的变更")
    parser.add_argument("--branch", type=str, help="对比指定分支")
    args = parser.parse_args()

    mode = "staged" if args.staged else "unstaged"
    branch = args.branch

    # 获取变更文件
    changed_files = git_diff_files(mode, branch)
    if not changed_files:
        print("[OK] specs/ 目录无变更。")
        return

    print(f"\n=== Spec 变更影响分析 ===\n")
    print(f"变更文件: {len(changed_files)} 个\n")

    registry = load_registry()
    total_affected = 0

    # 分析每个变更文件
    for changed in changed_files:
        print(f"📄 {changed}")
        spec = registry.get(changed)

        if spec:
            api = spec.get("api", {})
            print(f"   接口: {api.get('method', '?')} {api.get('path', '?')}")

            params = spec.get("parameters") or []
            if params:
                req_params = [p["name"] for p in params if p.get("required")]
                print(f"   必填参数: {', '.join(req_params)}")

        # 查找受影响的测试
        tests = find_tests_referencing(changed)
        if tests:
            total_affected += len(tests)
            for t in tests:
                print(f"   → 影响: {t['file']}::{t['function']} (行 {t['line']})")
        else:
            print(f"   → 无对应测试（建议新增）")
        print()

    # 分析 registry.yaml 自身的变更
    if "specs/registry.yaml" in changed_files:
        diff_text = git_diff_registry(mode, branch)
        changes = parse_registry_diff(diff_text)
        if changes:
            print("📋 registry.yaml 结构性变更:")
            for c in changes[:10]:  # 最多显示 10 条
                print(f"   {c}")
            print()

    # 汇总
    print(f"{'─' * 50}")
    print(f"受影响测试: {total_affected} 个")
    if total_affected > 0:
        print("\n建议操作:")
        print("  1. 运行受影响的测试确认是否通过: pytest <file> -v")
        print("  2. 如测试失败，检查是否需要更新断言或测试数据")
        print("  3. 如果是新增参数/响应码，运行 /case-design 补充用例")
    else:
        print("\n建议操作:")
        print("  1. 对变更的 spec 运行 /case-design 检查是否有遗漏用例")
        print("  2. 运行 python scripts/generate_skeletons.py 生成缺失的测试骨架")


if __name__ == "__main__":
    main()
