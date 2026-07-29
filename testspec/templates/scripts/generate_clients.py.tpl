# -*- coding: utf-8 -*-
"""从 registry.yaml 自动生成 API Client 桩代码。

不依赖 AI，纯代码生成。生成的代码可直接使用或按需修改。

用法:
    python scripts/generate_clients.py                       # 生成所有 client
    python scripts/generate_clients.py --business order      # 只生成指定业务线
    python scripts/generate_clients.py --dry-run             # 只预览

生成规则:
    1. 读取 registry.yaml，按业务线（tags / 路径推断）分组
    2. 每个业务线生成一个 Client 类
    3. 每个接口生成一个方法（含参数类型注解和 docstring）

退出码:
    0 = 成功
    2 = registry.yaml 不存在
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "specs" / "registry.yaml"


def load_registry() -> list[dict] | None:
    if not REGISTRY_PATH.exists():
        print(f"[ERROR] 注册表不存在: {REGISTRY_PATH}")
        return None
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return (data or {}).get("specs", [])


def to_pascal(s: str) -> str:
    return "".join(w.capitalize() for w in s.split("-"))


def to_snake(s: str) -> str:
    return s.replace("-", "_")


def infer_business(spec: dict) -> str:
    """从 spec 推断业务线。"""
    spec_file = spec.get("file", "")
    parts = Path(spec_file).parts
    if len(parts) >= 3:
        return parts[1]
    # 回退：从 tags 推断
    tags = spec.get("tags", [])
    if tags:
        return tags[0]
    return "default"


def python_type(oa_type: str) -> str:
    """OpenAPI 类型 → Python 类型注解。"""
    mapping = {
        "string": "str",
        "integer": "int",
        "float": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return mapping.get(oa_type, "str")


def generate_method(spec: dict) -> str:
    """为单个 spec 生成 client 方法。"""
    spec_id = spec["id"]
    api = spec.get("api", {})
    method = api.get("method", "GET").lower()
    path = api.get("path", "/")
    auth = spec.get("auth", "none")
    params = spec.get("parameters") or []

    method_name = to_snake(spec_id)

    # 构建参数签名
    sig_params = []
    body_params = []
    path_params = []
    query_params = []

    for p in params:
        name = p.get("name", "param")
        ptype = python_type(p.get("type", "string"))
        required = p.get("required", False)
        p_in = p.get("in", "body")

        if p_in == "path":
            path_params.append(name)
            sig_params.append(f"{name}: {ptype}")
        elif p_in in ("query", "form"):
            query_params.append(name)
            if required:
                sig_params.append(f"{name}: {ptype}")
            else:
                sig_params.append(f"{name}: {ptype} | None = None")
        else:  # body
            body_params.append(name)
            if required:
                sig_params.append(f"{name}: {ptype}")
            else:
                sig_params.append(f"{name}: {ptype} | None = None")

    # self 始终第一个
    sig = ", ".join(["self"] + sig_params)

    # 构建请求体
    if body_params:
        body_lines = ", ".join(f'"{p}": {p}' for p in body_params)
        json_arg = f", json={{{body_lines}}}"
    else:
        json_arg = ""

    # 构建查询参数
    if query_params:
        required_q = [p for p in query_params
                      if p in {pp.get("name") for pp in params if pp.get("required")}]
        optional_q = [p for p in query_params if p not in required_q]
        all_q = required_q + optional_q
        q_items = ", ".join(f'"{p}": {p}' for p in all_q)
        params_arg = f", params={{k: v for k, v in {{{q_items}}}.items() if v is not None}}"
    else:
        params_arg = ""

    # 构建路径（替换路径参数）
    url_expr = f'"{path}"'
    if path_params:
        # 生成 f-string：f"/orders/{order_id}" — 直接由 Python f-string 插值
        url_expr = f'f"{path}"'

    # 期望状态码
    expected_status = "200"
    for code in (spec.get("responses") or {}):
        if str(code).startswith("2"):
            expected_status = str(code)
            break

    # Docstring
    summary = ""
    for code, resp in (spec.get("responses") or {}).items():
        if str(code).startswith("2"):
            summary = resp.get("description", "")
            break

    return f'''    def {method_name}({sig}) -> dict:
        """{summary or f'{method.upper()} {path}'}

        spec: {spec.get('file', '')}
        """
        resp = self._http.request(
            "{method.upper()}", {url_expr}{json_arg}{params_arg},
            assert_status={expected_status},
        )
        return resp.json()
'''


def generate_client_class(business: str, specs: list[dict]) -> str:
    """为业务线生成完整的 Client 类。"""
    class_name = f"{to_pascal(business)}Client"

    methods = []
    for spec in specs:
        methods.append(generate_method(spec))

    methods_str = "\n".join(methods)

    return f'''"""{business} 业务 API Client。

⚠️ 本文件由 generate_clients.py 自动生成。
请根据实际需要修改方法签名和实现。
"""

from __future__ import annotations

from utils.http_client import HttpClient


class {class_name}:
    """{business} 业务线 API 封装。"""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

{methods_str}
'''


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="从 registry.yaml 生成 API Client 桩代码")
    parser.add_argument("--business", type=str, help="只生成指定业务线的 client")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入文件")
    args = parser.parse_args()

    specs = load_registry()
    if specs is None:
        sys.exit(2)

    # 按业务线分组
    groups: dict[str, list[dict]] = {}
    for spec in specs:
        biz = infer_business(spec)
        groups.setdefault(biz, []).append(spec)

    if args.business:
        if args.business not in groups:
            print(f"[ERROR] 未找到业务线: {args.business}")
            sys.exit(2)
        groups = {args.business: groups[args.business]}

    generated = 0
    for business, biz_specs in groups.items():
        class_name = f"{to_pascal(business)}Client"
        import re
        safe_name = re.sub(r"[^\w]", "_", to_snake(business))
        filename = f"{safe_name}_client.py"
        out_dir = PROJECT_ROOT / "client"
        out_path = out_dir / filename
        if not out_path.resolve().is_relative_to(out_dir.resolve()):
            raise ValueError(f"生成路径超出 client/ 目录: {out_path}")

        if out_path.exists() and not args.dry_run:
            print(f"  [SKIP] {out_path}（文件已存在）")
            continue

        content = generate_client_class(business, biz_specs)

        if args.dry_run:
            print(f"\n--- {out_path} ---")
            print(content)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            print(f"  [OK] {out_path}（{len(biz_specs)} 个方法）")

        generated += 1

    print(f"\n生成 {generated} 个 Client 文件。")


if __name__ == "__main__":
    main()
