# -*- coding: utf-8 -*-
"""Spec 注册表校验工具。

校验 specs/registry.yaml 的完整性和一致性。

用法:
    python scripts/validate_specs.py

检查项:
    1. registry.yaml 文件是否存在且可解析
    2. 每个 spec 是否有 id / file / api / parameters / responses
    3. 引用的 spec 文件是否存在
    4. parameters 是否有 name + type + required
    5. responses 是否有至少一个正常响应
    6. db_effects 中的 operation 是否合法
    7. business_rules 是否有 id + description

退出码:
    0 = 全部通过
    1 = 存在警告（不阻塞 CI）
    2 = 存在错误（阻塞 CI）
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "specs" / "registry.yaml"

VALID_OPERATIONS = {"INSERT", "UPDATE", "DELETE", "UPSERT", "SELECT"}
VALID_PARAM_TYPES = {"string", "integer", "float", "boolean", "array", "object"}
VALID_PARAM_LOCATIONS = {"query", "body", "path", "header", "form", "cookie"}
VALID_AUTH_TYPES = {"bearer", "api_key", "basic", "none", "inherit"}
VALID_BUSINESS_RULE_TYPES = {"idempotency", "precondition", "invariant", "transition", "authorization"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}


class ValidationResult:
    """收集校验过程中的错误和警告。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def print_report(self) -> None:
        if self.errors:
            print(f"\n[ERROR] 发现 {len(self.errors)} 个错误：")
            for e in self.errors:
                print(f"  ✗ {e}")

        if self.warnings:
            print(f"\n[WARN] 发现 {len(self.warnings)} 个警告：")
            for w in self.warnings:
                print(f"  ⚠ {w}")

        if not self.errors and not self.warnings:
            print("[OK] specs/registry.yaml 校验通过。")


def validate_registry(result: ValidationResult) -> dict | None:
    """加载并校验 registry.yaml，返回解析后的 dict。"""
    if not REGISTRY_PATH.exists():
        result.error(f"注册表文件不存在: {REGISTRY_PATH}")
        return None

    try:
        with REGISTRY_PATH.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result.error(f"registry.yaml YAML 解析失败: {e}")
        return None

    if not isinstance(data, dict):
        result.error("registry.yaml 顶层结构应为 dict")
        return None

    if "version" not in data:
        result.warn("registry.yaml 缺少 version 字段")

    if "specs" not in data or not isinstance(data.get("specs"), list):
        result.error("registry.yaml 缺少 specs 列表或格式不正确")
        return None

    return data


