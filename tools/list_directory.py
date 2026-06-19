from __future__ import annotations

from pathlib import Path
from typing import Any


def list_directory(path: str = ".") -> str:
    """列出目录内容。"""
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


def register() -> dict[str, Any]:
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "列出指定目录中的文件和子目录。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "目录路径，默认为当前目录",
                            }
                        },
                        "required": [],
                    },
                },
            }
        ],
        "handlers": {"list_directory": list_directory},
        "safety": {"list_directory": False},
    }
