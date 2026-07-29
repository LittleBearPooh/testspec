# -*- coding: utf-8 -*-
"""测试质量度量数据生成工具。

生成 JSON 格式的质量度量数据，可被 Grafana、Allure Dashboard 或自定义仪表盘消费。

用法:
    python scripts/generate_metrics.py                        # 输出到 stdout
    python scripts/generate_metrics.py --output metrics.json  # 输出到文件
    python scripts/generate_metrics.py --pretty               # 美化 JSON

度量维度:
    1. 用例统计：总数/通过/失败/跳过
    2. Spec 覆盖率：基于 registry.yaml
    3. 合规状态：基于 check_compliance.py
    4. 执行时间：基于 JUnit XML
    5. Flaky Test 数量：基于 detect_flaky.py

退出码:
    0 = 成功
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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
REGISTRY_PATH = PROJECT_ROOT / "specs" / "registry.yaml"
TESTCASE_DIR = PROJECT_ROOT / "testcase"
REPORTS_DIR = PROJECT_ROOT / "reports"

SPEC_REF_RE = re.compile(r"spec:\s*(specs/\S+\.md)")


def get_test_counts() -> dict:
    """通过 pytest --collect-only 获取用例统计。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "testcase/", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60
        )
        output = result.stdout.strip()
        # 解析 "N tests collected" 格式
        m = re.search(r"(\d+)\s+test[s]?\s+collected", output)
        total = int(m.group(1)) if m else 0
        return {"total": total, "collected": True}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"total": 0, "collected": False}


def get_spec_coverage() -> dict:
    """计算 spec 覆盖率。"""
    if not REGISTRY_PATH.exists():
        return {"available": False}

    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    specs = data.get("specs", [])
    spec_files = {s["file"] for s in specs if "file" in s}

    # 扫描测试文件中的 spec 引用
    covered = set()
    if TESTCASE_DIR.exists():
        for py_file in TESTCASE_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for match in SPEC_REF_RE.finditer(content):
                    if match.group(1) in spec_files:
                        covered.add(match.group(1))
            except (OSError, UnicodeDecodeError):
                continue

    total = len(spec_files)
    covered_count = len(covered)
    rate = (covered_count / total * 100) if total > 0 else 0.0

    by_business: dict[str, dict] = {}
    for s in specs:
        parts = Path(s.get("file", "")).parts
        biz = parts[1] if len(parts) >= 3 else "unknown"
        if biz not in by_business:
            by_business[biz] = {"total": 0, "covered": 0}
        by_business[biz]["total"] += 1
        if s.get("file") in covered:
            by_business[biz]["covered"] += 1

    for biz in by_business:
        t = by_business[biz]["total"]
        c = by_business[biz]["covered"]
        by_business[biz]["rate"] = round(c / t * 100, 1) if t > 0 else 0.0

    return {
        "available": True,
        "total_specs": total,
        "covered_specs": covered_count,
        "uncovered_specs": total - covered_count,
        "rate": round(rate, 1),
        "by_business": by_business,
    }


def get_compliance_status() -> dict:
    """运行合规检查获取状态。"""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/check_compliance.py"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
        )
        return {
            "passed": result.returncode == 0,
            "output_preview": result.stdout[:200].strip(),
        }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"passed": None, "error": "check_compliance.py 不可用"}


def get_latest_run_stats() -> dict:
    """从最新的 JUnit XML 中获取运行统计。"""
    if not REPORTS_DIR.exists():
        return {"available": False}

    run_dirs = sorted(
        [d for d in REPORTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )

    if not run_dirs:
        return {"available": False}

    latest_dir = run_dirs[0]
    passed = failed = errors = skipped = 0
    durations = []

    for xml_file in latest_dir.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            for tc in tree.getroot().findall(".//testcase"):
                durations.append(_safe_float(tc.get("time")))
                if tc.findall("failure"):
                    failed += 1
                elif tc.findall("error"):
                    errors += 1
                elif tc.findall("skipped"):
                    skipped += 1
                else:
                    passed += 1
        except (ET.ParseError, OSError):
            continue

    total = passed + failed + errors + skipped
    return {
        "available": total > 0,
        "run_id": latest_dir.name,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0.0,
        "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "total_duration": round(sum(durations), 2),
    }


def build_metrics() -> dict:
    """汇总所有度量数据。"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": PROJECT_ROOT.name,
        "test_counts": get_test_counts(),
        "spec_coverage": get_spec_coverage(),
        "compliance": get_compliance_status(),
        "latest_run": get_latest_run_stats(),
    }


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="测试质量度量数据生成")
    parser.add_argument("--output", "-o", type=str, help="输出到文件")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON")
    args = parser.parse_args()

    metrics = build_metrics()

    indent = 2 if args.pretty else None
    json_str = json.dumps(metrics, ensure_ascii=False, indent=indent)

    if args.output:
        output_path = Path(args.output).resolve()
        project_root = Path(__file__).resolve().parent.parent
        if not str(output_path).startswith(str(project_root)):
            print(f"[ERROR] 输出路径必须在项目目录内: {args.output}", file=sys.stderr)
            sys.exit(1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding="utf-8")
        print(f"[OK] 度量数据已写入: {args.output}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
