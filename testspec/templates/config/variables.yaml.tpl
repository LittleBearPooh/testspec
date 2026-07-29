# {{PROJECT_NAME_TITLE}} - 测试配置
# 非敏感默认值，提交到 git
# 敏感值（密码、token、DB 凭据等）放在 variables_override.yaml（gitignored）

# ——— 通用 ———
base_url: "https://your-api-host.example.com"
timeout: 30

{{#IF_HAS_HTTP}}
# ——— 被测服务 ———
{{PROJECT_NAME_SNAKE}}:
  host: "https://api.example.com"
  timeout: 30
{{/IF_HAS_HTTP}}

{{#IF_HAS_DB}}
# ——— 数据库连接 ———
# 密码等敏感字段请填写到 variables_override.yaml，此处仅留非敏感默认值
db:
  default:
    host: "localhost"
    port: {{DB_DEFAULT_PORT}}   # SQL Server=1433, MySQL=3306, PostgreSQL=5432
    user: "test_user"
    password: ""       # 敏感值：在 variables_override.yaml 中覆盖
    name: "test_db"
  # 如有多库，按此格式追加
  # secondary:
  #   host: "localhost"
  #   port: 1433
  #   user: "test_user"
  #   password: ""
  #   name: "secondary_db"
{{/IF_HAS_DB}}

{{#IF_HAS_HTTP}}
# ——— 测试账号（测试环境） ———
# 密码等敏感字段请填写到 variables_override.yaml
test_accounts:
  default:
    username: "test@example.com"
    password: ""    # 敏感值：在 variables_override.yaml 中覆盖
{{/IF_HAS_HTTP}}

{{#IF_HAS_HTTP}}
# ——— 认证账号 ———
auth:
  default:
    username: ""
    password: ""    # 敏感值：在 variables_override.yaml 中覆盖
    # 以下字段适用于 OAuth2/OIDC 认证流程，非项目可删除
    # sso_base: "https://sso.example.com"
    # client_id: "MyApp.JSClient"
    # redirect_uri: "https://app.example.com/callback"
    # scope: "openid offline_access profile email"
    # timeout_seconds: 30
{{/IF_HAS_HTTP}}

{{#IF_HAS_EMAIL}}
# ——— 发件账号（邮件触发场景） ———
email:
  accounts:
    default:
      smtp_host: "smtp.example.com"
      smtp_port: 465
      sender: "test@example.com"
      sender_name: "Test Sender"
      username: "test@example.com"
      password: ""    # 敏感值：在 variables_override.yaml 中覆盖
      use_ssl: true
      use_tls: false
      timeout_seconds: 30
  messages:
    default:
      subject: "Test Notification"
      content: "This is a test notification email."
      content_type: "plain"
{{/IF_HAS_EMAIL}}

# ——— 业务线特定配置（按需追加） ———
# 参照上方格式，将各业务线的 host、账号、超时等非敏感配置写在此处。
