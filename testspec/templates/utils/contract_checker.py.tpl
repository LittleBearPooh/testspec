# -*- coding: utf-8 -*-
"""API 契约校验 — 验证响应结构是否符合预期 Schema。

解决的问题:
    - 接口响应字段被悄悄删除或改名，现有测试未覆盖
    - 新增字段导致前端解析异常
    - 响应结构变更未被及时发现

已知限制:
    本校验器为轻量级实现，支持 JSON Schema Draft-07 的核心子集：
    type、required、properties、items、enum、minimum/maximum、minLength/maxLength。
    不支持 anyOf、oneOf、allOf、$ref、additionalProperties、patternProperties。
    如需完整 JSON Schema 校验，请使用 jsonschema 库替代。

用法:
    from utils.contract_checker import validate_response, ContractError

    resp = http_client.get("/api/v1/orders/123")
    validate_response(resp.json(), schema="order-detail")

    # 或直接用 JSON Schema dict:
    validate_response(resp.json(), schema={
        "type": "object",
        "required": ["code", "data"],
        "properties": {
            "code": {"type": "integer"},
            "data": {"type": "object"}
        }
    })

Schema 定义位置:
    schemas/ 目录下的 YAML 文件，文件名即 schema 名称。
    例如 schemas/order-detail.yaml → validate_response(data, "order-detail")
"""

from __future__ import annotations

import json
import re as _re
import threading
from pathlib import Path
from typing import Any

import yaml

from utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
_schema_cache: dict[str, dict] = {}
_schema_lock = threading.Lock()


class ContractError(AssertionError):
    """契约校验失败异常。"""
    pass


def _load_schema(name: str) -> dict:
    """加载并缓存 Schema 文件。"""
    if name in _schema_cache:
        return _schema_cache[name]
    with _schema_lock:
        if name in _schema_cache:  # double-check
            return _schema_cache[name]

        if not _re.fullmatch(r"[\w][\w.\-]*", name):
            raise ValueError(f"无效 schema 名称（仅允许字母/数字/连字符/点）: {name!r}")

        schema_file = _SCHEMAS_DIR / f"{name}.yaml"
        if not schema_file.exists():
            schema_file = _SCHEMAS_DIR / f"{name}.json"
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema 文件不存在: schemas/{name}.yaml 或 .json")

        with schema_file.open(encoding="utf-8") as f:
            if schema_file.suffix == ".yaml":
                schema = yaml.safe_load(f)
            else:
                schema = json.load(f)

        _schema_cache[name] = schema
        return schema


def _check_type(value: Any, expected_type: str, path: str) -> list[str]:
    """校验值的类型是否匹配。

    注意：Python 中 bool 是 int 的子类，isinstance(True, int) 为 True。
    必须在检查 integer/number 之前先处理 boolean，否则 JSON 布尔值会
    错误地通过 {"type": "integer"} 或 {"type": "number"} 的校验。
    """
    errors = []
    # Must check bool BEFORE int, as bool subclasses int in Python
    if expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: 期望类型 boolean，实际 {type(value).__name__}")
    elif expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{path}: 期望类型 integer，实际 {type(value).__name__}")
    elif expected_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{path}: 期望类型 number，实际 {type(value).__name__}")
    else:
        type_map = {
            "string": str,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        py_type = type_map.get(expected_type)
        if py_type and not isinstance(value, py_type):
            errors.append(f"{path}: 期望类型 {expected_type}，实际 {type(value).__name__}")
    return errors


def _validate_recursive(data: Any, schema: dict, path: str = "$") -> list[str]:
    """递归校验数据结构。"""
    errors = []

    # 类型检查
    if "type" in schema:
        errors.extend(_check_type(data, schema["type"], path))
        if errors:
            return errors

    # required 字段检查
    if "required" in schema and isinstance(data, dict):
        for field in schema["required"]:
            if field not in data:
                errors.append(f"{path}: 缺少必填字段 '{field}'")

    # properties 检查
    if "properties" in schema and isinstance(data, dict):
        for field, field_schema in schema["properties"].items():
            if field in data:
                errors.extend(
                    _validate_recursive(data[field], field_schema, f"{path}.{field}")
                )

    # items 检查（数组）
    if "items" in schema and isinstance(data, list):
        for i, item in enumerate(data):
            errors.extend(
                _validate_recursive(item, schema["items"], f"{path}[{i}]")
            )

    # enum 检查
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: 值 {data!r} 不在枚举范围 {schema['enum']}")

    # minimum / maximum
    if isinstance(data, (int, float)):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: 值 {data} < 最小值 {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: 值 {data} > 最大值 {schema['maximum']}")

    # minLength / maxLength
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: 长度 {len(data)} < 最小长度 {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"{path}: 长度 {len(data)} > 最大长度 {schema['maxLength']}")

    return errors


def validate_response(data: Any, schema: str | dict) -> None:
    """校验响应数据是否符合 Schema。

    Args:
        data: 响应数据（通常是 dict）
        schema: Schema 名称（字符串，从 schemas/ 加载）或 Schema dict

    Raises:
        ContractError: 校验失败时抛出，包含所有错误详情
    """
    if isinstance(schema, str):
        schema = _load_schema(schema)

    errors = _validate_recursive(data, schema)

    if errors:
        msg = f"契约校验失败（{len(errors)} 个错误）:\n" + "\n".join(f"  ✗ {e}" for e in errors)
        logger.error(msg)
        raise ContractError(msg)

    logger.debug("契约校验通过")


def list_schemas() -> list[str]:
    """列出所有可用的 Schema 名称。"""
    if not _SCHEMAS_DIR.exists():
        return []
    return sorted(
        f.stem for f in _SCHEMAS_DIR.iterdir()
        if f.suffix in (".yaml", ".json") and not f.name.startswith("_")
    )
