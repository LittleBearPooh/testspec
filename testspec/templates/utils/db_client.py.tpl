# -*- coding: utf-8 -*-
"""数据库客户端（DBUtils 连接池）。

支持以下数据库驱动（由 init.py 在生成时按选择保留对应块）：
  - SQL Server（pymssql）
  - MySQL（pymysql）
  - PostgreSQL（psycopg2）
  - SQLite（内置，无需连接池）

用法：
    from utils.db_client import get_db

    db = get_db("default")            # 获取默认数据库连接
    rows = db.query("SELECT * FROM orders WHERE id = %s", (order_id,))
    row  = db.query_one("SELECT * FROM orders WHERE id = %s", (order_id,))
    db.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))

    # SQLite 使用 ? 占位符
    db.query("SELECT * FROM orders WHERE id = ?", (order_id,))

数据库配置来自 variables.yaml：
    db:
      default: { host, port, user, password, name }
      secondary: { host, port, user, password, name }
"""

from __future__ import annotations

import threading
from typing import Any

from config.variable_loader import get_nested as var_get_nested
from utils.logger import get_logger, safe_copy

logger = get_logger(__name__)

# ===========================================================================
{{#IF_DB_SQLSERVER}}
# SQL Server 驱动（pymssql）
# 安装：pip install pymssql dbutils
# SQL 占位符：%s
# ===========================================================================
import pymssql
from dbutils.pooled_db import PooledDB


def _build_pool_sqlserver(db_name: str, cfg: dict) -> "PooledDB":
    host     = cfg["host"]
    port     = int(cfg.get("port", 1433))
    user     = cfg["user"]
    password = cfg["password"]
    name     = cfg["name"]
    logger.info("初始化 SQL Server 连接池：db=%s host=%s name=%s", db_name, host, name)
    return PooledDB(
        creator=pymssql,
        mincached=1,
        maxcached=5,
        maxconnections=20,
        blocking=True,
        server=host,
        port=port,
        user=user,
        password=password,
        database=name,
        tds_version="7.4",
        as_dict=True,
    )
{{/IF_DB_SQLSERVER}}

# ===========================================================================
{{#IF_DB_MYSQL}}
# MySQL 驱动（pymysql）
# 安装：pip install pymysql dbutils
# SQL 占位符：%s
# ===========================================================================
import pymysql
from dbutils.pooled_db import PooledDB


def _build_pool_mysql(db_name: str, cfg: dict) -> "PooledDB":
    host     = cfg["host"]
    port     = int(cfg.get("port", 3306))
    user     = cfg["user"]
    password = cfg["password"]
    name     = cfg["name"]
    logger.info("初始化 MySQL 连接池：db=%s host=%s name=%s", db_name, host, name)
    return PooledDB(
        creator=pymysql,
        mincached=1,
        maxcached=5,
        maxconnections=20,
        blocking=True,
        host=host,
        port=port,
        user=user,
        password=password,
        database=name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
{{/IF_DB_MYSQL}}

# ===========================================================================
{{#IF_DB_POSTGRESQL}}
# PostgreSQL 驱动（psycopg2）
# 安装：pip install psycopg2-binary dbutils
# SQL 占位符：%s
# 使用 RealDictCursor 让 query() 返回 list[dict] 而非 list[tuple]
# ===========================================================================
import psycopg2
import psycopg2.extras
from dbutils.pooled_db import PooledDB


def _build_pool_postgresql(db_name: str, cfg: dict) -> "PooledDB":
    host     = cfg["host"]
    port     = int(cfg.get("port", 5432))
    user     = cfg["user"]
    password = cfg["password"]
    name     = cfg["name"]
    logger.info("初始化 PostgreSQL 连接池：db=%s host=%s name=%s", db_name, host, name)
    return PooledDB(
        creator=psycopg2,
        mincached=1,
        maxcached=5,
        maxconnections=20,
        blocking=True,
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=name,
        connect_timeout=10,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
{{/IF_DB_POSTGRESQL}}

# ===========================================================================
{{#IF_DB_SQLITE}}
# SQLite 驱动（内置，无需安装额外包）
# SQL 占位符：?（注意：与其他驱动不同）
# SQLite 单文件数据库，无需连接池；每次查询都创建新连接即可。
# ===========================================================================
import sqlite3


def _build_sqlite_conn(cfg: dict) -> sqlite3.Connection:
    """创建 SQLite 连接，row_factory=sqlite3.Row 使 fetchall() 返回类 dict 对象。"""
    db_path = cfg.get("name", cfg.get("path", ":memory:"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
{{/IF_DB_SQLITE}}


{{#IF_NOT_DB_SQLITE}}
# ===========================================================================
# 连接池（非 SQLite）管理
# SQLite 不使用连接池，此节仅在非 SQLite 模式下生成。
# ===========================================================================

_pools: dict[str, Any] = {}
_pools_lock = threading.Lock()


def _build_pool(db_name: str) -> Any:
    """根据 variables.yaml 中 db.<db_name> 配置初始化连接池。"""
    cfg = var_get_nested(f"db.{db_name}")
    if not isinstance(cfg, dict):
        raise ValueError(
            f"数据库配置不存在：db.{db_name}，请在 variables.yaml 的 db 节点下添加"
        )

    {{#IF_DB_SQLSERVER}}
    return _build_pool_sqlserver(db_name, cfg)
    {{/IF_DB_SQLSERVER}}

    {{#IF_DB_MYSQL}}
    return _build_pool_mysql(db_name, cfg)
    {{/IF_DB_MYSQL}}

    {{#IF_DB_POSTGRESQL}}
    return _build_pool_postgresql(db_name, cfg)
    {{/IF_DB_POSTGRESQL}}


def _get_pool(db_name: str) -> Any:
    """线程安全的懒初始化连接池（双重检查锁定模式）。"""
    if db_name not in _pools:
        with _pools_lock:
            if db_name not in _pools:
                _pools[db_name] = _build_pool(db_name)
    return _pools[db_name]
{{/IF_NOT_DB_SQLITE}}


# ===========================================================================
# DbClient：对外暴露的查询/执行接口
# ===========================================================================

class DbClient:
    """针对单个数据库的查询/执行封装。通过 get_db() 获取实例。"""

    def __init__(self, db_name: str) -> None:
        self._db_name = db_name

    {{#IF_NOT_DB_SQLITE}}
    # ——— 非 SQLite：使用连接池 ———

    def _conn(self):
        """从连接池取出一个连接（需在 with 块中使用）。"""
        return _get_pool(self._db_name).connection()

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """执行 SELECT，返回所有行（list of dict）。

        SQL Server / MySQL / PostgreSQL 占位符用 %s；
        SQLite 占位符用 ?（见 {{#IF_DB_SQLITE}} 块）。
        """
        logger.debug("query db=%s sql=%s params=%s", self._db_name, sql, safe_copy(params))
        with self._conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                # pymssql as_dict=True 和 psycopg2 RealDictCursor 已返回 dict；
                # pymysql DictCursor 也返回 dict；统一转换以防万一。
                return [dict(row) for row in rows]
            finally:
                cursor.close()

    def query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """执行 SELECT，返回第一行（dict）；无结果时返回 None。"""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """执行 INSERT / UPDATE / DELETE，返回受影响行数。"""
        logger.debug("execute db=%s sql=%s params=%s", self._db_name, sql, safe_copy(params))
        with self._conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                rowcount = cursor.rowcount
                conn.commit()
                return rowcount
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    {{/IF_NOT_DB_SQLITE}}

    {{#IF_DB_SQLITE}}
    # ——— SQLite 专用：直接创建连接，不使用连接池 ———

    def _sqlite_conn(self) -> sqlite3.Connection:
        cfg = var_get_nested(f"db.{self._db_name}")
        if not isinstance(cfg, dict):
            raise ValueError(f"数据库配置不存在：db.{self._db_name}")
        return _build_sqlite_conn(cfg)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:  # type: ignore[override]
        """SQLite SELECT，返回 list of dict（SQLite 占位符为 ?）。"""
        logger.debug("query db=%s sql=%s params=%s", self._db_name, sql, safe_copy(params))
        conn = self._sqlite_conn()
        try:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:  # type: ignore[override]
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:  # type: ignore[override]
        """SQLite INSERT / UPDATE / DELETE（占位符为 ?）。"""
        logger.debug("execute db=%s sql=%s params=%s", self._db_name, sql, safe_copy(params))
        conn = self._sqlite_conn()
        try:
            cursor = conn.execute(sql, params)
            rowcount = cursor.rowcount
            conn.commit()
            return rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    {{/IF_DB_SQLITE}}


def get_db(db_name: str = "default") -> DbClient:
    """获取指定数据库的客户端实例。

    Args:
        db_name: variables.yaml 中 db 节点下的 key，默认 "default"。
                 示例值："default"、"secondary"。
    """
    return DbClient(db_name)
