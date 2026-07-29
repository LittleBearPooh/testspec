# -*- coding: utf-8 -*-
"""项目级 pytest 配置。

两个核心职责：
1. pytest_configure：若命令行传入了 --alluredir，将 base_url 写入 environment.properties
2. pytest_runtest_makereport：用例失败时，将最后一次 HTTP 响应 attach 到 Allure 报告

同时保留日志记录 hooks，支持按项目写入分类日志。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from utils.logger import get_logger, infer_project, today_log_file
from config.variable_loader import get as var_get


logger = get_logger("pytest")


def _logger_for_nodeid(nodeid: str):
    """按用例 nodeid 选择对应业务日志。"""
    # 例如 nodeid 包含 "hotel" 时，日志会写到 logs/YYYY-MM-DD/hotel.log。
    return get_logger(infer_project(nodeid))


{{#IF_HAS_ALLURE}}
# ——— Allure 集成 ———

def pytest_configure(config: pytest.Config) -> None:
    """若传入了 --alluredir，将 base_url 写入 environment.properties（展示在 Allure 报告环境面板）。"""
    try:
        allure_dir = config.getoption("--alluredir", default=None)
    except ValueError:
        # allure-pytest 未安装时 --alluredir 选项不存在，静默跳过
        return
    if not allure_dir:
        return

    # xdist 的每个 worker 进程都会触发 pytest_configure；只让 controller 进程写，
    # 避免多进程并发 write_text 同一文件（Windows 无原子 append）。
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return

    env_props = Path(allure_dir) / "environment.properties"
    env_props.parent.mkdir(parents=True, exist_ok=True)

    # Allure 会自动读取 environment.properties，并在报告的 Environment 面板展示。
    base_url = var_get("base_url", "N/A")
    safe_url = base_url.replace("\n", "").replace("\r", "").strip()
    env_props.write_text(f"base_url={safe_url}\n", encoding="utf-8")
{{/IF_HAS_ALLURE}}


{{#IF_HAS_HTTP}}
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """用例失败时，将最后一次 HTTP 响应 attach 到 Allure 报告，并将详情写入日志。"""
    outcome = yield
    report = outcome.get_result()

    if report.failed:
        project_logger = _logger_for_nodeid(item.nodeid)

        # 尝试 attach 最后一次 HTTP 响应到 Allure。
        # testcase/conftest.py 的 _track_last_response fixture 会把 http_client._last_response
        # 挂到 item._last_response，用例失败时报告里就能直接看到 URL、状态码、响应体片段。
        last_response = getattr(item, "_last_response", None)
        if last_response is not None:
            try:
                import allure
                body_preview = (getattr(last_response, "text", "") or "")[:3000]
                allure.attach(
                    f"URL: {last_response.url}\n"
                    f"Status: {last_response.status_code}\n\n"
                    f"{body_preview}",
                    name="Last HTTP Response",
                    attachment_type=allure.attachment_type.TEXT,
                )
            except Exception:  # noqa: BLE001
                pass

        if call.excinfo is not None:
            logger.error("测试失败：%s", item.nodeid, exc_info=(call.excinfo.type, call.excinfo.value, call.excinfo.tb))
            project_logger.error("测试失败：%s", item.nodeid, exc_info=(call.excinfo.type, call.excinfo.value, call.excinfo.tb))
        else:
            logger.error("测试失败：%s", item.nodeid)
            project_logger.error("测试失败：%s", item.nodeid)

        # 保留原始错误信息（断言详情、堆栈），在末尾追加日志路径提示。
        log_hint = f"\n\n[响应详情已写入日志] {today_log_file(item.nodeid)}"
        try:
            report.longrepr = str(report.longrepr) + log_hint
        except Exception:  # noqa: BLE001
            pass
{{/IF_HAS_HTTP}}


# ——— 日志记录 hooks ———

def pytest_sessionstart(session: pytest.Session) -> None:
    logger.info("pytest 会话开始：root=%s log_file=%s", session.config.rootpath, today_log_file("pytest"))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    logger.info("pytest 会话结束：exitstatus=%s", exitstatus)


def pytest_runtest_logstart(nodeid: str, location: tuple) -> None:
    logger.info("测试开始：%s", nodeid)
    _logger_for_nodeid(nodeid).info("测试开始：%s", nodeid)


def pytest_runtest_logfinish(nodeid: str, location: tuple) -> None:
    logger.info("测试结束：%s", nodeid)
    _logger_for_nodeid(nodeid).info("测试结束：%s", nodeid)


def pytest_collectreport(report: pytest.CollectReport) -> None:
    """收集阶段失败时记录完整错误，并在终端详情末尾追加日志路径。"""
    if report.failed:
        # 收集阶段失败通常是 import 失败/语法错误/fixture 装载错误，也需要归档到业务日志。
        project_logger = _logger_for_nodeid(report.nodeid)
        logger.error("测试收集失败：%s\n%s", report.nodeid, report.longreprtext)
        project_logger.error("测试收集失败：%s\n%s", report.nodeid, report.longreprtext)
        try:
            report.longrepr = str(report.longrepr) + f"\n\n[详细日志] {today_log_file(report.nodeid)}"
        except Exception:  # noqa: BLE001
            pass
