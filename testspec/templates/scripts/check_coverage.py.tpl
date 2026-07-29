# -*- coding: utf-8 -*-
"""Spec-to-Test 覆盖率报告工具。

计算 specs/registry.yaml 中注册的 spec 与 testcase/ 下测试代码的覆盖率。

用法:
    python scripts/check_coverage.py              # 完整报告
    python scripts/check_coverage.py --json       # JSON 输出（CI 消费）

工作方式:
    1. 读取 specs/registry.yaml
    2. 扫描 testcase/ 下所有 .py 文件的 docstring 中的 spec: 标记
    3. 对比哪些 spec 有对应测试，哪些没有
    4. 输出覆盖率报告

退出码:
    0 = 覆盖率 >= 阈值（默认 80%）
    1 = 覆盖率 < 阈值
    2 = 运行错误（registry 不存在等）
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "specs" / "registry.yaml"
TESTCASE_DIR = PROJECT_ROOT / "testcase"

# 匹配 docstring 中的 spec 标记：spec: specs/order/create-order.md
SPEC_REF_RE = re.compile(r"spec:\s*(specs/\S+\.md)")

DEFAULT_THRESHOLD = 80.0


def load_registry() -> list[dict] | None:
    """加载 registry.yaml 中的 specs 列表。"""
    if not REGISTRY_PATH.exists():
        print(f"[ERROR] 注册表不存在: {REGISTRY_PATH}")
        return None
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "specs" not in data:
        print("[ERROR] registry.yaml 中缺少 specs 列表")
        return None
    return data["specs"]


def scan_test_refs() -> dict[str, set[str]]:
    """扫描 testcase/ 下所有 .py 文件，提取 spec: 引用。

    返回: { spec_file_path: set(test_file_paths) }
    """
    refs: dict[str, set[str]] = {}

    if not TESTCASE_DIR.exists():
        return refs

    for py_file in TESTCASE_DIR.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for match in SPEC_REF_RE.finditer(content):
            spec_path = match.group(1)
            if spec_path not in refs:
                refs[spec_path] = set()
            refs[spec_path].add(str(py_file.relative_to(PROJECT_ROOT)))

    return refs


def build_coverage_report(specs: list[dict], refs: dict[str, set[str]]) -> dict:
    """构建覆盖率报告数据。"""
    by_business: dict[str, dict] = {}
    total = 0
    covered = 0
    uncovered_specs: list[dict] = []

    for spec in specs:
        spec_file = spec.get("file", "")
        spec_id = spec.get("id", "?")

        # 从文件路径推断业务线：specs/order/create-order.md → order
        parts = Path(spec_file).parts
        business = parts[1] if len(parts) >= 3 else "unknown"

        if business not in by_business:
            by_business[business] = {"total": 0, "covered": 0, "uncovered": []}

        by_business[business]["total"] += 1
        total += 1

        if spec_file in refs:
            by_business[business]["covered"] += 1
            covered += 1
        else:
            by_business[business]["uncovered"].append(spec_id)
            uncovered_specs.append({
                "id": spec_id,
                "file": spec_file,
                "business": business,
            })

    rate = (covered / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "covered": covered,
        "uncovered": total - covered,
        "rate": round(rate, 1),
        "by_business": by_business,
        "uncovered_specs": uncovered_specs,
    }


def print_text_report(report: dict, threshold: float) -> None:
    """输出文本格式的覆盖率报告。"""
    print("\n=== Spec-to-Test 覆盖率报告 ===\n")

    # 表头
    print(f"{'业务线':<20} {'Spec 总数':>10} {'已覆盖':>10} {'未覆盖':>10} {'覆盖率':>10}")
    print("─" * 62)

    biz_data = report["by_business"]
    for biz in sorted(biz_data.keys()):
        d = biz_data[biz]
        rate = (d["covered"] / d["total"] * 100) if d["total"] > 0 else 0.0
        print(f"{biz:<20} {d['total']:>10} {d['covered']:>10} {len(d['uncovered']):>10} {rate:>9.1f}%")

    # 汇总
    print("─" * 62)
    rate = report["rate"]
    print(f"{'合计':<20} {report['total']:>10} {report['covered']:>10} {report['uncovered']:>10} {rate:>9.1f}%")

    # 阈值判断
    print()
    if rate >= threshold:
        print(f"[OK] 覆盖率 {rate}% >= 阈值 {threshold}%")
    else:
        print(f"[WARN] 覆盖率 {rate}% < 阈值 {threshold}%")

    # 未覆盖的 spec 详情
    if report["uncovered_specs"]:
        print(f"\n未覆盖的 Spec（共 {len(report['uncovered_specs'])} 个）：")
        for spec in report["uncovered_specs"]:
            print(f"  - [{spec['business']}] {spec['id']} ({spec['file']})")


def print_json_report(report: dict, threshold: float) -> None:
    """输出 JSON 格式的覆盖率报告。"""
    output = {
        "type": "spec_coverage",
        "threshold": threshold,
        **report,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Spec-to-Test 覆盖率检查")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"覆盖率阈值百分比（默认 {DEFAULT_THRESHOLD}）")
    args = parser.parse_args()

    specs = load_registry()
    if specs is None:
        sys.exit(2)

    refs = scan_test_refs()
    report = build_coverage_report(specs, refs)

    if args.json:
        print_json_report(report, args.threshold)
    else:
        print_text_report(report, args.threshold)

    if report["rate"] >= args.threshold:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
