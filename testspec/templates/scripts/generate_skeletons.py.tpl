# -*- coding: utf-8 -*-
"""从 registry.yaml 自动生成测试文件骨架。

不依赖 AI，纯代码生成。生成的代码带 TODO 注释，由人工或 AI 补全细节。

用法:
    python scripts/generate_skeletons.py                         # 生成所有未存在的测试文件
    python scripts/generate_skeletons.py --spec order-create      # 只生成指定 spec
    python scripts/generate_skeletons.py --dry-run                # 只预览，不写入文件

生成规则:
    1. 读取 registry.yaml 中每个 spec 的 parameters / responses / db_effects
    2. 根据 responses 中的状态码生成正常/异常路径测试函数
    3. 根据 db_effects 生成 DB 校验 TODO
    4. 根据 business_rules 生成业务规则 TODO
    5. 如果测试文件已存在，跳过（不覆盖）

退出码:
    0 = 成功
    1 = 部分生成失败
    2 = registry.yaml 不存在
"""

from __future__ import annotations

import argparse
import io
import re
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
    """kebab-case → PascalCase: order-create → OrderCreate"""
    return "".join(w.capitalize() for w in s.split("-"))


def _to_safe_identifier(s: str) -> str:
    """将任意字符串转换为合法的 Python 标识符片段。"""
    s = re.sub(r'[.\-\s/]+', '_', s)
    s = re.sub(r'[^\w]', '', s)
    if s and s[0].isdigit():
        s = '_' + s
    return s or '_unknown'


def to_test_filename(spec_id: str, business: str) -> str:
    """spec id → 测试文件名: order-create → test_order_creation_e2e.py"""
    snake = spec_id.replace("-", "_")
    return f"test_{snake}_e2e.py"


def infer_business(spec_file: str) -> str:
    """从 spec 文件路径推断业务线：specs/order/create.md → order"""
    parts = Path(spec_file).parts
    return parts[1] if len(parts) >= 3 else "default"


def _resolve_path_params(path: str, path_params: list[str]) -> tuple[str, str]:
    """处理路径参数：生成 URL 变量声明和格式化后的路径。

    Returns:
        (url_setup_code, resolved_path) — url_setup_code 是 Python 代码行，
        resolved_path 是替换后的路径表达式。
    """
    if not path_params:
        return "", f'"{path}"'

    # 生成路径参数变量声明
    setup_lines = []
    for pp in path_params:
        setup_lines.append(f'        {pp} = "TODO"  # TODO: 提供路径参数值')

    # 生成 format 调用
    format_args = ", ".join(f"{pp}={pp}" for pp in path_params)
    resolved = f'f"{path}"'

    return "\n".join(setup_lines), resolved


