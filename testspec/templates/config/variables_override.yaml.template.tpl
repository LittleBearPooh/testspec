# variables_override.yaml.template
#
# 使用说明：
#   1. 将本文件复制为 variables_override.yaml（该文件已被 .gitignore，不会提交到 Git）
#   2. 将下方所有 "<FILL_IN>" 占位符替换为真实值
#   3. 执行环境（CI/本地）只需维护 variables_override.yaml，不要修改 variables.yaml
#   4. 同名键会深度合并并覆盖 variables.yaml 中的默认值
#
# 注意：本模板文件（*.template）需要提交到 git，以记录配置结构；
#       variables_override.yaml 含真实凭据，绝不提交。

{{#IF_HAS_HTTP}}
# ——— 测试账号密码 ———
test_accounts:
  default:
    password: "<FILL_IN>"
{{/IF_HAS_HTTP}}

{{#IF_HAS_HTTP}}
# ——— 认证账号密码 ———
auth:
  default:
    password: "<FILL_IN>"
{{/IF_HAS_HTTP}}

{{#IF_HAS_DB}}
# ——— 数据库连接（敏感字段） ———
db:
  default:
    host: "<FILL_IN>"
    user: "<FILL_IN>"
    password: "<FILL_IN>"
  # secondary:
  #   host: "<FILL_IN>"
  #   user: "<FILL_IN>"
  #   password: "<FILL_IN>"
{{/IF_HAS_DB}}

{{#IF_HAS_EMAIL}}
# ——— 发件账号密码 ———
email:
  accounts:
    default:
      password: "<FILL_IN>"
{{/IF_HAS_EMAIL}}

{{#IF_HAS_HTTP}}
# ——— 被测服务 API 密钥（如有） ———
# {{PROJECT_NAME_SNAKE}}:
#   api_key: "<FILL_IN>"
#   secret: "<FILL_IN>"
{{/IF_HAS_HTTP}}
