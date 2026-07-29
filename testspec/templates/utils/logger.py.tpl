# -*- coding: utf-8 -*-
"""项目统一日志工厂。

日志策略：
- 默认写入仓库根目录 logs/YYYY-MM-DD/<项目名>.log。
- 不向控制台输出，避免报错信息直接展示在终端。
- HTTP Header/Body 中的敏感字段会脱敏后再写日志。

渲染占位符说明：
  {{PROJECT_NAME_SNAKE}}     — 项目名（snake_case），用于日志文件名前缀推断
  {{BUSINESS_LINES_LIST}}    — Python set 字面量，列出所有业务线目录名，
                               例如：{"hotel", "flight", "auth"}
                               init.py 渲染时替换此占位符。
"""

from __future__ import annotations

import copy
import logging
import os
import threading
import traceback
from datetime import date
from pathlib import Path
from typing import Any

_LOGGER_NAME = "{{PROJECT_NAME_SNAKE}}_project"
_CONFIGURED_PROJECTS: set[str] = set()
_CONFIGURE_LOCK = threading.Lock()

# 已知业务线/项目目录名集合，用于从 nodeid/模块名推断日志归属。
# 渲染时由 init.py 将 {{BUSINESS_LINES_LIST}} 替换为实际 set 字面量，
# 例如：{"hotel", "flight", "auth", "MyService"}
_KNOWN_PROJECTS: set[str] = {{BUSINESS_LINES_LIST}}

SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "refresh_token",
    "id_token",
    "password",
    "licensekey",
    "license_key",
    "clientsecret",
    "client_secret",
    "token",
}


def _repo_root() -> Path:
    """返回仓库根目录路径。"""
    return Path(__file__).resolve().parent.parent


def infer_project(value: str | None = None) -> str:
    """根据模块名、nodeid 或路径推断项目名。"""
    if not value:
        return "common"

    # pytest nodeid 可能长这样：testcase/hotel/...::TestX::test_y
    # Python 模块名可能长这样：services.hotel.hotel_api
    # 统一把斜杠与点号拆成片段，再查是否包含已知项目名。
    normalized = str(value).replace("\\", "/")
    parts = [part for chunk in normalized.split("/") for part in chunk.split(".") if part]
    for part in parts:
        if part in _KNOWN_PROJECTS:
            return part

    first = parts[0] if parts else "common"
    if first in {"pytest", "conftest"}:
        return "pytest"
    return "common"


def today_log_file(project: str | None = None) -> Path:
    """返回当天指定项目的日志文件路径。

    xdist 并行时每个 worker 写独立文件（ProjectName_gw0.log），避免多进程同时
    append 同一文件在 Windows 上导致日志行交叉乱序。
    """
    project_name = infer_project(project)
    log_dir = _repo_root() / "logs" / date.today().isoformat()
    log_dir.mkdir(parents=True, exist_ok=True)
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "")
    suffix = f"_{worker_id}" if worker_id else ""
    return log_dir / f"{project_name}{suffix}.log"


def is_sensitive_key(key: str) -> bool:
    """判断日志字段名是否属于敏感字段。"""
    normalized = key.replace("-", "_").lower()
    return normalized in SENSITIVE_KEYS or any(part in normalized for part in ("password", "secret"))


def sanitize(value: Any) -> Any:
    """递归脱敏日志内容。"""
    # dict/list/tuple 都递归处理，确保嵌套 header/body 中的 token、password 也不会明文写日志。
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                sanitized[key] = "***"
            else:
                sanitized[key] = sanitize(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize(item) for item in value)

    return value


def configure_logging(project: str | None = None) -> Path:
    """初始化指定项目日志，只写文件，不输出到控制台。"""
    project_name = infer_project(project)
    log_file = today_log_file(project_name)

    # 同一个项目只初始化一次 handler，避免重复 import 后一条日志写多遍。
    # 加锁保证多线程（pytest-xdist worker 内的多线程 fixture）下检查与 addHandler 原子执行。
    if project_name in _CONFIGURED_PROJECTS:
        return log_file

    with _CONFIGURE_LOCK:
        # 双重检查：拿到锁后再确认一次，避免多个线程都通过了锁外的首次检查后重复注册。
        if project_name in _CONFIGURED_PROJECTS:
            return log_file

        project_logger = logging.getLogger(f"{_LOGGER_NAME}.{project_name}")
        project_logger.setLevel(logging.DEBUG)
        project_logger.propagate = False

        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        project_logger.addHandler(file_handler)

        _CONFIGURED_PROJECTS.add(project_name)
        project_logger.info("日志初始化完成，文件路径：%s", log_file)
        return log_file


def get_logger(name: str | None = None) -> logging.Logger:
    """获取项目 logger。

    所有 logger 均嵌套在项目 logger 之下，确保继承文件 handler。

    用法：
        from utils.logger import get_logger
        logger = get_logger(__name__)
    """
    project_name = infer_project(name)
    configure_logging(project_name)
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{project_name}.{name}")
    return logging.getLogger(f"{_LOGGER_NAME}.{project_name}")


def log_exception(logger: logging.Logger, message: str, exc: BaseException | None = None) -> None:
    """记录异常完整堆栈。"""
    if exc is None:
        logger.error("%s\n%s", message, traceback.format_exc())
    else:
        logger.error("%s: %s\n%s", message, exc, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


def safe_copy(value: Any) -> Any:
    """复制并脱敏对象，避免修改调用方原始对象。"""
    try:
        return sanitize(copy.deepcopy(value))
    except Exception:  # noqa: BLE001
        return sanitize(value)


# 模块被 import 时即初始化，保证普通脚本/pytest 都有日志文件。
configure_logging()
