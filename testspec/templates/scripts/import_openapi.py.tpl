# -*- coding: utf-8 -*-
"""从 OpenAPI/Swagger 规格文件导入接口定义到 TestSpec registry.yaml。

支持 OpenAPI 3.0 和 Swagger 2.0 格式。

用法:
    python scripts/import_openapi.py openapi.yaml                          # 导入并追加到 registry.yaml
    python scripts/import_openapi.py openapi.yaml --output registry-new.yaml  # 输出到新文件
    python scripts/import_openapi.py openapi.yaml --gen-specs               # 同时生成 Markdown spec 文档
    python scripts/import_openapi.py openapi.yaml --dry-run                 # 只预览，不写入

转换规则:
    OpenAPI paths[].{method}         → registry spec 条目
    parameters[].in/name/schema      → parameters[].in/name/type/required
    responses[].{code}.description   → responses[].{code}.description
    tags[0]                          → 推断业务线（specs/{tag}/）
    operationId                      → spec id（kebab-case 化）
    security                         → auth 字段

退出码:
    0 = 成功
    1 = 导入警告
    2 = 文件不存在或解析失败
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def to_kebab(s: str) -> str:
    """camelCase / PascalCase / snake_case → kebab-case"""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1-\2", s)
    s = s.replace("_", "-").lower()
    return re.sub(r"-+", "-", s).strip("-")


def resolve_schema_type(schema: dict) -> str:
    """从 OpenAPI schema 对象解析参数类型。"""
    if not schema:
        return "string"
    t = schema.get("type", "string")
    type_map = {
        "string": "string",
        "integer": "integer",
        "number": "float",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }
    return type_map.get(t, "string")


def extract_constraints(schema: dict) -> dict | None:
    """从 OpenAPI schema 提取约束条件。"""
    if not schema:
        return None
    constraints = {}
    for key in ("minimum", "maximum", "minLength", "maxLength", "pattern", "format"):
        if key in schema:
            constraints[key] = schema[key]
    if "enum" in schema:
        constraints["enum"] = schema["enum"]
    return constraints if constraints else None


def infer_auth(spec_data: dict) -> str:
    """从 OpenAPI security 定义推断认证方式。"""
    security = spec_data.get("security", [])
    if not security:
        return "none"

    # 检查第一个 security requirement
    first = security[0] if security else {}
    if not first:
        return "none"

    # 从 components/securitySchemes 查找类型
    schemes = (
        spec_data.get("components", {}).get("securitySchemes", {})
        or spec_data.get("securityDefinitions", {})
    )
    for scheme_name in first:
        scheme = schemes.get(scheme_name, {})
        scheme_type = scheme.get("type", "")
        if scheme_type in ("http", "apiKey"):
            if scheme.get("scheme") == "bearer":
                return "bearer"
            if scheme.get("in") == "header":
                return "api_key"
            return "basic"
        if scheme_type == "oauth2":
            return "bearer"

    return "inherit"


def convert_parameters(oa_params: list[dict]) -> list[dict]:
    """转换 OpenAPI 参数列表为 TestSpec 参数格式。"""
    result = []
    for p in oa_params:
        # 处理 $ref（简化处理：提取名称）
        if "$ref" in p:
            ref_name = p["$ref"].split("/")[-1]
            result.append({
                "name": ref_name,
                "in": "body",
                "type": "object",
                "required": False,
                "description": f"(引用: {p['$ref']})",
            })
            continue

        schema = p.get("schema", {})
        param = {
            "name": p.get("name", "unknown"),
            "in": p.get("in", "query"),
            "type": resolve_schema_type(schema),
            "required": p.get("required", False),
        }
        if p.get("description"):
            param["description"] = p["description"]
        constraints = extract_constraints(schema)
        if constraints:
            param["constraints"] = constraints

        result.append(param)

    return result


def convert_responses(oa_responses: dict) -> dict:
    """转换 OpenAPI 响应定义为 TestSpec 格式。"""
    result = {}
    for status_code, resp in oa_responses.items():
        code_str = str(status_code)
        entry = {}

        if "description" in resp:
            entry["description"] = resp["description"]

        # 提取响应字段（从 schema/content 中）
        content = resp.get("content", {})
        schema = None
        fallback_schema = None
        for media_type, media_obj in content.items():
            s = media_obj.get("schema", {})
            if "application/json" in media_type:
                schema = s
                break
            if fallback_schema is None:
                fallback_schema = s
        if schema is None:
            schema = fallback_schema

        if schema:
            # Swagger 2.0 格式
            if "properties" in schema:
                entry["fields"] = list(schema["properties"].keys())
            # $ref
            elif "$ref" in schema:
                ref_name = schema["$ref"].split("/")[-1]
                entry["description"] = f"(引用 schema: {ref_name})"

        # 对于非 2xx 响应，尝试提取错误码
        code_int = int(code_str) if code_str.isdigit() else 0
        if not (200 <= code_int < 300):
            # 如果有 x-error-codes 扩展
            error_codes = resp.get("x-error-codes", [])
            if error_codes:
                entry["codes"] = error_codes

        result[code_str] = entry

    return result


def import_openapi(file_path: str, gen_specs: bool = False, dry_run: bool = False) -> dict:
    """从 OpenAPI 文件导入并生成 registry 数据。

    Returns:
        dict with keys: specs (list), warnings (list), business_lines (set)
    """
    path = Path(file_path)
    if not path.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        return {"specs": [], "warnings": [f"文件不存在: {file_path}"], "business_lines": set()}

    # 解析文件
    content = path.read_text(encoding="utf-8")
    try:
        if path.suffix in (".yaml", ".yml"):
            spec_data = yaml.safe_load(content)
        else:
            spec_data = json.loads(content)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        print(f"[ERROR] 解析失败: {e}")
        return {"specs": [], "warnings": [f"解析失败: {e}"], "business_lines": set()}

    if not isinstance(spec_data, dict):
        return {"specs": [], "warnings": ["顶层结构不是对象"], "business_lines": set()}

    # 检测 OpenAPI 版本
    openapi_version = spec_data.get("openapi", spec_data.get("swagger", "unknown"))
    print(f"[INFO] 检测到规格版本: {openapi_version}")

    paths = spec_data.get("paths", {})
    if not paths:
        return {"specs": [], "warnings": ["paths 为空"], "business_lines": set()}

    global_auth = infer_auth(spec_data)
    specs = []
    warnings = []
    business_lines = set()

    for path_str, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation:
                continue

            # 生成 spec id
            operation_id = operation.get("operationId", "")
            if operation_id:
                spec_id = to_kebab(operation_id)
            else:
                # 从路径推导：/api/v1/orders → order-list, /api/v1/orders/{id} → order-detail
                clean_path = path_str.strip("/").split("/")
                spec_id_parts = []
                for part in clean_path:
                    if part.startswith("{"):
                        spec_id_parts.append("detail")
                    elif part not in ("api", "v1", "v2", "v3"):
                        spec_id_parts.append(part)
                spec_id = to_kebab("-".join(spec_id_parts) + f"-{method}")

            # 推断业务线（从 tags 或路径）
            tags = operation.get("tags", [])
            business = to_kebab(tags[0]) if tags else "default"
            business_lines.add(business)

            # 转换参数（operation 级别覆盖 path 级别同名参数，符合 OpenAPI 规范）
            path_level = {(p.get("name"), p.get("in")): p
                          for p in path_item.get("parameters", []) if p.get("name")}
            op_level = {(p.get("name"), p.get("in")): p
                        for p in operation.get("parameters", []) if p.get("name")}
            path_level.update(op_level)
            all_params = list(path_level.values())
            parameters = convert_parameters(all_params)

            # 转换响应
            oa_responses = operation.get("responses", {})
            responses = convert_responses(oa_responses)

            # 构建 spec 条目
            spec_entry = {
                "id": spec_id,
                "file": f"specs/{business}/{spec_id}.md",
                "api": {
                    "method": method.upper(),
                    "path": path_str,
                },
                "auth": infer_auth({"security": operation["security"], "components": spec_data.get("components", {})}) if operation.get("security") is not None else global_auth,
                "parameters": parameters,
                "responses": responses,
            }

            # 可选字段
            summary = operation.get("summary", operation.get("description", ""))
            if summary:
                spec_entry["_summary"] = summary  # 用于生成 spec 文档

            specs.append(spec_entry)

    result = {
        "specs": specs,
        "warnings": warnings,
        "business_lines": sorted(business_lines),
    }

    # 生成输出
    if not dry_run:
        _write_output(specs, result, gen_specs, spec_data.get("info", {}).get("title", "Imported API"))

    return result


def _write_output(specs: list, result: dict, gen_specs: bool, project_title: str) -> None:
    """写入 registry.yaml 和可选的 Markdown spec 文档。"""

    # 读取现有 registry（如果存在）
    registry_path = PROJECT_ROOT / "specs" / "registry.yaml"
    existing_specs = []
    if registry_path.exists():
        with registry_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            existing_specs = data.get("specs", [])

    # 合并（跳过已存在的 id）
    existing_ids = {s.get("id") for s in existing_specs}
    new_specs = [s for s in specs if s["id"] not in existing_ids]
    skipped = len(specs) - len(new_specs)

    if not new_specs:
        print(f"[INFO] 所有 {len(specs)} 个接口已在 registry.yaml 中，无新增。")
        return

    # 清理临时字段
    clean_specs = []
    for s in new_specs:
        clean = {k: v for k, v in s.items() if not k.startswith("_")}
        clean_specs.append(clean)

    all_specs = existing_specs + clean_specs

    # 写入 registry.yaml
    output = {
        "version": "2.1",
        "specs": all_specs,
    }

    with registry_path.open("w", encoding="utf-8") as f:
        yaml.dump(output, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"[OK] 导入 {len(new_specs)} 个接口到 specs/registry.yaml（跳过 {skipped} 个已存在）")

    # 可选：生成 Markdown spec 文档
    if gen_specs:
        for spec in new_specs:
            _generate_spec_md(spec, project_title)


def _generate_spec_md(spec: dict, project_title: str) -> None:
    """为单个接口生成 Markdown spec 文档。"""
    spec_file = spec["file"]
    spec_path = PROJECT_ROOT / spec_file
    spec_path.parent.mkdir(parents=True, exist_ok=True)

    if spec_path.exists():
        return  # 不覆盖已存在的 spec 文档

    api = spec.get("api", {})
    method = api.get("method", "GET")
    path = api.get("path", "/")
    summary = spec.get("_summary", f"{method} {path}")

    # 参数表格
    param_rows = []
    for p in spec.get("parameters", []):
        param_rows.append(
            f"| {p.get('name', '?')} | {p.get('in', '?')} | {p.get('type', '?')} | "
            f"{'是' if p.get('required') else '否'} | {p.get('description', '')} |"
        )
    param_table = "\n".join(param_rows) if param_rows else "| (无参数) | | | | |"

    # 响应表格
    resp_rows = []
    for code, resp in spec.get("responses", {}).items():
        resp_rows.append(f"| {code} | {resp.get('description', '')} |")
    resp_table = "\n".join(resp_rows) if resp_rows else "| (无响应定义) | |"

    content = f"""# {project_title} — {summary}

