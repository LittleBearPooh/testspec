# -*- coding: utf-8 -*-
"""Flaky Test 检测工具。

从最近 N 次 CI 运行的 JUnit XML 结果中识别不稳定测试。

用法:
    python scripts/detect_flaky.py                       # 扫描 reports/ 下所有结果
    python scripts/detect_flaky.py --runs 50             # 分析最近 50 次运行
    python scripts/detect_flaky.py --threshold 95        # 通过率低于 95% 视为 flaky
    python scripts/detect_flaky.py --json                # JSON 输出

工作方式:
    1. 扫描 reports/ 目录下所有 JUnit XML 文件
    2. 解析每个测试函数的通过/失败记录
    3. 计算通过率，低于阈值的标记为 Flaky
    4. 输出 Flaky Test 清单

退出码:
    0 = 无 Flaky Test 或分析完成
    1 = 发现 Flaky Test
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换浮点数，处理空值和无效格式。

    Args:
        value: 待转换的值（字符串、数字或 None）。
        default: 转换失败时的默认值。

    Returns:
        转换后的浮点数。
    """
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_THRESHOLD = 95.0
DEFAULT_RUNS = 30


def find_xml_files(max_runs: int) -> list[Path]:
    """从 reports/ 目录找到最近 N 次运行的 JUnit XML 文件。

    reports/ 目录结构：
        reports/
        ├── 2026-07-07_103015/
        │   ├── 1_Contract_Smoke.xml
        │   └── 2_Order_E2E.xml
        └── 2026-07-07_143022/
            └── ...
    """
    if not REPORTS_DIR.exists():
        return []

    # 按目录名排序（目录名含时间戳，自然排序即时间序）
    run_dirs = sorted(
        [d for d in REPORTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )[:max_runs]

    xml_files = []
    for run_dir in run_dirs:
        for xml_file in sorted(run_dir.glob("*.xml")):
            xml_files.append(xml_file)

    return xml_files


def parse_junit_xml(xml_path: Path) -> list[dict]:
    """解析单个 JUnit XML 文件，提取测试结果。"""
    results = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except (ET.ParseError, OSError):
        return results

    # 处理 <testsuite> 和 <testsuites> 两种根节点
    suites = root.findall(".//testcase")

    for tc in suites:
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        test_id = f"{classname}::{name}" if classname else name

        # 判断是否失败
        failures = tc.findall("failure")
        errors = tc.findall("error")
        skipped = tc.findall("skipped")

        status = "passed"
        if failures:
            status = "failed"
        elif errors:
            status = "error"
        elif skipped:
            status = "skipped"

        results.append({
            "test_id": test_id,
            "status": status,
            "duration": _safe_float(tc.get("time")),
        })

    return results


def analyze_flaky(xml_files: list[Path], threshold: float) -> dict:
    """分析 Flaky Test。"""
    # test_id → {"passed": N, "failed": N, "total": N, "durations": [...]}
    stats: dict[str, dict] = defaultdict(lambda: {
        "passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0, "durations": []
    })

    for xml_file in xml_files:
        results = parse_junit_xml(xml_file)
        for r in results:
            tid = r["test_id"]
            stats[tid]["total"] += 1
            stats[tid][r["status"]] += 1
            stats[tid]["durations"].append(r["duration"])

    flaky_tests = []
    stable_tests = []

    for test_id, s in stats.items():
        if s["total"] < 2:
            continue  # 只运行过一次的无法判断

        pass_rate = (s["passed"] / s["total"]) * 100
        avg_duration = sum(s["durations"]) / len(s["durations"])

        entry = {
            "test_id": test_id,
            "total_runs": s["total"],
            "passed": s["passed"],
            "failed": s["failed"],
            "pass_rate": round(pass_rate, 1),
            "avg_duration": round(avg_duration, 2),
        }

        # Flaky 的定义：既有通过也有失败（排除始终失败的情况）
        if s["passed"] > 0 and s["failed"] > 0 and pass_rate < threshold:
            flaky_tests.append(entry)
        else:
            stable_tests.append(entry)

    # 按通过率升序排列（最不稳定的排前面）
    flaky_tests.sort(key=lambda x: x["pass_rate"])

    return {
        "flaky": flaky_tests,
        "stable": stable_tests,
        "total_tests": len(stats),
        "total_runs": len(xml_files),
    }


def print_text_report(report: dict, threshold: float) -> None:
    """输出文本报告。"""
    print(f"\n=== Flaky Test 报告 ===")
    print(f"分析范围: 最近 {report['total_runs']} 次运行")
    print(f"测试总数: {report['total_tests']}")
    print(f"Flaky 阈值: 通过率 < {threshold}%\n")

    flaky = report["flaky"]
    if not flaky:
        print("[OK] 未发现 Flaky Test。")
        return

    print(f"[WARN] 发现 {len(flaky)} 个 Flaky Test:\n")

    print(f"{'测试 ID':<65} {'运行次数':>8} {'通过率':>8} {'平均耗时':>10}")
    print("─" * 95)

    for t in flaky:
        print(
            f"{t['test_id']:<65} "
            f"{t['total_runs']:>8} "
            f"{t['pass_rate']:>7.1f}% "
            f"{t['avg_duration']:>9.2f}s"
        )

    print(f"\n建议操作:")
    print("  1. 对 Flaky Test 添加 @pytest.mark.flaky(reruns=3) 临时缓解")
    print("  2. 分析失败模式：是数据冲突、时序问题还是环境不稳定")
    print("  3. 修复根因后移除 flaky 标记")


def print_json_report(report: dict, threshold: float) -> None:
    output = {
        "type": "flaky_detection",
        "threshold": threshold,
        **report,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Flaky Test 检测")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="分析最近 N 次运行")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="通过率阈值")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    xml_files = find_xml_files(args.runs)
    if not xml_files:
        print("[WARN] reports/ 目录下未找到 JUnit XML 文件。")
        print("       请先运行测试并生成 XML 报告：")
        print("       pytest testcase/ --junit-xml=reports/<timestamp>/results.xml")
        sys.exit(0)

    report = analyze_flaky(xml_files, args.threshold)

    if args.json:
        print_json_report(report, args.threshold)
    else:
        print_text_report(report, args.threshold)

    if report["flaky"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