def generate_normal_path(spec: dict, class_name: str) -> str:
    """生成正常路径测试函数，包含字段断言和 DB 校验。"""
    spec_id = spec["id"]
    api = spec.get("api", {})
    method = api.get("method", "GET")
    path = api.get("path", "/")
    auth = spec.get("auth", "none")
    sla_ms = spec.get("sla_ms")
    params = spec.get("parameters") or []
    resp_2xx = {}
    resp_2xx_code = ""
    for code, resp in (spec.get("responses") or {}).items():
        if str(code).startswith("2"):
            resp_2xx = resp
            resp_2xx_code = str(code)
            break

    # 分类参数
    param_lines = []
    path_params = []
    for p in params:
        if p.get("in") == "path":
            path_params.append(p["name"])
            continue
        # 从 constraints 推导默认值
        constraints = p.get("constraints") or {}
        ptype = p.get("type", "string")
        if isinstance(constraints, dict):
            if "enum" in constraints and constraints["enum"]:
                default = repr(constraints["enum"][0])
            elif ptype == "string":
                default = '"TODO"'
            elif ptype in ("integer", "float"):
                default = str(constraints.get("min", 0))
            elif ptype == "boolean":
                default = "True"
            elif ptype == "array":
                default = "[]"
            elif ptype == "object":
                default = "{}"
            else:
                default = '"TODO"'
        else:
            default = '"TODO"' if ptype == "string" else "0"
        param_lines.append(f'            "{p["name"]}": {default},')

    params_block = "\n".join(param_lines) if param_lines else "            # TODO: 补全请求参数"

    # 路径参数处理
    url_setup, url_expr = _resolve_path_params(path, path_params)

    # 构建响应字段断言（从 responses.2xx.fields 生成）
    fields = resp_2xx.get("fields") or []
    field_assertions = []
    if fields:
        for field in fields:
            field_assertions.append(
                f'            assert data.get("{field}") is not None, '
                f'f"响应缺少字段: {field}"'
            )
    field_section = "\n".join(field_assertions) if field_assertions else "            # TODO: 断言核心业务字段"

    # 构建 DB 校验（从 db_effects 生成实际 SQL + 断言）
    db_blocks = []
    has_insert = False
    for effect in spec.get("db_effects") or []:
        table = effect.get("table", "?")
        op = effect.get("operation", "?")
        key_fields = effect.get("key_fields", [])
        fields_str = ", ".join(key_fields) if key_fields else "*"

        if op == "INSERT":
            has_insert = True
            db_blocks.append(
                f'        with allure.step("校验 DB — {table} INSERT"):\n'
                f'            row = db.query_one(\n'
                f'                "SELECT {fields_str} FROM {table} WHERE Id = %s",\n'
                f'                (created_id,),\n'
                f'            )\n'
                f'            assert row is not None, "{table} 表应新增记录"\n'
            )
            for field in key_fields:
                db_blocks.append(
                    f'            assert row.get("{field}") is not None, '
                    f'f"{table}.{field} 不应为空"\n'
                )
            db_blocks.append("")
        elif op == "UPDATE":
            db_blocks.append(
                f'        with allure.step("校验 DB — {table} UPDATE"):\n'
                f'            row = db.query_one(\n'
                f'                "SELECT {fields_str} FROM {table} WHERE Id = %s",\n'
                f'                (target_id,),\n'
                f'            )\n'
                f'            assert row is not None, "{table} 记录应存在"\n'
            )
            for field in key_fields:
                db_blocks.append(
                    f'            # TODO: 断言 {table}.{field} 的期望值\n'
                )
            db_blocks.append("")
        elif op == "DELETE":
            db_blocks.append(
                f'        with allure.step("校验 DB — {table} DELETE/软删除"):\n'
                f'            row = db.query_one(\n'
                f'                "SELECT * FROM {table} WHERE Id = %s",\n'
                f'                (target_id,),\n'
                f'            )\n'
                f'            # TODO: 区分物理删除(row is None)或软删除(status=deleted)\n'
            )
            db_blocks.append("")
        elif op == "UPSERT":
            has_insert = True
            db_blocks.append(
                f'        with allure.step("校验 DB — {table} UPSERT"):\n'
                f'            row = db.query_one(\n'
                f'                "SELECT {fields_str} FROM {table} WHERE Id = %s",\n'
                f'                (created_id,),\n'
                f'            )\n'
                f'            assert row is not None, "{table} 记录应存在（新增或更新）"\n'
            )
            for field in key_fields:
                db_blocks.append(
                    f'            # TODO: 断言 {table}.{field} 的期望值\n'
                )
            db_blocks.append("")
        elif op == "SELECT":
            db_blocks.append(
                f'        with allure.step("校验 DB — {table} SELECT 数据一致性"):\n'
                f'            row = db.query_one(\n'
                f'                "SELECT {fields_str} FROM {table} WHERE Id = %s",\n'
                f'                (target_id,),\n'
                f'            )\n'
                f'            assert row is not None, "{table} 记录应存在"\n'
            )
            for field in key_fields:
                db_blocks.append(
                    f'            # TODO: 断言响应中 {field} 与 DB 一致\n'
                )
            db_blocks.append("")

    db_section = "\n".join(db_blocks) if db_blocks else ""

    # DB import 声明（按需）
    db_import = "from utils.db_client import get_db\n" if db_blocks else ""
    db_init = "        db = get_db()\n" if db_blocks else ""

    # created_id / target_id 变量声明（修复 NameError）
    id_vars = ""
    if has_insert:
        id_vars = '        created_id = data.get("id")  # TODO: 替换 "id" 为实际主键字段名\n'
    if any(e.get("operation") in ("UPDATE", "DELETE", "SELECT") for e in (spec.get("db_effects") or [])):
        id_vars += '        target_id = "TODO"  # TODO: 提供目标记录 ID\n'

    # SLA 断言
    sla_assertion = ""
    if sla_ms:
        sla_assertion = (
            f'\n        with allure.step("校验响应时间 < {sla_ms}ms"):\n'
            f'            assert resp.elapsed.total_seconds() * 1000 < {sla_ms}, \\\n'
            f'                f"响应时间 {{resp.elapsed.total_seconds() * 1000:.0f}}ms 超过 SLA {sla_ms}ms"\n'
        )

    needs_cleanup = any(
        e.get("operation") in ("INSERT", "UPSERT") for e in (spec.get("db_effects") or [])
    )
    fixture_param = ", cleanup_created" if needs_cleanup else ""
    cleanup_line = "        cleanup_created.append(created_id)\n" if needs_cleanup and has_insert else ""

    # 确定期望状态码
    expected_status = resp_2xx_code if resp_2xx_code else "200"

    return f'''
    @allure.title("{method} {path} → 正常场景")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.e2e
    def test_{to_pascal(spec_id)}_Success(self, http_client{fixture_param}):
        """spec: {spec.get('file', '')}"""
{url_setup}
        with allure.step("准备请求参数"):
            params = {{
{params_block}
            }}
            allure.attach(str(params), "请求参数", allure.attachment_type.JSON)

        with allure.step("发送请求: {method} {path}"):
            resp = http_client.request(
                "{method}", {url_expr},
                json=params,
                assert_status={expected_status},
            )
            data = resp.json().get("data", resp.json())
            allure.attach(str(resp.json()), "响应", allure.attachment_type.JSON)
{id_vars}{cleanup_line}{db_init}
        with allure.step("校验响应字段"):
{field_section}
{sla_assertion}
{db_section}'''


