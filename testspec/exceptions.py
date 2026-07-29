"""TestSpec 自定义异常层次。

所有 TestSpec 特有异常继承自 TestSpecError，
方便调用方精确捕获框架级错误。

向后兼容策略：
  - ConfigError 同时继承 ValueError，现有 except ValueError 代码不受影响
  - GenerationError 同时继承 RuntimeError，现有 except RuntimeError 代码不受影响
"""

from __future__ import annotations

__all__ = [
    "TestSpecError",
    "ConfigError",
    "TemplateError",
    "GenerationError",
    "ValidationError",
]


class TestSpecError(Exception):
    """TestSpec 框架基础异常。"""
    __test__ = False  # 防止 pytest 将此类误收集为测试类


class ConfigError(TestSpecError, ValueError):
    """配置相关错误（无效参数、格式错误、JSON 解析失败等）。

    同时继承 ValueError 以保持向后兼容。
    """


class TemplateError(TestSpecError):
    """模板渲染错误。

    Attributes:
        source_path: 模板文件路径
        context_key: 关联的上下文键名
        line_number: 错误所在行号（1-based）
    """

    def __init__(
        self,
        message: str,
        *,
        source_path: str | None = None,
        context_key: str | None = None,
        line_number: int | None = None,
    ) -> None:
        self.source_path = source_path
        self.context_key = context_key
        self.line_number = line_number
        loc = f" in {source_path}" if source_path else ""
        line = f" line {line_number}" if line_number else ""
        key = f" (key: {context_key})" if context_key else ""
        super().__init__(f"TemplateError{loc}{line}{key}: {message}")


class GenerationError(TestSpecError, RuntimeError):
    """项目生成过程中的错误（IO/权限/编码等）。

    同时继承 RuntimeError 以保持向后兼容。
    """


class ValidationError(TestSpecError, ValueError):
    """项目完整性校验相关错误。

    用于 ProjectValidator 检测到必需文件缺失或格式错误时抛出。
    同时继承 ValueError 以保持向后兼容。
    """
