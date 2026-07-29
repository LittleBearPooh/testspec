#!/usr/bin/env bash
# {{PROJECT_NAME_TITLE}} - 测试执行脚本（Bash 版）
#
# 使用方式：
#   chmod +x run_tests.sh
#   ./run_tests.sh
#
# 前提：
#   - 已激活 Python 虚拟环境（source .venv/bin/activate）
#   - 已配置好 variables_override.yaml（含敏感配置）
#
# 新增用例时：
#   - 新增 smoke/contract 用例：追加到分组 1 的 run_pytest_group 调用参数。
#   - 新增 e2e 用例：参照现有分组块，新增独立 run_pytest_group 调用，分组编号递增。

set -euo pipefail

PROJECT_NAME="{{PROJECT_NAME_SNAKE}}"

# 切换到脚本所在目录（项目根目录），确保 pytest 按 pytest.ini 解析测试
cd "$(dirname "$0")"

# ------------------------------------------------------------------
# Python 可执行文件检测
# ------------------------------------------------------------------
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON="python"
    else
        echo "[ERROR] Python not found" >&2; exit 1
    fi
fi

# ------------------------------------------------------------------
# 报告目录：按执行时间命名，每次运行独立存放
# ------------------------------------------------------------------
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
DIR_LABEL=$(date +"%Y-%m-%d_%H%M%S")
REPORT_DIR="reports/${DIR_LABEL}"

mkdir -p "$REPORT_DIR"
echo "报告目录：$REPORT_DIR"

# 用临时目录存储各分组退出码（兼容 bash 3.x / macOS，不依赖关联数组）
RESULTS_DIR=$(mktemp -d)

# ------------------------------------------------------------------
# 工具函数：统一封装 pytest 调用、HTML 报告生成与结果记录
# ------------------------------------------------------------------
run_pytest_group() {
    local group_name="$1"
    shift  # 移除第一个参数，剩余均为 pytest 参数

    # 将分组名转为合法文件名（替换非字母数字字符为下划线，合并连续下划线）
    local safe_name
    safe_name=$(echo "$group_name" | tr -cs '[:alnum:]_' '_' | sed 's/__*/_/g; s/^_//; s/_$//')

    local report_file="${REPORT_DIR}/${safe_name}.html"
    local xml_file="${REPORT_DIR}/${safe_name}.xml"

    echo ""
    echo "============================================================"
    echo "  ${group_name}"
    echo "============================================================"

    # 执行 pytest，追加 HTML 和 JUnit XML 报告参数
    # 使用 exit_code=0; cmd || exit_code=$? 模式正确捕获退出码
    exit_code=0
    $PYTHON -m pytest "$@" \
        --html="$report_file" \
        --self-contained-html \
        --junit-xml="$xml_file" \
        || exit_code=$?

    # 记录退出码（0=全部通过，1=有失败，2=执行错误，5=无用例收集到）
    printf '%d' "$exit_code" > "${RESULTS_DIR}/${safe_name}"
}

# ==================================================================
# 分组 1：Contract & Smoke
# 始终执行，用于验证基础配置与接口契约。
# 新增 smoke/contract 用例时，直接在下方追加测试文件路径。
# ==================================================================
run_pytest_group "1. Contract & Smoke" \
    -v
    # "testcase/<业务线>/test_xxx_contract.py" \
    # "testcase/<业务线>/test_xxx_smoke.py" \

# ==================================================================
# --- 业务线 E2E 分组 ---
# 新增业务线时，复制下方模板块，递增分组编号。
# ==================================================================

# ==================================================================
# 分组 2：<业务线名> E2E
# 描述：填写该分组覆盖的场景说明。
# ==================================================================
# run_pytest_group "2. <业务线名> E2E" \
#     "testcase/<业务线>/test_xxx_e2e.py" \
#     -v -s

# ==================================================================
# 汇总输出
# ==================================================================
echo ""
echo "============================================================"
echo "  执行结果汇总"
echo "============================================================"

ALL_PASSED=true
for result_file in "${RESULTS_DIR}"/*; do
    group=$(basename "$result_file")
    code=$(cat "$result_file")
    if [ "$code" -eq 0 ]; then
        echo "  [PASS]  $group"
    elif [ "$code" -eq 5 ]; then
        echo "  [SKIP]  $group (no tests collected)"
    else
        echo "  [FAIL]  $group (exit=$code)"
        ALL_PASSED=false
    fi
done

# ==================================================================
# 保存 results.json
# ==================================================================
echo ""
echo "保存执行结果..."

# 将各分组退出码序列化为 JSON（通过 Python 确保正确转义）
$PYTHON -c "
import json, pathlib
d = {}
for f in pathlib.Path('${RESULTS_DIR}').iterdir():
    d[f.name] = int(f.read_text().strip())
print(json.dumps(d, ensure_ascii=False))
" > "${REPORT_DIR}/results.json"

{{#IF_HAS_EMAIL}}
# ==================================================================
# 发送报告邮件（需要配置 variables_override.yaml 中的邮件账号）
# ==================================================================
echo "发送测试报告邮件..."
$PYTHON scripts/send_test_report.py --report-dir "$REPORT_DIR" --timestamp "$TIMESTAMP" || \
    echo "[WARN] 邮件发送失败，请检查 variables_override.yaml 中的邮件配置"
{{/IF_HAS_EMAIL}}

# ==================================================================
# 最终退出码
# ==================================================================
echo ""
if [ "$ALL_PASSED" = true ]; then
    echo "  全部通过"
    exit 0
else
    echo "  存在失败分组，请检查上方详情"
    exit 1
fi