def generate_error_paths(spec: dict, class_name: str) -> str:
    """为每个异常响应码生成测试函数。"""
    spec_id = spec["id"]
    api = spec.get("api", {})
    method = api.get("method", "GET")
    path = api.get("path", "/")
    params = spec.get("parameters") or []
    path_params = [p["name"] for p in params if p.get("in") == "path"]
    url_setup, url_expr = _resolve_path_params(path, path_params)
    functions = []

    for status_code, resp in (spec.get("responses") or {}).items():
        code_int = int(status_code) if str(status_code).isdigit() else 0
        if 200 <= code_int < 300:
            continue

        codes = resp.get("codes", [])
        descriptions = resp.get("descriptions", {})

        if codes:
            for biz_code in codes:
                desc = descriptions.get(biz_code, "")
                func_name = f"test_{to_pascal(spec_id)}_{status_code}_{_to_safe_identifier(biz_code)}"
                safe_desc = desc.replace('"', '\\"')

                functions.append(f'''
    @allure.title("{method} {path} → {status_code}: {safe_desc}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    def {func_name}(self, http_client):
        """spec: {spec.get('file', '')}"""
        with allure.step("构造触发 {status_code}/{biz_code} 的请求"):
            # TODO: 构造触发此错误的请求参数
            params = {{}}
{url_setup}
            allure.attach(str(params), "请求参数", allure.attachment_type.JSON)

        with allure.step("发送请求"):
            resp = http_client.request(
                "{method}", {url_expr},
                json=params,
                assert_status=None,
            )
            allure.attach(str(resp.json()), "响应", allure.attachment_type.JSON)

        with allure.step("校验响应: status={status_code}, code={biz_code}"):
            assert resp.status_code == {status_code}, \\
                f"期望 {status_code}，实际 {{resp.status_code}}"
            assert resp.json().get("code") == {biz_code}, \\
                f"期望 code={biz_code}，实际 {{resp.json().get('code')}}"''')
        else:
            func_name = f"test_{to_pascal(spec_id)}_{status_code}"
            functions.append(f'''
    @allure.title("{method} {path} → {status_code}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    def {func_name}(self, http_client):
        """spec: {spec.get('file', '')}"""
        with allure.step("发送请求"):
{url_setup}
            resp = http_client.request(
                "{method}", {url_expr},
                json={{}},  # TODO: 构造请求
                assert_status=None,
            )

        with allure.step("校验响应: status={status_code}"):
            assert resp.status_code == {status_code}''')

    return "\n".join(functions)