def validate_spec(spec: dict, index: int, result: ValidationResult) -> None:
    """校验单个 spec 条目。"""
    prefix = f"specs[{index}]"

    # --- id ---
    spec_id = spec.get("id", f"(index {index}, 无 id)")
    if not spec.get("id"):
        result.error(f"{prefix}: 缺少 id 字段")
    prefix = f"spec '{spec_id}'"

    # --- file ---
    spec_file = spec.get("file")
    if not spec_file:
        result.error(f"{prefix}: 缺少 file 字段")
    else:
        file_path = (PROJECT_ROOT / spec_file).resolve()
        try:
            file_path.relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            result.error(f"{prefix}: spec file 路径超出项目根目录 (路径遍历): {spec_file}")
            return
        if not file_path.exists():
            result.error(f"{prefix}: 引用的文件不存在: {spec_file}")

    # --- api ---
    api = spec.get("api")
    if not api:
        result.error(f"{prefix}: 缺少 api 字段")
    else:
        if "method" not in api:
            result.error(f"{prefix}: api 缺少 method")
        if "path" not in api:
            result.error(f"{prefix}: api 缺少 path")

    # --- auth ---
    auth = spec.get("auth")
    if auth is not None and auth not in VALID_AUTH_TYPES:
        result.warn(f"{prefix}: 未知 auth 类型 '{auth}'（合法值: {VALID_AUTH_TYPES}）")
    elif auth is None:
        result.warn(f"{prefix}: 未定义 auth 字段（建议声明: bearer / api_key / basic / none / inherit）")

    # --- sla_ms ---
    sla_ms = spec.get("sla_ms")
    if sla_ms is not None:
        if not isinstance(sla_ms, (int, float)) or sla_ms <= 0:
            result.error(f"{prefix}: sla_ms 必须是正数")

    # --- parameters ---
    params = spec.get("parameters")
    if params is None:
        result.warn(f"{prefix}: 缺少 parameters 字段（查询接口也需要至少声明路径参数）")
    elif isinstance(params, list):
        for pi, param in enumerate(params):
            p_prefix = f"{prefix}.parameters[{pi}]"
            if "name" not in param:
                result.error(f"{p_prefix}: 缺少 name")
            if "type" not in param:
                result.error(f"{p_prefix}: 缺少 type")
            elif param["type"] not in VALID_PARAM_TYPES:
                result.warn(f"{p_prefix}: 未知类型 '{param['type']}'")
            if "required" not in param:
                result.warn(f"{p_prefix}: 缺少 required 字段（默认 false）")
            # 校验 in 字段
            param_in = param.get("in")
            if param_in is None:
                result.error(f"{p_prefix}: 缺少 in 字段（必须声明参数位置: path/query/body/header）")
            elif param_in not in VALID_PARAM_LOCATIONS:
                result.error(f"{p_prefix}: 未知 in 值 '{param_in}'（合法值: {VALID_PARAM_LOCATIONS}）")
            # 校验 constraints 结构
            constraints = param.get("constraints")
            if constraints is not None:
                if isinstance(constraints, str):
                    result.warn(f"{p_prefix}: constraints 建议使用结构化格式（如 {{min: 1, max: 999}}）而非字符串")
                elif isinstance(constraints, dict):
                    valid_keys = {"min", "max", "minLength", "maxLength", "enum", "pattern", "format"}
                    for key in constraints:
                        if key not in valid_keys:
                            result.warn(f"{p_prefix}: constraints 中有未知键 '{key}'（合法键: {valid_keys}）")

    # --- responses ---
    responses = spec.get("responses")
    if not responses:
        result.error(f"{prefix}: 缺少 responses 字段")
    elif isinstance(responses, dict):
        has_success = False
        for status_code, resp in responses.items():
            code_int = int(status_code) if str(status_code).isdigit() else 0
            if 200 <= code_int < 300:
                has_success = True
        if not has_success:
            result.error(f"{prefix}: responses 中没有成功响应（2xx）")
        if len(responses) < 2:
            result.warn(f"{prefix}: responses 只有一个条目，建议至少定义一个异常响应")

    # --- response_schema ---
    response_schema = spec.get("response_schema")
    if response_schema is not None:
        schema_file_yaml = PROJECT_ROOT / "schemas" / f"{response_schema}.yaml"
        schema_file_json = PROJECT_ROOT / "schemas" / f"{response_schema}.json"
        if not schema_file_yaml.exists() and not schema_file_json.exists():
            result.warn(f"{prefix}: response_schema '{response_schema}' 对应的 schema 文件不存在（schemas/{response_schema}.yaml 或 .json）")

    # --- db_effects ---
    db_effects = spec.get("db_effects")
    if db_effects and isinstance(db_effects, list):
        for di, effect in enumerate(db_effects):
            d_prefix = f"{prefix}.db_effects[{di}]"
            if "table" not in effect:
                result.error(f"{d_prefix}: 缺少 table")
            op = effect.get("operation", "")
            if op not in VALID_OPERATIONS:
                result.error(f"{d_prefix}: 未知 operation '{op}'（合法值: {VALID_OPERATIONS}）")
            if not effect.get("key_fields"):
                result.warn(f"{d_prefix}: 缺少 key_fields（建议声明需要校验的字段列表）")

    # --- business_rules ---
    rules = spec.get("business_rules")
    if rules and isinstance(rules, list):
        for ri, rule in enumerate(rules):
            r_prefix = f"{prefix}.business_rules[{ri}]"
            if "id" not in rule:
                result.error(f"{r_prefix}: 缺少 id")
            if "description" not in rule:
                result.error(f"{r_prefix}: 缺少 description")
            rule_type = rule.get("type")
            if rule_type is not None and rule_type not in VALID_BUSINESS_RULE_TYPES:
                result.warn(f"{r_prefix}: 未知 type '{rule_type}'（合法值: {VALID_BUSINESS_RULE_TYPES}）")

    # --- 路径参数一致性校验 ---
    api_path = (spec.get("api") or {}).get("path", "")
    path_placeholders = set(re.findall(r"\{(\w+)\}", api_path)) if api_path else set()
    declared_path_params = set()
    for p in (spec.get("parameters") or []):
        if p.get("in") == "path":
            declared_path_params.add(p.get("name", ""))

    missing_in_params = path_placeholders - declared_path_params
    if missing_in_params:
        result.error(
            f"{prefix}: api.path 中的路径参数 {missing_in_params} "
            f"未在 parameters 中声明（需要 in: path）"
        )
    extra_path_params = declared_path_params - path_placeholders
    if extra_path_params:
        result.warn(
            f"{prefix}: parameters 中声明了 in: path 的参数 {extra_path_params} "
            f"但 api.path 中没有对应的 {{{{param}}}} 占位符"
        )

    # --- environment ---
    env = spec.get("environment")
    if env is not None and not isinstance(env, str):
        result.error(f"{prefix}: environment 必须是字符串")

    # --- tags ---
    tags = spec.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            result.error(f"{prefix}: tags 必须是列表")
        elif not all(isinstance(t, str) for t in tags):
            result.error(f"{prefix}: tags 列表元素必须是字符串")

    # --- priority ---
    priority = spec.get("priority")
    if priority is not None and priority not in VALID_PRIORITIES:
        result.warn(f"{prefix}: 未知 priority '{priority}'（建议值: {VALID_PRIORITIES}）")

    # --- enabled ---
    enabled = spec.get("enabled")
    if enabled is not None and not isinstance(enabled, bool):
        result.error(f"{prefix}: enabled 必须是布尔值（true/false）")

    # --- dependencies ---
    deps = spec.get("dependencies")
    if deps is not None:
        if not isinstance(deps, list):
            result.error(f"{prefix}: dependencies 必须是列表")

    # --- headers ---
    headers = spec.get("headers")
    if headers is not None and not isinstance(headers, dict):
        result.error(f"{prefix}: headers 必须是字典")


