"""testspec.hooks 模块测试。

HookRegistry 单元测试 + 与 ProjectGenerator 的集成测试。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from testspec.hooks import HookRegistry, VALID_EVENTS
from testspec.context import build_context_from_wizard
from testspec.generator import ProjectGenerator


# ---------------------------------------------------------------------------
# HookRegistry 单元测试
# ---------------------------------------------------------------------------

class TestHookRegistry:
    """HookRegistry 基础功能测试。"""

    def test_register_and_fire(self) -> None:
        hooks = HookRegistry()
        called = []
        hooks.register("test_event", lambda: called.append(1))
        hooks.fire("test_event")
        assert called == [1]

    def test_fire_unregistered_event_is_noop(self) -> None:
        hooks = HookRegistry()
        # 不应抛出异常
        hooks.fire("nonexistent_event", foo="bar")

    def test_multiple_callbacks_same_event(self) -> None:
        hooks = HookRegistry()
        results = []
        hooks.register("ev", lambda: results.append("a"))
        hooks.register("ev", lambda: results.append("b"))
        hooks.fire("ev")
        assert results == ["a", "b"]

    def test_kwargs_forwarded_to_callback(self) -> None:
        hooks = HookRegistry()
        received = {}

        def callback(**kwargs: Any) -> None:
            received.update(kwargs)

        hooks.register("ev", callback)
        hooks.fire("ev", ctx={"PROJECT_NAME": "test"}, section="AI")
        assert received["ctx"]["PROJECT_NAME"] == "test"
        assert received["section"] == "AI"

    def test_unregister(self) -> None:
        hooks = HookRegistry()
        called = []

        def cb() -> None:
            called.append(1)

        hooks.register("ev", cb)
        hooks.unregister("ev", cb)
        hooks.fire("ev")
        assert called == []

    def test_unregister_nonexistent_is_noop(self) -> None:
        hooks = HookRegistry()
        # 不应抛出异常
        hooks.unregister("ev", lambda: None)

    def test_has_hooks(self) -> None:
        hooks = HookRegistry()
        assert not hooks.has_hooks("ev")
        hooks.register("ev", lambda: None)
        assert hooks.has_hooks("ev")
        assert not hooks.has_hooks("other")

    def test_clear_specific_event(self) -> None:
        hooks = HookRegistry()
        hooks.register("ev1", lambda: None)
        hooks.register("ev2", lambda: None)
        hooks.clear("ev1")
        assert not hooks.has_hooks("ev1")
        assert hooks.has_hooks("ev2")

    def test_clear_all(self) -> None:
        hooks = HookRegistry()
        hooks.register("ev1", lambda: None)
        hooks.register("ev2", lambda: None)
        hooks.clear()
        assert not hooks.has_hooks("ev1")
        assert not hooks.has_hooks("ev2")

    def test_repr(self) -> None:
        hooks = HookRegistry()
        hooks.register("ev1", lambda: None)
        hooks.register("ev2", lambda: None)
        r = repr(hooks)
        assert "HookRegistry" in r
        assert "2 hooks" in r
        assert "2 events" in r

    def test_valid_events_defined(self) -> None:
        assert "pre_generate" in VALID_EVENTS
        assert "post_section" in VALID_EVENTS
        assert "pre_atomic_move" in VALID_EVENTS
        assert "post_generate" in VALID_EVENTS

    def test_custom_event_name_allowed(self) -> None:
        """不限制事件名称，允许第三方扩展。"""
        hooks = HookRegistry()
        called = []
        hooks.register("my_custom_event", lambda: called.append(1))
        hooks.fire("my_custom_event")
        assert called == [1]


# ---------------------------------------------------------------------------
# Hook + ProjectGenerator 集成测试
# ---------------------------------------------------------------------------

class TestHookIntegration:
    """Hook 在 ProjectGenerator.generate() 中的触发测试。"""

    def _make_ctx(self, tmp_path: Path) -> Any:
        params = {
            "project_name": "hook-test",
            "test_types": ["api"],
            "language": "python",
            "framework": "pytest",
            "database": "none",
            "report_tool": "allure",
            "business_lines": ["default"],
            "output_dir": str(tmp_path / "hook-test"),
            "ci_system": "none",
            "language_locale": "zh",
        }
        return build_context_from_wizard(**params)

    def test_pre_generate_fires(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = self._make_ctx(tmp_path)
        hooks = HookRegistry()
        fired = []
        hooks.register("pre_generate", lambda **kw: fired.append(kw))

        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
        gen.generate()

        assert len(fired) == 1
        assert "ctx" in fired[0]

    def test_post_section_fires_per_section(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = self._make_ctx(tmp_path)
        hooks = HookRegistry()
        sections_fired = []
        hooks.register(
            "post_section",
            lambda **kw: sections_fired.append(kw["section"]),
        )

        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
        gen.generate()

        # 12 个 section renderers → 12 次 post_section
        assert len(sections_fired) == 12

    def test_post_generate_fires(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = self._make_ctx(tmp_path)
        hooks = HookRegistry()
        fired = []
        hooks.register("post_generate", lambda **kw: fired.append(kw))

        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
        gen.generate()

        assert len(fired) == 1
        assert "ctx" in fired[0]
        assert "generated" in fired[0]
        assert len(fired[0]["generated"]) > 0

    def test_pre_atomic_move_not_fired_in_dry_run(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = self._make_ctx(tmp_path)
        hooks = HookRegistry()
        fired = []
        hooks.register("pre_atomic_move", lambda **kw: fired.append(1))

        gen = ProjectGenerator(
            ctx, templates_dir, dry_run=True, hook_registry=hooks,
        )
        gen.generate()

        assert len(fired) == 0

    def test_pre_atomic_move_fired_in_normal_run(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        ctx = self._make_ctx(tmp_path)
        hooks = HookRegistry()
        fired = []
        hooks.register("pre_atomic_move", lambda **kw: fired.append(1))

        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
        gen.generate()

        assert len(fired) == 1

    def test_hooks_not_fired_on_exception(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        """生成异常时 post_generate 不应被触发。"""
        from testspec.sections import BaseSectionRenderer

        class FailingSection(BaseSectionRenderer):
            name = "Failing"
            def render(self, ctx, generator):
                raise RuntimeError("故意失败")

        ctx = self._make_ctx(tmp_path)
        hooks = HookRegistry()
        post_fired = []
        hooks.register("post_generate", lambda **kw: post_fired.append(1))

        gen = ProjectGenerator(
            ctx, templates_dir,
            hook_registry=hooks,
            section_renderers=[FailingSection()],
        )
        try:
            gen.generate()
        except RuntimeError:
            pass

        assert len(post_fired) == 0

    def test_default_hook_registry_is_empty(self) -> None:
        """默认创建的 HookRegistry 不注册任何回调。"""
        hooks = HookRegistry()
        assert not hooks.has_hooks("pre_generate")
        assert not hooks.has_hooks("post_generate")


# ---------------------------------------------------------------------------
# HookRegistry safe_fire 异常隔离测试 (v1.2.0)
# ---------------------------------------------------------------------------


class TestHookRegistrySafeMode:
    """HookRegistry safe_fire / fire(safe=True) 异常隔离测试。"""

    def test_failing_callback_does_not_block_subsequent(self) -> None:
        """一个回调抛出异常，后续回调仍应被执行。"""
        hooks = HookRegistry()
        results: list[str] = []

        def failing_cb(**kw: Any) -> None:
            raise RuntimeError("deliberate failure")

        hooks.register("ev", failing_cb)
        hooks.register("ev", lambda **kw: results.append("ok"))

        hooks.safe_fire("ev")
        assert results == ["ok"]

    def test_safe_fire_logs_warning(self) -> None:
        """失败的回调应产生 logging.warning。"""
        from unittest.mock import patch

        hooks = HookRegistry()

        def bad_cb(**kw: Any) -> None:
            raise ValueError("oops")

        hooks.register("ev", bad_cb)

        with patch("testspec.hooks._logger") as mock_log:
            hooks.safe_fire("ev")

        mock_log.warning.assert_called_once()

    def test_regular_fire_still_raises(self) -> None:
        """fire() 默认行为：异常向上传播（向后兼容）。"""
        hooks = HookRegistry()

        def bad_cb(**kw: Any) -> None:
            raise RuntimeError("fail")

        hooks.register("ev", bad_cb)

        with pytest.raises(RuntimeError, match="fail"):
            hooks.fire("ev")

    def test_fire_safe_true_equivalent_to_safe_fire(self) -> None:
        """fire(safe=True) 与 safe_fire() 行为相同。"""
        hooks = HookRegistry()
        results: list[int] = []

        def bad(**kw: Any) -> None:
            raise RuntimeError("x")

        hooks.register("ev", bad)
        hooks.register("ev", lambda **kw: results.append(1))

        hooks.fire("ev", safe=True)
        assert results == [1]

    def test_pre_generate_failure_still_aborts(
        self, templates_dir: Path, tmp_path: Path,
    ) -> None:
        """pre_generate hook 失败时，generate() 应抛出异常（关键事件使用 fire()）。"""
        from testspec.context import build_context_from_wizard
        from testspec.generator import ProjectGenerator

        ctx = build_context_from_wizard(
            project_name="test-proj",
            test_types=["api"],
            language="python",
            framework="pytest",
            database="none",
            report_tool="allure",
            business_lines=["default"],
            output_dir=str(tmp_path / "output"),
        )
        hooks = HookRegistry()

        def abort_cb(**kw: Any) -> None:
            raise RuntimeError("abort")

        hooks.register("pre_generate", abort_cb)

        gen = ProjectGenerator(ctx, templates_dir, hook_registry=hooks)
        with pytest.raises(RuntimeError, match="abort"):
            gen.generate()