def generate_business_rules(spec: dict) -> str:
    """为每条业务规则生成测试函数，根据 type 字段生成不同骨架模式。"""
    rules = spec.get("business_rules") or []
    if not rules:
        return ""

    spec_id = spec["id"]
    api = spec.get("api", {})
    method = api.get("method", "GET")
    path = api.get("path", "/")
    params = spec.get("parameters") or []
    path_params = [p["name"] for p in params if p.get("in") == "path"]
    url_setup, url_expr = _resolve_path_params(path, path_params)
    functions = ["\n    # --- 业务规则 ---\n"]

    for rule in rules:
        rule_id = rule.get("id", "BR-???")
        desc = rule.get("description", "")
        rule_type = rule.get("type", "")
        func_name = f"test_{to_pascal(spec_id)}_{_to_safe_identifier(rule_id)}"

        if rule_type == "idempotency":
            # 幂等性规则：发两次请求，断言结果一致
            functions.append(f'''
    @allure.title("业务规则 {rule_id}: {desc}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    def {func_name}(self, http_client, cleanup_orders):
        """
        spec: {spec.get('file', '')}
        business_rule: {rule_id} (idempotency)
        """
        with allure.step("第一次请求"):
            params = {{}}  # TODO: 补全请求参数
{url_setup}
            resp1 = http_client.request("{method}", {url_expr}, json=params)
            data1 = resp1.json().get("data", resp1.json())
            cleanup_orders.append(data1.get("id", "TODO"))
            allure.attach(str(resp1.json()), "第一次响应", allure.attachment_type.JSON)

        with allure.step("第二次请求（相同参数）"):
            resp2 = http_client.request("{method}", {url_expr}, json=params, assert_status=None)
            allure.attach(str(resp2.json()), "第二次响应", allure.attachment_type.JSON)

        with allure.step("断言幂等性"):
            # TODO: 根据业务逻辑断言两次请求结果一致
            # 例如：断言返回相同的 ID，或第二次返回冲突错误码
            pass''')
        elif rule_type == "precondition":
            # 前置条件规则：先构造不满足前置条件的场景
            functions.append(f'''
    @allure.title("业务规则 {rule_id}: {desc}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    def {func_name}(self, http_client):
        """
        spec: {spec.get('file', '')}
        business_rule: {rule_id} (precondition)
        """
        with allure.step("构造不满足前置条件的请求"):
            # TODO: 构造触发此前置条件失败的请求参数
            params = {{}}
            allure.attach(str(params), "请求参数", allure.attachment_type.JSON)

        with allure.step("发送请求"):
{url_setup}
            resp = http_client.request("{method}", {url_expr}, json=params, assert_status=None)
            allure.attach(str(resp.json()), "响应", allure.attachment_type.JSON)

        with allure.step("断言前置条件校验"):
            # TODO: 断言返回预期错误码
            pass''')
        else:
            # 通用业务规则
            functions.append(f'''
    @allure.title("业务规则 {rule_id}: {desc}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.e2e
    def {func_name}(self, http_client):
        """
        spec: {spec.get('file', '')}
        business_rule: {rule_id} ({rule_type or "general"})
        """
        # TODO: 实现业务规则测试
        # 规则: {desc}
        pass''')

    return "\n".join(functions)


def append_to_existing(spec: dict, out_path: Path, dry_run: bool) -> bool:
    """向已有测试文件追加缺失的测试函数。

    扫描现有文件中的 def test_* 函数名，与 registry 中应生成的函数名对比，
    追加缺失的函数。

    Returns:
        True if any functions were appended.
    """
    if not out_path.exists():
        return False

    existing_content = out_path.read_text(encoding="utf-8")
    # 提取已有的函数名
    existing_funcs = set(re.findall(r"^\s+def (test_\w+)", existing_content, re.MULTILINE))

    # 生成所有应有的函数
    spec_id = spec["id"]
    class_name = f"Test{to_pascal(spec_id)}"
    normal = generate_normal_path(spec, class_name)
    errors = generate_error_paths(spec, class_name)
    rules = generate_business_rules(spec)

    # 提取新生成代码中的函数名
    all_new_code = normal + errors + rules
    new_funcs = re.findall(r"^\s+def (test_\w+)", all_new_code, re.MULTILINE)

    # 找出缺失的函数
    missing_funcs = [f for f in new_funcs if f not in existing_funcs]
    if not missing_funcs:
        return False

    # 构建追加内容（只追加缺失的函数）
    append_blocks = []
    for func_name in missing_funcs:
        # 从生成的代码中提取对应函数块
        pattern = rf"(    def {re.escape(func_name)}\(.*?)(?=\n    def |\nclass |\Z)"
        match = re.search(pattern, all_new_code, re.DOTALL)
        if match:
            append_blocks.append(match.group(1).rstrip())

    if not append_blocks:
        return False

    append_content = "\n\n    # --- 以下为 generate_skeletons.py --append 自动追加 ---\n\n"
    append_content += "\n\n".join(append_blocks) + "\n"

    if not dry_run:
        with out_path.open("a", encoding="utf-8") as f:
            f.write(append_content)

    return True


