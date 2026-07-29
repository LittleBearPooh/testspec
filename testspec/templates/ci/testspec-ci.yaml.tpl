# TestSpec CI Pipeline 模板
#
# 支持 GitHub Actions / GitLab CI / Jenkins
# 根据实际 CI 系统选择对应模板
#
# =====================================================
# GitHub Actions 版本
# =====================================================
# 将此内容保存到 .github/workflows/testspec.yml

# name: TestSpec CI
#
# on:
#   push:
#     branches: [main, develop]
#   pull_request:
#     branches: [main]
#
# jobs:
#   testspec:
#     runs-on: ubuntu-latest
#
#     steps:
#       - uses: actions/checkout@v4
#         with:
#           fetch-depth: 0  # spec-diff 需要完整 git 历史
#
#       - name: Set up Python
#         uses: actions/setup-python@v5
#         with:
#           python-version: '3.11'
#           cache: 'pip'
#
#       - name: Install dependencies
#         run: pip install -r requirements.txt
#
#       - name: Configure override
#         run: |
#           echo '${{ secrets.VARIABLES_OVERRIDE }}' > variables_override.yaml
#
#       # --- Phase 1: Spec 质量门禁 ---
#       - name: Validate Specs
#         run: python scripts/validate_specs.py
#
#       - name: Check Coverage
#         run: python scripts/check_coverage.py --threshold 70
#
#       # --- Phase 2: 变更影响分析（PR 时） ---
#       - name: Spec Change Impact
#         if: github.event_name == 'pull_request'
#         run: python scripts/spec_diff.py --branch origin/main
#
#       # --- Phase 3: 合规检查 ---
#       - name: Compliance Check
#         run: python scripts/check_compliance.py
#
#       # --- Phase 4: 运行测试 ---
#       - name: Run Smoke Tests
#         run: pytest testcase/ -m smoke -v --junit-xml=reports/smoke.xml
#
#       - name: Run E2E Tests
#         run: |
#           pytest testcase/ -m "not smoke" -v \
#             --junit-xml=reports/e2e.xml \
#             --alluredir=reports/allure-results \
#             --reruns 2 --reruns-delay 3
#
#       # --- Phase 5: 质量度量 ---
#       - name: Generate Metrics
#         if: always()
#         run: python scripts/generate_metrics.py --output reports/metrics.json --pretty
#
#       - name: Detect Flaky Tests
#         if: always()
#         run: python scripts/detect_flaky.py --threshold 95
#
#       # --- Phase 6: 报告发布 ---
#       - name: Upload JUnit Results
#         if: always()
#         uses: actions/upload-artifact@v4
#         with:
#           name: test-results
#           path: reports/*.xml
#
#       - name: Publish Allure Report
#         if: always()
#         uses: simple-elf/allure-report-action@v1.9
#         with:
#           allure_results: reports/allure-results
#           allure_report: reports/allure-report
#
#       - name: Upload Metrics
#         if: always()
#         uses: actions/upload-artifact@v4
#         with:
#           name: quality-metrics
#           path: reports/metrics.json


# =====================================================
# GitLab CI 版本
# =====================================================
# 将此内容保存到 .gitlab-ci.yml

# stages:
#   - validate
#   - test
#   - quality
#
# variables:
#   PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
#
# .python_setup: &python_setup
#   image: python:3.11
#   before_script:
#     - pip install -r requirements.txt
#     - echo "$VARIABLES_OVERRIDE" > variables_override.yaml
#
# # --- Phase 1: Spec 质量门禁 ---
# validate-specs:
#   <<: *python_setup
#   stage: validate
#   script:
#     - python scripts/validate_specs.py
#     - python scripts/check_coverage.py --threshold 70
#     - python scripts/check_compliance.py
#
# # --- Phase 2: 变更影响分析 ---
# spec-impact:
#   <<: *python_setup
#   stage: validate
#   script:
#     - python scripts/spec_diff.py --branch origin/$CI_DEFAULT_BRANCH
#   only:
#     - merge_requests
#
# # --- Phase 3: 运行测试 ---
# test-smoke:
#   <<: *python_setup
#   stage: test
#   script:
#     - pytest testcase/ -m smoke -v --junit-xml=reports/smoke.xml
#   artifacts:
#     reports:
#       junit: reports/smoke.xml
#
# test-e2e:
#   <<: *python_setup
#   stage: test
#   script:
#     - pytest testcase/ -m "not smoke" -v
#         --junit-xml=reports/e2e.xml
#         --alluredir=reports/allure-results
#         --reruns 2 --reruns-delay 3
#   artifacts:
#     reports:
#       junit: reports/e2e.xml
#     paths:
#       - reports/allure-results
#
# # --- Phase 4: 质量度量 ---
# quality-metrics:
#   <<: *python_setup
#   stage: quality
#   script:
#     - python scripts/generate_metrics.py --output reports/metrics.json --pretty
#     - python scripts/detect_flaky.py --threshold 95
#   artifacts:
#     paths:
#       - reports/metrics.json
#   when: always
