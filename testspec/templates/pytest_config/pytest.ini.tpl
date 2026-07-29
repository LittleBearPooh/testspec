[pytest]
minversion = 7.0
addopts = -v --tb=short --strict-markers --strict-config

testpaths =
    testcase

pythonpath = .

python_files = test_*.py
python_classes = Test*
python_functions = test_*

# markers 说明：
#   - smoke / regression / e2e 是通用分类标记
#   - p0 / p1 是优先级标记
#   - 其余为各业务线专用标记（按需新增，并在此处注册）
markers =
    smoke: 冒烟测试（配置验证/契约检查，不依赖真实环境）
    regression: 回归测试
    e2e: 端到端测试（调用真实环境接口）
    p0: 最高优先级（阻塞发布）
    p1: 高优先级（核心业务流程）
    contract: 契约测试（JSON Schema 结构校验）
    {{#IF_HAS_ALLURE}}
    # Allure 相关 markers（severity / feature / story 等）由 allure-pytest 自动处理，无需在此注册
    {{/IF_HAS_ALLURE}}
    {{#IF_NOT_HAS_ALLURE}}
    feature: 业务模块标记（非 Allure 模式使用）
    story: 业务场景标记（非 Allure 模式使用）
    severity: 用例等级标记（非 Allure 模式使用）
    {{/IF_NOT_HAS_ALLURE}}
    # --- 业务线标记（按需取消注释并补充说明） ---
    # <业务线>: <描述>
    # （新增业务线 marker 时，在此处添加并同步更新 CLAUDE.md 中的 marker 列表）

norecursedirs =
    .git
    .venv
    .vscode
    .claude
    venv
    env
    __pycache__
    build
    dist
    logs
    reports
    .tox
    .mypy_cache
    .pytest_cache