def generate_file(spec: dict, dry_run: bool, append_mode: bool = False) -> tuple[str, str, bool]:
    """为单个 spec 生成完整测试文件。

    返回: (file_path, content, skipped)
    """
    spec_file = spec.get("file", "")
    business = infer_business(spec_file)
    spec_id = spec["id"]
    filename = to_test_filename(spec_id, business)
    class_name = f"Test{to_pascal(spec_id)}"

    out_dir = PROJECT_ROOT / "testcase" / business
    out_path = out_dir / filename

    if out_path.exists() and not dry_run:
        if append_mode:
            appended = append_to_existing(spec, out_path, dry_run)
            return str(out_path), "", not appended
        return str(out_path), "", True

    api = spec.get("api", {})
    method = api.get("method", "GET")
    path = api.get("path", "/")

    normal = generate_normal_path(spec, class_name)
    errors = generate_error_paths(spec, class_name)
    rules = generate_business_rules(spec)

    needs_cleanup = any(
        e.get("operation") == "INSERT" for e in (spec.get("db_effects") or [])
    )

    cleanup_fixture = ""
    if needs_cleanup:
        # 从 api.path 推导删除路径（去掉末尾参数或添加 /{id}）
        delete_path = path.rstrip("/")
        # 规范化路径参数为 {oid}，确保与清理循环变量一致
        delete_path_template = re.sub(r'\{[^}]+\}', '{oid}', delete_path)
        cleanup_fixture = f'''

@pytest.fixture(autouse=True)
def cleanup_created(http_client):
    """自动清理测试创建的数据"""
    created_ids = []
    yield created_ids
    for oid in created_ids:
        try:
            http_client.delete(f"{delete_path_template}", assert_status=None)
        except Exception as exc:
            logger.warning("清理失败: %s, 错误: %s", oid, exc)
'''

    content = f'''"""{method} {path} — E2E 测试

⚠️ 本文件由 generate_skeletons.py 自动生成，请根据 TODO 标记补全细节。
spec: {spec_file}
"""
import allure
import pytest

from utils.http_client import HttpClient
from utils.db_client import get_db
from utils.logger import get_logger

logger = get_logger(__name__)


@allure.epic("{business}")
@allure.feature("{spec_id.replace('-', ' ').title()}")
class {class_name}:
{normal}
{errors}
{rules}
{cleanup_fixture}
'''

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

    return str(out_path), content, False


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="从 registry.yaml 生成测试骨架")
    parser.add_argument("--spec", type=str, help="只生成指定 spec id 的骨架")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入文件")
    parser.add_argument("--append", action="store_true", help="向已有文件追加缺失的测试函数")
    args = parser.parse_args()

    specs = load_registry()
    if specs is None:
        sys.exit(2)

    if args.spec:
        specs = [s for s in specs if s.get("id") == args.spec]
        if not specs:
            print(f"[ERROR] 未找到 spec id: {args.spec}")
            sys.exit(2)

    generated = 0
    skipped = 0
    appended = 0

    for spec in specs:
        path, content, was_skipped = generate_file(spec, args.dry_run, args.append)
        if was_skipped:
            if args.append:
                print(f"  [UP-TO-DATE] {path}")
            else:
                print(f"  [SKIP] {path}（文件已存在）")
            skipped += 1
        else:
            if args.append and Path(path).exists():
                prefix = "[APPEND]" if not args.dry_run else "[DRY-APPEND]"
                print(f"  {prefix} {path}（追加缺失函数）")
                appended += 1
            else:
                prefix = "[DRY-RUN]" if args.dry_run else "[OK]"
                print(f"  {prefix} {path}")
            if args.dry_run and content:
                print(content)
            generated += 1

    if args.append:
        print(f"\n新增 {generated} 个文件，追加 {appended} 个文件，{skipped} 个已是最新。")
    else:
        print(f"\n生成 {generated} 个文件，跳过 {skipped} 个（已存在）。")


if __name__ == "__main__":
    main()
