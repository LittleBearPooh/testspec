# TestSpec — 规格优先的测试自动化工程化框架

**[English](README-EN.md)** | 中文

[![CI](https://github.com/testspec/testspec/actions/workflows/testspec.yml/badge.svg)](https://github.com/testspec/testspec/actions/workflows/testspec.yml)
[![PyPI version](https://img.shields.io/pypi/v/testspec.svg)](https://pypi.org/project/testspec/)
[![Python](https://img.shields.io/pypi/pyversions/testspec.svg)](https://pypi.org/project/testspec/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 规格优先的测试自动化工程化框架，类似 OpenSpec 但面向测试项目。
> 一条命令初始化新测试项目，立即获得完整的 AI 指导能力。

---

## 核心理念

```
Spec（规格文档）→ Cases（用例设计）→ Data（测试数据）→ Code（测试代码）
     → Assertion（断言设计）→ Verify（数据验证）→ Report（报告装饰）→ Compliance（合规自检）
```

TestSpec 的核心哲学：**先写规格文档，再写测试代码**。

- 规格文档（specs/）是 AI 和人类共同消费的"单一事实来源"
- 8 步工作流确保每个测试用例都有完整的覆盖维度、数据策略、断言方案和合规检查
- AI 在每个步骤中严格按照规范执行，不会"自由发挥"

---

## 快速开始

```bash
# 方式 1: pip 安装（推荐）
pip install -e testspec/
testspec init                          # 交互式初始化
testspec init --config project.json    # 非交互式（从配置文件）
testspec init -y                       # 使用默认值快速生成
testspec validate ./my-project         # 校验已生成项目的完整性
testspec upgrade ./my-project          # 升级框架管理文件（保留用户代码）

# 方式 2: 直接运行（向后兼容）
python testspec/init.py

# 2. 按交互提示输入项目信息（项目名称、测试类型、数据库、业务线等）

# 3. 进入生成的项目
cd your-project-name

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置敏感变量
cp variables_override.yaml.template variables_override.yaml
# 编辑 variables_override.yaml，填入 DB 密码、API 密钥等

# 6. 在 specs/ 下添加规格文档（参考 specs/spec-template.md）

# 7. 使用 Claude Code 的技能命令开始开发
# /test-workflow — 启动 8 步工作流
```

---

## 框架结构

```
testspec/
├── README.md                      ← 你正在看的文件
├── README-EN.md                   ← English version
├── pyproject.toml                 ← pip 打包配置（testspec init）
├── init.py                        ← 脚手架脚本（向后兼容入口）
├── LICENSE                        ← MIT 许可证
├── CONTRIBUTING.md                ← 贡献指南
├── CHANGELOG.md                   ← 版本变更记录
├── CODE_OF_CONDUCT.md             ← 行为准则
├── SECURITY.md                    ← 安全策略
├── testspec/                      ← Python 包（CLI + 模块化逻辑）
│   ├── __init__.py                ← 公共 API 导出
│   ├── cli.py                     ← CLI 入口（testspec 命令）
│   ├── constants.py               ← 版本号、枚举、验证集合
│   ├── catalogs.py                ← 数据映射表、技能文件列表
│   ├── registry.py                ← OptionRegistry 可注册选项机制
│   ├── context.py                 ← 上下文构建（TypedDict + dataclass）
│   ├── wizard.py                  ← 交互式向导
│   ├── renderer.py                ← 模板引擎（IF/FOR/include）
│   ├── generator.py               ← 项目生成器（原子写入 + 错误处理）
│   ├── sections.py                ← 12 个可插拔 SectionRenderer
│   ├── ci_builders.py             ← 动态文件内容构建（requirements/CI YAML）
│   ├── yaml_emitter.py            ← 零依赖 YAML 序列化器
│   ├── hooks.py                   ← 生命周期 Hook 注册表
│   ├── plugins.py                 ← 插件发现（entry_points）
│   ├── upgrader.py                ← 项目升级器（plan/apply 两阶段）
│   ├── validator.py               ← 项目完整性校验器
│   ├── exceptions.py              ← 异常类层次
│   └── templates/                 ← 所有模板文件（随包分发）
│       ├── ai_rules/              ← AI 行为规则
│       ├── skills/                ← 15 个技能定义
│       ├── specs/                 ← 规格文档模板
│       ├── config/                ← 变量配置模板
│       ├── config_loader/         ← 变量加载器
│       ├── utils/                 ← 工具层代码桩
│       ├── execution/             ← 执行脚本（PowerShell + Bash）
│       ├── pytest_config/         ← pytest 配置和 conftest
│       ├── scripts/               ← 工具链脚本（10 个）
│       ├── mock/                  ← Mock 服务模板
│       ├── docker/                ← Docker 配置模板
│       ├── schemas/               ← Schema 文档模板
│       └── ci/                    ← CI/CD 模板
├── tests/                         ← 框架自身的单元测试
└── docs/                          ← 使用文档
    ├── philosophy.md              ← 规格优先开发哲学
    ├── workflow-guide.md          ← 8 步工作流详细指南
    └── extension-guide.md         ← 扩展指南
```

---

## 文档导航

| 文档 | 说明 |
|---|---|
| [USER-GUIDE.md](USER-GUIDE.md) | 用户完整使用指南（含安装、配置、工作流详解） |
| [PLAYBOOK.md](PLAYBOOK.md) | 实战操作手册（场景驱动的端到端操作指南） |
| [docs/philosophy.md](docs/philosophy.md) | 规格优先开发哲学与设计理念 |
| [docs/workflow-guide.md](docs/workflow-guide.md) | 8 步工作流详细指南 |
| [docs/extension-guide.md](docs/extension-guide.md) | 框架扩展开发指南 |

---

## 生成的项目结构

运行 `init.py` 后，生成的项目结构如下（以 API 测试项目为例）：

```
your-project/
├── CLAUDE.md                        ← AI 行为规则 + 架构指南（给 AI 和新成员的地图）
├── testspec.json                    ← TestSpec 版本标记
├── .claude/commands/              ← Claude Code 技能命令（15 个）
├── config/
│   └── variable_loader.py         ← 深度合并变量加载器
├── utils/
│   ├── http_client.py             ← HTTP 客户端（sentinel 断言模式）
│   ├── db_client.py               ← 数据库客户端（连接池 + 参数化 SQL）
│   ├── logger.py                  ← 日志工厂（文件写入 + 敏感脱敏）
│   ├── data_reader.py             ← YAML/JSON/Excel 数据读取
│   ├── data_factory.py            ← 测试数据工厂
│   ├── contract_checker.py        ← 契约校验工具
│   ├── assertions.py              ← 通用断言辅助
│   ├── poll_helper.py             ← 轮询等待辅助
│   └── mock_server.py             ← Mock 服务
├── <project_name>/                ← 项目专属模块（需自行实现）
├── testcase/                      ← 测试用例目录
│   ├── conftest.py                ← 测试级 fixtures
│   └── <business_line>/           ← 按业务线分目录
├── specs/                         ← 规格文档目录
│   ├── spec-template.md           ← 规格文档模板
│   ├── spec-example.md            ← 规格文档示例
│   ├── registry.yaml              ← Spec 注册表
│   └── <business_line>/           ← 按业务线分目录
├── mock/                          ← Mock 服务目录
├── data/yaml|json|excel/          ← 测试数据目录
├── scripts/                       ← 工具脚本（10 个）
├── ci/                            ← CI/CD 配置
├── docker/                        ← Docker 配置（有 DB 时生成）
├── variables.yaml                 ← 非敏感默认变量
├── variables_override.yaml.template ← 敏感变量结构指南
├── pytest.ini                     ← pytest 配置
├── conftest.py                    ← 根级 conftest
├── run_<project>_tests.ps1        ← PowerShell 执行脚本
├── run_<project>_tests.sh         ← Bash 执行脚本
├── requirements.txt               ← 动态生成的依赖
└── .gitignore                     ← Git 忽略规则
```

---

## 8 步工作流

| 步骤 | 命令 | 必须 | 说明 |
|---|---|---|---|
| — | `/AutomatedTesting` | 入口 | 智能调度器：分析输入素材，自动规划技能调用序列 |
| 0 | （内联） | ✓ | 读 `specs/` 规格文档，建立追溯表 |
| 1 | `/case-design` | ✓ | 先出用例清单，确认覆盖维度 |
| 2 | `/test-data` | 推荐 | 数据驱动用例或需要 YAML 组织数据时 |
| 3 | `/write-tests` | ✓ | 生成 pytest 代码框架 |
| 4 | `/assertion-design` | 推荐 | 断言策略不明确或字段复杂时 |
| 5 | `/data-verify` | ✓（写操作） | 写操作必须有数据验证 |
| 6 | `/report-decorate` | ✓ | 补全 Allure 注解 |
| 7 | `/compliance-check` | ✓ | 收尾门禁扫描 |
| — | `/spec-review` | 推荐 | AI 审查 spec 文档质量 |
| — | `/mock-setup` | 按需 | 搭建 Mock 服务 |
| — | `/contract-test` | 按需 | 生成契约测试 |
| — | `/analyze-ci-failures` | 按需 | 分析 CI 失败原因 |
| — | `/spec-diff` | 按需 | 对比规约变更影响 |
| — | `/debug-failure` | 按需 | 用例失败时调用 |

---

## 支持的测试类型

| 类型 | 说明 | 步骤 5（数据验证）含义 |
|---|---|---|
| **api** | HTTP 接口自动化测试 | DB 查询验证（get_db().query()） |
| **unit** | 单元测试 | Mock 调用验证（assert_called_once_with） |
| **integ** | 集成测试 | 系统状态验证（DB 或查询 API） |
| **e2e** | 端到端测试 | 多层验证（API + DB + 副作用） |

---

## 支持的数据库

| 数据库 | Python 驱动 | 条件块标识 |
|---|---|---|
| SQL Server | pymssql + DBUtils | `DB_SQLSERVER` |
| MySQL | PyMySQL + DBUtils | `DB_MYSQL` |
| PostgreSQL | psycopg2 + DBUtils | `DB_POSTGRESQL` |
| SQLite | sqlite3（标准库） | `DB_SQLITE` |

---

## 技术细节

- **模板引擎**: `{{KEY}}` 占位符 + `{{#IF_KEY}}...{{/IF_KEY}}` 条件块，纯 Python 标准库实现
- **Python 版本**: 3.9+（init.py 无外部依赖）
- **AI 工具兼容**: 生成 `.claude/commands/` 格式，共 15 个技能命令
- **CI/CD**: 支持 GitHub Actions 和 GitLab CI（直接生成可用 YAML，非注释模板）
- **非交互式**: `testspec init --config project.json` 支持 CI 中自动化生成项目
- **原子写入**: 项目生成使用临时目录 + 原子移动，失败时自动清理
- **Spec DSL v2.0**: 支持 auth 认证、结构化 constraints、SELECT 操作、SLA 定义、response_schema 关联

---

## 文档索引

- [规格优先开发哲学](docs/philosophy.md)
- [8 步工作流详细指南](docs/workflow-guide.md)
- [扩展指南](docs/extension-guide.md)

---

## License

MIT — 可自由使用和修改。
