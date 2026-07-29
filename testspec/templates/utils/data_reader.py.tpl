# -*- coding: utf-8 -*-
"""测试数据读取器。

所有路径相对于项目根目录的 data/ 目录。

用法：
    from utils.data_reader import read_yaml, read_json, read_excel

    cases = read_yaml("yaml/login_cases.yaml")
    cases = read_json("json/order_cases.json")
    cases = read_excel("excel/test_cases.xlsx", sheet="Sheet1")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from utils.logger import get_logger

logger = get_logger(__name__)

# data/ 目录固定位于仓库根目录下；此路径解析在任何工作目录下均稳定。
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _resolve(relative_path: str) -> Path:
    """把 data/ 下的相对路径转换成绝对路径。

    例如：read_yaml("yaml/a.yaml") 实际读取 <项目根>/data/yaml/a.yaml。
    """
    resolved = (_DATA_DIR / relative_path).resolve()
    data_dir_resolved = _DATA_DIR.resolve()
    try:
        resolved.relative_to(data_dir_resolved)
    except ValueError:
        raise PermissionError(f"路径遍历检测: {relative_path!r} 超出 data/ 目录")
    logger.debug("数据文件路径：%s", resolved)
    return resolved


def read_yaml(relative_path: str) -> Any:
    """读取 YAML 文件，返回 list 或 dict。"""
    path = _resolve(relative_path)
    logger.info("读取数据文件：%s", path)
    try:
        # yaml.safe_load 把 YAML 自动转换成 Python 的 dict/list/str/int 等基础类型。
        with path.open(encoding="utf-8") as f:
            result = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("数据文件不存在：%s", path)
        raise
    except yaml.YAMLError as e:
        logger.error("YAML 解析失败：%s — %s", path, e)
        raise
    logger.info("加载完成：%d 条记录", len(result) if isinstance(result, list) else 1)
    return result


def read_json(relative_path: str) -> Any:
    """读取 JSON 文件，返回 list 或 dict。"""
    path = _resolve(relative_path)
    logger.info("读取数据文件：%s", path)
    try:
        # json.load 直接从文件对象读取并解析 JSON。
        with path.open(encoding="utf-8") as f:
            result = json.load(f)
    except FileNotFoundError:
        logger.error("数据文件不存在：%s", path)
        raise
    except json.JSONDecodeError as e:
        logger.error("JSON 解析失败：%s — %s", path, e)
        raise
    logger.info("加载完成：%d 条记录", len(result) if isinstance(result, list) else 1)
    return result


def read_excel(relative_path: str, sheet: str = "Sheet1") -> list[dict[str, Any]]:
    """读取 Excel 文件，第一行为表头，返回 list[dict]。

    依赖 openpyxl，未安装时抛出 ImportError（含安装提示）。
    """
    try:
        import openpyxl
    except ImportError as e:
        raise ImportError("read_excel 需要安装 openpyxl：pip install openpyxl") from e

    path = _resolve(relative_path)
    logger.info("读取数据文件：%s (sheet=%s)", path, sheet)
    try:
        # data_only=True 读取公式单元格的缓存计算值，而非公式字符串本身。
        wb = openpyxl.load_workbook(path, data_only=True)
    except FileNotFoundError:
        logger.error("数据文件不存在：%s", path)
        raise
    try:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    if not rows:
        logger.info("加载完成：0 条记录（空表）")
        return []

    # 第一行作为表头，后续每一行按表头组装成 dict，便于 pytest 参数化使用。
    headers = [str(h) for h in rows[0]]
    result = [dict(zip(headers, row)) for row in rows[1:]]
    logger.info("加载完成：%d 条记录", len(result))
    return result
