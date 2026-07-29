<#
.SYNOPSIS
    {{PROJECT_NAME_TITLE}} 全量测试执行脚本

.DESCRIPTION
    顺序执行所有测试分组，为每个分组生成独立 HTML 报告，
    全部执行完毕后输出汇总结果，并可选发送报告邮件。

    【新增用例时的操作】
    - 新增 smoke/contract 用例：将测试文件路径追加到分组 1 的参数列表中。
    - 新增 e2e 用例：参照现有分组块，新增独立分组块（Invoke-PytestGroup），分组编号顺序递增。

    {{#IF_HAS_EMAIL}}
    【收件人配置】
    - 可通过环境变量 TEST_REPORT_EMAIL_TO 指定报告接收人
    {{/IF_HAS_EMAIL}}

    【前提】
    - 已激活 Python 虚拟环境（.venv\Scripts\Activate.ps1）
    - 已配置好 variables_override.yaml（含敏感配置）

    【执行方式】
        cd <项目根目录>
        .\.venv\Scripts\Activate.ps1
        .\run_tests.ps1
#>

$ProjectName = "{{PROJECT_NAME_SNAKE}}"

# 切到脚本所在目录（项目根目录），确保 pytest 按 pytest.ini 中的 testpaths 解析测试
Set-Location $PSScriptRoot

# Python 可执行文件检测
$pythonExe = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

# ------------------------------------------------------------------
# 报告目录：按执行时间命名，每次运行独立存放
# ------------------------------------------------------------------
$runTime   = Get-Date
$timestamp = $runTime.ToString("yyyy-MM-dd HH:mm:ss")   # 用于邮件主题和 HTML 正文
$dirLabel  = $runTime.ToString("yyyy-MM-dd_HHmmss")     # 用于目录名（不含冒号/空格）
$reportDir = "reports\$dirLabel"

New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
Write-Host "报告目录：$reportDir" -ForegroundColor DarkGray

# 有序字典：记录各分组退出码，用于末尾汇总和写入 results.json
$results = [ordered]@{}

# ------------------------------------------------------------------
# 工具函数：统一封装 pytest 调用、HTML 报告生成与结果记录
# ------------------------------------------------------------------
function Invoke-PytestGroup {
    param(
        [string]   $GroupName,  # 分组名称（汇总时展示，同时作为报告文件名基础）
        [string[]] $PytestArgs  # 传给 pytest 的完整参数列表（不含 --html）
    )

    # 将分组名转为合法文件名（替换空格和标点为下划线）
    $safeName   = $GroupName -replace '[^\w]', '_' -replace '_+', '_'
    $reportFile = "$script:reportDir\$safeName.html"

    Write-Host ""
    Write-Host ("=" * 62) -ForegroundColor Cyan
    Write-Host "  $GroupName" -ForegroundColor Cyan
    Write-Host ("=" * 62) -ForegroundColor Cyan

    # 将 HTML / JUnit XML 报告参数追加到调用方传入的参数列表末尾
    $xmlFile = "$script:reportDir\$safeName.xml"
    $allArgs = $PytestArgs + @("--html=$reportFile", "--self-contained-html", "--junit-xml=$xmlFile")
    & $pythonExe -m pytest @allArgs

    # 记录退出码（0=全部通过，1=有失败，2=执行错误，5=无用例收集到）
    $code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    $script:results[$GroupName] = $code
}

# ==================================================================
# 分组 1：Contract & Smoke
# 始终执行，用于验证基础配置与接口契约。
# 新增 smoke/contract 用例时，直接在下方列表中追加测试文件路径。
# ==================================================================
Invoke-PytestGroup "1. Contract & Smoke" @(
    # "testcase/<业务线>/test_xxx_contract.py",
    # "testcase/<业务线>/test_xxx_smoke.py",
    "-v"
)

# ==================================================================
# --- 业务线 E2E 分组 ---
# 新增业务线时，在此处复制下方模板块，递增分组编号。
# ==================================================================

# ==================================================================
# 分组 2：<业务线名> E2E
# 描述：填写该分组覆盖的场景说明。
# ==================================================================
# Invoke-PytestGroup "2. <业务线名> E2E" @(
#     "testcase/<业务线>/test_xxx_e2e.py",
#     "-v", "-s"
# )

# ==================================================================
# 汇总输出
# ==================================================================
Write-Host ""
Write-Host ("=" * 62) -ForegroundColor Cyan
Write-Host "  执行结果汇总" -ForegroundColor Cyan
Write-Host ("=" * 62) -ForegroundColor Cyan

$allPassed = $true
foreach ($group in $results.Keys) {
    $code = $results[$group]
    if ($code -eq 0) {
        Write-Host "  [PASS]  $group" -ForegroundColor Green
    } elseif ($code -eq 5) {
        Write-Host "  [SKIP]  $group (no tests collected)" -ForegroundColor Yellow
    } else {
        Write-Host "  [FAIL]  $group (exit=$code)" -ForegroundColor Red
        $allPassed = $false
    }
}

# ==================================================================
# 保存 results.json
# ==================================================================
Write-Host ""
Write-Host "保存执行结果..." -ForegroundColor DarkGray

$resultsJson = $results | ConvertTo-Json
$resultsJson | Out-File -FilePath "$reportDir\results.json" -Encoding utf8

{{#IF_HAS_EMAIL}}
# ==================================================================
# 发送报告邮件（需要配置 variables_override.yaml 中的邮件账号）
# ==================================================================
Write-Host "发送测试报告邮件..." -ForegroundColor DarkGray
python scripts\send_test_report.py --report-dir $reportDir --timestamp $timestamp
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] 邮件发送失败，请检查 variables_override.yaml 中的邮件配置（exit=$LASTEXITCODE）" -ForegroundColor Yellow
}
{{/IF_HAS_EMAIL}}

# ==================================================================
# 最终退出码
# ==================================================================
Write-Host ""
if ($allPassed) {
    Write-Host "  全部通过" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  存在失败分组，请检查上方详情" -ForegroundColor Red
    exit 1
}
