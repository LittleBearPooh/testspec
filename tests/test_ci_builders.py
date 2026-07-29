"""testspec.ci_builders 模块测试。

直接测试 ci_builders.py 的私有辅助函数和公共 API。
"""

from __future__ import annotations

from testspec.ci_builders import (
    _build_e2e_args,
    _build_gitlab_job_dict,
    build_requirements,
    build_gitignore,
    build_github_actions_yaml,
    build_gitlab_ci_yaml,
    build_testspec_manifest,
)


class TestBuildE2eArgs:
    """测试 _build_e2e_args 辅助函数。"""

    def test_with_allure(self) -> None:
        result = _build_e2e_args(True)
        assert "--alluredir=reports/allure-results" in result
        assert "--reruns 2" in result
        assert "--reruns-delay 3" in result
        assert 'reports/e2e.xml' in result

    def test_without_allure(self) -> None:
        result = _build_e2e_args(False)
        assert "--alluredir" not in result
        assert "--reruns 2" in result
        assert 'reports/e2e.xml' in result

    def test_smoke_marker_excluded(self) -> None:
        result = _build_e2e_args(False)
        assert '"not smoke"' in result


class TestBuildGitlabJobDict:
    """_build_gitlab_job_dict 辅助函数测试（dict 结构断言）。"""

    def test_basic_job_has_extends_and_stage(self) -> None:
        d = _build_gitlab_job_dict("test", ["echo hello"])
        assert d["extends"] == ".python_setup"
        assert d["stage"] == "test"
        assert "echo hello" in d["script"]

    def test_no_yaml_anchors_in_dict(self) -> None:
        """dict 中不应存在 YAML anchor 字符串片段。"""
        d = _build_gitlab_job_dict("test", ["echo hello"])
        assert "<<: *python_setup" not in str(d)

    def test_with_artifacts_junit(self) -> None:
        d = _build_gitlab_job_dict(
            "test", ["pytest"], artifacts_junit="reports/test.xml",
        )
        assert d["artifacts"]["reports"]["junit"] == "reports/test.xml"

    def test_with_artifact_paths(self) -> None:
        d = _build_gitlab_job_dict(
            "test", ["pytest"], artifact_paths=["reports/", "coverage/"],
        )
        assert "reports/" in d["artifacts"]["paths"]
        assert "coverage/" in d["artifacts"]["paths"]

    def test_with_only(self) -> None:
        d = _build_gitlab_job_dict(
            "validate", ["check"], only=["merge_requests"],
        )
        assert d["only"] == ["merge_requests"]

    def test_with_when(self) -> None:
        d = _build_gitlab_job_dict("quality", ["clean"], when="always")
        assert d["when"] == "always"

    def test_no_artifacts_key_when_empty(self) -> None:
        d = _build_gitlab_job_dict("test", ["cmd"])
        assert "artifacts" not in d

    def test_multiple_scripts(self) -> None:
        d = _build_gitlab_job_dict("test", ["cmd1", "cmd2", "cmd3"])
        assert d["script"] == ["cmd1", "cmd2", "cmd3"]


class TestCiBuildersPublicApi:
    """公共 API 冒烟测试：所有构建函数可调用并返回非空字符串。"""

    def test_build_requirements_callable(self, base_ctx) -> None:
        result = build_requirements(base_ctx)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "pytest" in result

    def test_build_gitignore_callable(self, base_ctx) -> None:
        result = build_gitignore(base_ctx)
        assert isinstance(result, str)
        assert "__pycache__" in result

    def test_build_github_actions_yaml_callable(self, base_ctx) -> None:
        result = build_github_actions_yaml(base_ctx)
        assert isinstance(result, str)
        assert "TestSpec CI" in result

    def test_build_gitlab_ci_yaml_callable(self, base_ctx) -> None:
        result = build_gitlab_ci_yaml(base_ctx)
        assert isinstance(result, str)
        assert "stages:" in result

    def test_build_gitlab_ci_yaml_uses_extends_not_anchors(
        self, base_ctx,
    ) -> None:
        """迁移后应使用 extends: 而非 <<: *python_setup YAML 锚点。"""
        result = build_gitlab_ci_yaml(base_ctx)
        assert "<<: *python_setup" not in result
        assert "extends:" in result
        assert ".python_setup" in result

    def test_build_testspec_manifest_callable(self, base_ctx) -> None:
        result = build_testspec_manifest(base_ctx)
        assert isinstance(result, str)
        import json
        data = json.loads(result)
        assert "testspec_version" in data
