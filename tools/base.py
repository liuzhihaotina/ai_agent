from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """工具模板基类。

    子类只需要定义元数据和实现 run()，无需重复编写 schema 构造逻辑。
    """

    name: str = ""
    description: str = ""
    properties: dict[str, Any] = {}
    required: list[str] = []
    dangerous: bool = False

    @classmethod
    def schema(cls) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": {
                    "type": "object",
                    "properties": cls.properties,
                    "required": cls.required,
                },
            },
        }

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """执行工具逻辑。"""

    @classmethod
    def register(cls) -> dict[str, Any]:
        instance = cls()
        return {
            "tools": [cls.schema()],
            "handlers": {cls.name: instance.run},
            "safety": {cls.name: cls.dangerous},
        }


def register_tool(tool_cls: type[BaseTool]) -> dict[str, Any]:
    """将 BaseTool 子类转换为 Agent 可加载的插件字典。"""
    return tool_cls.register()
