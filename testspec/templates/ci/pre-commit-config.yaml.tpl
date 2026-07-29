# TestSpec 项目 Git Hooks 配置
#
# 安装方式：
#   pip install pre-commit
#   pre-commit install
#
# 手动运行：
#   pre-commit run --all-files

repos:
  # --- 通用检查 ---
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: ['--allow-multiple-documents']
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-merge-conflict

  # --- Python 代码质量 ---
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: ['--fix', '--select', 'E,F,W']
      - id: ruff-format

  # --- TestSpec 工具链 ---
  - repo: local
    hooks:
      # Spec 注册表校验
      - id: validate-specs
        name: TestSpec - Validate Registry
        entry: python scripts/validate_specs.py
        language: system
        files: ^specs/
        pass_filenames: false

      # 覆盖率检查（不阻塞，仅提示）
      - id: check-coverage
        name: TestSpec - Check Coverage
        entry: python scripts/check_coverage.py --threshold 60
        language: system
        files: ^(specs/|testcase/)
        pass_filenames: false

      # 合规自检
      - id: compliance-check
        name: TestSpec - Compliance Check
        entry: python scripts/check_compliance.py
        language: system
        files: ^testcase/.*\.py$
        pass_filenames: false

      # Spec 变更影响分析（仅提示）
      - id: spec-diff
        name: TestSpec - Spec Change Impact
        entry: python scripts/spec_diff.py --staged
        language: system
        files: ^specs/
        pass_filenames: false
        stages: [pre-commit]
