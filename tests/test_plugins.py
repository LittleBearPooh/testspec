"""testspec.plugins 模块测试。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from testspec.plugins import discover_plugins, load_plugin_renderers
from testspec.sections import BaseSectionRenderer


class _MockSection(BaseSectionRenderer):
    """测试用 Section Renderer。"""
    name = "mock-section"

    def render(self, ctx, generator):  # type: ignore[override]
        pass


class _BrokenSection(BaseSectionRenderer):
    """实例化时抛异常的 Section。"""
    name = "broken"

    def __init__(self) -> None:
        raise ValueError("cannot instantiate")

    def render(self, ctx, generator):  # type: ignore[override]
        pass


# ---------------------------------------------------------------------------
# discover_plugins 测试
# ---------------------------------------------------------------------------


class TestDiscoverPlugins:
    """discover_plugins() 单元测试。"""

    def test_no_plugins_returns_empty_list(self) -> None:
        """无插件时返回空列表。"""
        with patch("testspec.plugins.entry_points", return_value=[]):
            result = discover_plugins()
        assert result == []

    def test_loads_plugin_class(self) -> None:
        """成功加载单个插件类。"""
        mock_ep = MagicMock()
        mock_ep.load.return_value = _MockSection
        mock_ep.name = "mock_section"
        mock_ep.value = "mock_pkg.module:MockSection"

        with patch("testspec.plugins.entry_points", return_value=[mock_ep]):
            result = discover_plugins()

        assert result == [_MockSection]

    def test_failing_plugin_load_is_skipped(self) -> None:
        """加载失败的 entry_point 应被跳过，不影响其他插件。"""
        bad_ep = MagicMock()
        bad_ep.load.side_effect = ImportError("module not found")
        bad_ep.name = "bad_plugin"

        good_ep = MagicMock()
        good_ep.load.return_value = _MockSection
        good_ep.name = "good_plugin"
        good_ep.value = "pkg:MockSection"

        with patch("testspec.plugins.entry_points", return_value=[bad_ep, good_ep]):
            result = discover_plugins()

        assert result == [_MockSection]

    def test_failing_plugin_logs_warning(self) -> None:
        """加载失败的插件应产生 WARNING 日志。"""
        bad_ep = MagicMock()
        bad_ep.load.side_effect = ImportError("fail")
        bad_ep.name = "bad_plugin"

        with patch("testspec.plugins.entry_points", return_value=[bad_ep]):
            with patch("testspec.plugins._logger") as mock_log:
                discover_plugins()

        mock_log.warning.assert_called_once()

    def test_custom_group_name(self) -> None:
        """自定义 group 参数应传递给 entry_points。"""
        with patch("testspec.plugins.entry_points", return_value=[]) as mock_ep:
            discover_plugins(group="my.custom.group")
        mock_ep.assert_called_once_with(group="my.custom.group")


# ---------------------------------------------------------------------------
# load_plugin_renderers 测试
# ---------------------------------------------------------------------------


class TestLoadPluginRenderers:
    """load_plugin_renderers() 实例化测试。"""

    def test_returns_instances(self) -> None:
        """返回正确实例化的 BaseSectionRenderer 对象。"""
        mock_ep = MagicMock()
        mock_ep.load.return_value = _MockSection
        mock_ep.name = "mock_section"
        mock_ep.value = "pkg:MockSection"

        with patch("testspec.plugins.entry_points", return_value=[mock_ep]):
            renderers = load_plugin_renderers()

        assert len(renderers) == 1
        assert isinstance(renderers[0], _MockSection)
        assert isinstance(renderers[0], BaseSectionRenderer)

    def test_instantiation_failure_is_skipped(self) -> None:
        """实例化失败的插件被跳过。"""
        mock_ep = MagicMock()
        mock_ep.load.return_value = _BrokenSection
        mock_ep.name = "broken_section"
        mock_ep.value = "pkg:BrokenSection"

        with patch("testspec.plugins.entry_points", return_value=[mock_ep]):
            renderers = load_plugin_renderers()

        assert renderers == []

    def test_no_plugins_returns_empty(self) -> None:
        """无插件时返回空列表。"""
        with patch("testspec.plugins.entry_points", return_value=[]):
            result = load_plugin_renderers()
        assert result == []
