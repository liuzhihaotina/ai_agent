from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, register_tool


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "列出指定目录中的文件和子目录。"
    properties = {
        "path": {
            "type": "string",
            "description": "目录路径，默认为当前目录",
        }
    }
    required = []
    dangerous = False

    def run(self, path: str = ".") -> str:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return f"❌ 错误: 目录不存在 - {path}"
            if not p.is_dir():
                return f"❌ 错误: 路径不是目录 - {path}"

            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            lines = []
            for item in items:
                prefix = "📁" if item.is_dir() else "📄"
                lines.append(f"  {prefix} {item.name}")
            return "\n".join(lines) if lines else "(空目录)"
        except Exception as exc:
            return f"❌ 列出目录失败: {exc}"


def register() -> dict:
    return register_tool(ListDirectoryTool)
