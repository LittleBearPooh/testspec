# -*- coding: utf-8 -*-
"""TestSpec MCP Server — 将 TestSpec 工具链暴露为 MCP 工具。

供 Claude Code / Cursor / 其他 MCP 客户端调用，实现 AI 与工具链的双向交互。

用法:
    python scripts/mcp_server.py                   # 启动 MCP Server（stdio 模式）
    python scripts/mcp_server.py --port 8080        # HTTP SSE 模式

提供的 MCP Tools:
    - validate_specs     : 校验 registry.yaml 完整性
    - check_coverage     : 查询 spec→test 覆盖率
    - check_compliance   : 合规扫描（写操作 DB 校验）
    - generate_skeletons : 生成测试骨架
    - generate_clients   : 生成 API Client 桩
    - import_openapi     : 从 OpenAPI 导入接口定义
    - get_registry       : 读取 registry.yaml 内容（Resource）

退出码:
    0 = 正常退出
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REGISTRY_PATH = PROJECT_ROOT / "specs" / "registry.yaml"


# ---------------------------------------------------------------------------
# 共享脚本执行助手
# ---------------------------------------------------------------------------

def _run_script(script_name: str, extra_args: list[str] | None = None, timeout: int = 60) -> dict:
    """运行工具链脚本并返回结构化结果。"""
    script = SCRIPTS_DIR / script_name
    if not script.exists():
        return {"success": False, "error": f"脚本不存在: {script}", "output": ""}
    cmd = [sys.executable, str(script)] + (extra_args or [])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"命令执行超时 ({timeout}s)", "output": ""}
    return {
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# ---------------------------------------------------------------------------
# MCP Tool 实现
# ---------------------------------------------------------------------------

def tool_validate_specs() -> dict:
    """运行 validate_specs.py 并返回结构化结果。"""
    return _run_script("validate_specs.py")


def tool_check_coverage(threshold: int = 70) -> dict:
    """运行 check_coverage.py 并返回覆盖率数据。"""
    return _run_script("check_coverage.py", ["--threshold", str(threshold)])


def tool_check_compliance() -> dict:
    """运行 check_compliance.py 并返回合规扫描结果。"""
    return _run_script("check_compliance.py")


def tool_generate_skeletons(spec_id: str | None = None, append: bool = False) -> dict:
    """运行 generate_skeletons.py 生成测试骨架。"""
    extra: list[str] = []
    if spec_id:
        extra.extend(["--spec", spec_id])
    if append:
        extra.append("--append")
    return _run_script("generate_skeletons.py", extra or None)


def tool_generate_clients(business: str | None = None) -> dict:
    """运行 generate_clients.py 生成 API Client 桩。"""
    extra: list[str] = []
    if business:
        extra.extend(["--business", business])
    return _run_script("generate_clients.py", extra or None)


def tool_get_registry() -> dict:
    """读取 registry.yaml 内容并返回结构化数据。"""
    if not REGISTRY_PATH.exists():
        return {"success": False, "error": "registry.yaml 不存在"}

    import yaml
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    specs = data.get("specs", [])
    return {
        "success": True,
        "version": data.get("version", "unknown"),
        "spec_count": len(specs),
        "specs": [
            {
                "id": s.get("id"),
                "method": (s.get("api") or {}).get("method"),
                "path": (s.get("api") or {}).get("path"),
                "auth": s.get("auth"),
                "priority": s.get("priority"),
                "enabled": s.get("enabled", True),
                "tags": s.get("tags", []),
            }
            for s in specs
        ],
    }


def tool_import_openapi(file_path: str, gen_specs: bool = False) -> dict:
    """从 OpenAPI 文件导入接口定义。"""
    resolved = Path(file_path).resolve()
    project_root_resolved = PROJECT_ROOT.resolve()
    try:
        resolved.relative_to(project_root_resolved)
    except ValueError:
        return {"success": False, "error": f"文件路径必须在项目根目录内: {file_path}"}

    extra = [str(resolved)]
    if gen_specs:
        extra.append("--gen-specs")
    return _run_script("import_openapi.py", extra)


# ---------------------------------------------------------------------------
# MCP 工具注册表
# ---------------------------------------------------------------------------

TOOLS = {
    "validate_specs": {
        "description": "校验 specs/registry.yaml 的完整性和一致性",
        "handler": tool_validate_specs,
        "parameters": {},
    },
    "check_coverage": {
        "description": "查询 spec→test 覆盖率",
        "handler": tool_check_coverage,
        "parameters": {
            "threshold": {"type": "integer", "description": "覆盖率阈值（默认 70）", "default": 70},
        },
    },
    "check_compliance": {
        "description": "合规扫描：检查写操作用例是否缺少 DB 校验",
        "handler": tool_check_compliance,
        "parameters": {},
    },
    "generate_skeletons": {
        "description": "从 registry.yaml 生成测试骨架代码",
        "handler": tool_generate_skeletons,
        "parameters": {
            "spec_id": {"type": "string", "description": "指定 spec id（可选）"},
            "append": {"type": "boolean", "description": "向已有文件追加缺失函数", "default": False},
        },
    },
    "generate_clients": {
        "description": "从 registry.yaml 生成 API Client 桩代码",
        "handler": tool_generate_clients,
        "parameters": {
            "business": {"type": "string", "description": "指定业务线（可选）"},
        },
    },
    "get_registry": {
        "description": "读取 registry.yaml 内容，返回所有 spec 的结构化摘要",
        "handler": tool_get_registry,
        "parameters": {},
    },
    "import_openapi": {
        "description": "从 OpenAPI/Swagger 文件导入接口定义到 registry.yaml",
        "handler": tool_import_openapi,
        "parameters": {
            "file_path": {"type": "string", "description": "OpenAPI 文件路径"},
            "gen_specs": {"type": "boolean", "description": "同时生成 Markdown spec 文档", "default": False},
        },
    },
}


# ---------------------------------------------------------------------------
# MCP 协议处理（stdio 模式）
# ---------------------------------------------------------------------------

def handle_request(request: dict) -> dict:
    """处理单个 MCP JSON-RPC 请求。"""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "testspec-mcp", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        tool_list = []
        for name, info in TOOLS.items():
            props = {}
            for pname, pinfo in info["parameters"].items():
                props[pname] = {
                    "type": pinfo.get("type", "string"),
                    "description": pinfo.get("description", ""),
                }
            tool_list.append({
                "name": name,
                "description": info["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": props,
                },
            })
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tool_list},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": f"未知工具: {tool_name}"})}],
                    "isError": True,
                },
            }

        handler = TOOLS[tool_name]["handler"]
        try:
            result = handler(**tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                    "isError": not result.get("success", True),
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                    "isError": True,
                },
            }

    if method == "notifications/initialized":
        return None  # 通知无需响应

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio() -> None:
    """以 stdio 模式运行 MCP Server。"""
    print("[TestSpec MCP] Server started (stdio mode)", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request)
        if response is not None:
            print(json.dumps(response), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="TestSpec MCP Server")
    parser.add_argument("--port", type=int, help="HTTP SSE 模式端口（暂不支持，请使用 stdio 模式）")
    args = parser.parse_args()

    if args.port:
        print("[TestSpec MCP] HTTP SSE 模式暂不支持，请使用 stdio 模式。", file=sys.stderr)
        sys.exit(1)
    else:
        run_stdio()


if __name__ == "__main__":
    main()