## 基本信息

- **测试函数名**: `test_{spec['id'].replace('-', '_')}`
- **业务线/模块**: {spec['file'].split('/')[1] if '/' in spec['file'] else 'default'}
- **用例类型**: e2e
- **优先级**: P1
- **所在文件**: `testcase/{spec['file'].split('/')[1] if '/' in spec['file'] else 'default'}/test_{spec['id'].replace('-', '_')}_e2e.py`
- **认证方式**: {spec.get('auth', 'none')}

## 用例说明

> {summary}

## 接口定义

- **方法**: `{method}`
- **路径**: `{path}`

## 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
{param_table}

## 响应定义

| 状态码 | 说明 |
|--------|------|
{resp_table}

## 测试步骤

### 步骤 1：发送请求

- **接口**: `{method} {path}`
- **请求参数**:
  ```json
  {{}}
  ```
- **预期响应**: HTTP 200
- **断言**: 关键字段校验

## 数据验证

### 数据库校验

- 根据接口实际操作补充 DB 校验

## 清理策略

- 测试完成后清理创建的数据

## 注意事项

- 异步结果使用带超时的轮询循环，禁止无条件 `time.sleep`
- 禁止硬编码 base_url、token、账号密码
- 所有 SQL 必须参数化
"""

    spec_path.write_text(content, encoding="utf-8")
    print(f"  [SPEC] {spec_file}")


def main() -> None:
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="从 OpenAPI/Swagger 导入接口定义到 TestSpec registry.yaml"
    )
    parser.add_argument("file", type=str, help="OpenAPI/Swagger 文件路径（YAML 或 JSON）")
    parser.add_argument("--gen-specs", action="store_true", help="同时生成 Markdown spec 文档")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入文件")
    parser.add_argument("--output", type=str, help="输出到指定文件（而非追加到 registry.yaml）")
    args = parser.parse_args()

    result = import_openapi(args.file, args.gen_specs, args.dry_run)

    if args.dry_run and result["specs"]:
        print("\n--- 预览 registry.yaml 内容 ---")
        output = {"version": "2.1", "specs": [
            {k: v for k, v in s.items() if not k.startswith("_")}
            for s in result["specs"]
        ]}
        print(yaml.dump(output, default_flow_style=False, allow_unicode=True, sort_keys=False))

    if result["warnings"]:
        print(f"\n[WARN] {len(result['warnings'])} 个警告：")
        for w in result["warnings"]:
            print(f"  ⚠ {w}")

    print(f"\n导入完成: {len(result['specs'])} 个接口, {len(result['business_lines'])} 个业务线")
    print(f"  业务线: {', '.join(sorted(result['business_lines']))}")
    print(f"\n下一步:")
    print(f"  1. python scripts/validate_specs.py      # 校验导入结果")
    print(f"  2. python scripts/generate_skeletons.py  # 生成测试骨架")


if __name__ == "__main__":
    main()