def validate_no_duplicate_ids(data: dict, result: ValidationResult) -> None:
    """检查 spec id 是否有重复。"""
    ids = [s.get("id") for s in data["specs"] if s.get("id")]
    seen = set()
    for spec_id in ids:
        if spec_id in seen:
            result.error(f"重复的 spec id: '{spec_id}'")
        seen.add(spec_id)


def validate_dependencies(data: dict, result: ValidationResult) -> None:
    """检查 dependencies 引用的 spec id 是否存在。"""
    all_ids = {s.get("id") for s in data["specs"] if s.get("id")}
    for spec in data["specs"]:
        spec_id = spec.get("id", "?")
        deps = spec.get("dependencies")
        if deps and isinstance(deps, list):
            for dep_id in deps:
                if dep_id not in all_ids:
                    result.error(
                        f"spec '{spec_id}': dependencies 引用了不存在的 spec id '{dep_id}'"
                    )


def print_summary(data: dict, result: ValidationResult) -> None:
    """打印统计摘要。"""
    specs = data["specs"]
    total_params = sum(len(s.get("parameters") or []) for s in specs)
    total_responses = sum(len(s.get("responses") or {}) for s in specs)
    total_db = sum(len(s.get("db_effects") or []) for s in specs)
    total_rules = sum(len(s.get("business_rules") or []) for s in specs)

    print(f"\n=== 注册表统计 ===")
    print(f"  Spec 数量     : {len(specs)}")
    print(f"  参数总数      : {total_params}")
    print(f"  响应定义总数  : {total_responses}")
    print(f"  DB 影响总数   : {total_db}")
    print(f"  业务规则总数  : {total_rules}")


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    result = ValidationResult()

    data = validate_registry(result)
    if data is None:
        result.print_report()
        sys.exit(2)

    for i, spec in enumerate(data["specs"]):
        validate_spec(spec, i, result)

    validate_no_duplicate_ids(data, result)
    validate_dependencies(data, result)
    print_summary(data, result)
    result.print_report()

    if result.errors:
        sys.exit(2)
    elif result.warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
