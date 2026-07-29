# -*- coding: utf-8 -*-
"""变量加载器（单例）。

优先级（低 → 高）：
  variables.yaml（本地默认）  →  variables.{env}.yaml（环境层）  →  variables_override.yaml（执行机/本地敏感值覆盖）

环境变量:
  ENV                     — 指定环境名（如 staging / prod），加载 variables.{env}.yaml
  VARIABLES_OVERRIDE_PATH — 显式指定 override 文件路径（CI 执行机注入场景）

override 文件查找顺序：
  1. 环境变量 VARIABLES_OVERRIDE_PATH 显式指定的路径（CI 执行机注入场景）
  2. 从项目根目录向上逐级查找 variables_override.yaml（本地开发场景）
  3. 都找不到时返回项目根/variables_override.yaml（文件可以不存在，不报错）

在代码中使用：
    from config.variable_loader import get as var_get
    base_url = var_get("base_url", "http://localhost")

    # 点号路径访问嵌套 key
    from config.variable_loader import get_nested as var_get_nested
    db_cfg = var_get_nested("db.default")
    account = var_get_nested("test_accounts.default")

    # 获取当前环境名
    from config.variable_loader import current_env
    print(f"当前环境: {current_env()}")

    from config.variable_loader import _config as project_vars
    timeout = project_vars.get("timeout", 30)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from utils.logger import get_logger, is_sensitive_key

logger = get_logger(__name__)

# 哨兵对象，用于区分"键不存在"与"值为 None"两种情况。
_MISSING = object()


class SecurityError(Exception):
    """配置加载安全异常：路径遍历或符号链接攻击。"""
    pass

_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_FILE = _ROOT / "variables.yaml"


def _find_override_file(start: Path) -> Path:
    """确定 variables_override.yaml 的路径，按优先级：
    1. 环境变量 VARIABLES_OVERRIDE_PATH（CI 场景，直接指定绝对路径）
    2. 从 start 向上逐级查找（本地开发场景）
    3. 都找不到时返回 start/variables_override.yaml（文件可以不存在）
    """
    env_path = os.environ.get("VARIABLES_OVERRIDE_PATH", "").strip()
    if env_path:
        # 安全防护：resolve() 会跟随符号链接，必须在 resolve() 之前检查
        env_path_obj = Path(env_path)
        if env_path_obj.is_symlink():
            raise SecurityError(
                f"VARIABLES_OVERRIDE_PATH 指向符号链接: {env_path}"
            )
        resolved = env_path_obj.resolve()
        return resolved

    current = start.resolve()
    max_depth = 10  # 防止无限遍历
    depth = 0
    while depth < max_depth:
        candidate = current / "variables_override.yaml"
        # 安全防护：跳过符号链接
        if candidate.is_symlink():
            parent = current.parent
            if parent == current:
                break
            current = parent
            depth += 1
            continue
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
        depth += 1
    return start / "variables_override.yaml"


try:
    _OVERRIDE_FILE = _find_override_file(_ROOT)
except SecurityError as e:
    _OVERRIDE_FILE = _ROOT / "variables_override.yaml"
    import warnings
    warnings.warn(f"安全检查失败，使用默认 override 路径: {e}", stacklevel=1)

# 当前环境名（从 ENV 环境变量读取）
_ENV = os.environ.get("ENV", "").strip()
_ENV_FILE = _ROOT / f"variables.{_ENV}.yaml" if _ENV else None

# 对外暴露的全局变量字典。
# 其他模块 import `_config` 或调用 `get()` / `get_nested()` 时，读到的就是合并后的结果。
_config: dict[str, Any] = {}


def current_env() -> str:
    """返回当前环境名（ENV 环境变量值），未设置时返回空字符串。"""
    return _ENV


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并两个字典：override 中的同名 key 优先级更高；
    两边都是 dict 时递归合并，否则直接用 override 值覆盖。

    注意：override 中值为 None 的 key 会覆盖 base 中的同名 key 为 None，
    而非删除该 key。如需"取消"默认值，请在 override 中设为空字符串或空 dict。
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load() -> None:
    """加载并合并变量文件（三层合并），调用方无需关心执行顺序。

    合并顺序（低优先级 → 高优先级）：
    1. variables.yaml       — 本地默认值（提交到 Git）
    2. variables.{env}.yaml — 环境层（如 variables.staging.yaml）
    3. variables_override.yaml — 敏感覆盖（gitignored）
    """
    global _config

    # 1) 先读本地默认变量。本地文件不存在时按空字典处理，避免 import 直接失败。
    local: dict[str, Any] = {}
    if _LOCAL_FILE.exists():
        with _LOCAL_FILE.open(encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}

    # 2) 再读环境层变量（如果 ENV 已设置且文件存在）。
    env_layer: dict[str, Any] = {}
    if _ENV_FILE and _ENV_FILE.exists():
        with _ENV_FILE.open(encoding="utf-8") as f:
            env_layer = yaml.safe_load(f) or {}
        logger.debug("[variable_loader] 加载环境配置: %s (ENV=%s)", _ENV_FILE.name, _ENV)

    # 3) 再读执行机/本地覆盖变量。同名 key 会深度合并，override 优先级更高。
    override: dict[str, Any] = {}
    if _OVERRIDE_FILE.exists():
        with _OVERRIDE_FILE.open(encoding="utf-8") as f:
            override = yaml.safe_load(f) or {}

    # 4) 打印合并差异，便于排查配置问题。
    overridden_keys = [k for k in override if k in local]
    new_keys = [k for k in override if k not in local]
    env_keys = list(env_layer.keys()) if env_layer else []

    if env_keys:
        logger.debug("[variable_loader] 环境层变量 key: %s", env_keys)
    safe_overridden = [k for k in overridden_keys if not is_sensitive_key(k)]
    safe_new = [k for k in new_keys if not is_sensitive_key(k)]
    hidden_count = (len(overridden_keys) - len(safe_overridden)) + (len(new_keys) - len(safe_new))
    if safe_overridden:
        logger.debug("[variable_loader] 线上变量覆盖本地变量: %s", safe_overridden)
    if safe_new:
        logger.debug("[variable_loader] 线上变量新增 key: %s", safe_new)
    if hidden_count:
        logger.debug("[variable_loader] %d 个敏感 key 已隐藏", hidden_count)

    # 5) 三层深度合并：local → env → override。
    _config = _deep_merge(local, env_layer)
    _config = _deep_merge(_config, override)


def get(key: str, default: Any = None) -> Any:
    """获取变量值，未找到时返回 default。"""
    return _config.get(key, default)


def get_nested(path: str, default: Any = None) -> Any:
    """按点号分隔路径访问嵌套变量，路径不存在时返回 default。

    使用 _MISSING 哨兵区分"键不存在"与"值为 None"，
    避免将合法的 None 值误判为缺失。

    示例：
        get_nested("db.default")            -> dict
        get_nested("test_accounts.admin")   -> dict
    """
    keys = path.split(".")
    current: Any = _config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, _MISSING)
        if current is _MISSING:
            return default
    return current


# 模块 import 时自动加载
_load()
