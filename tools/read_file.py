from __future__ import annotations

from pathlib import Path
from typing import Any


def read_file(path: str) -> str:
    """读取文件内容。"""
    p = Path(path).expanduser()
    if not p.exists():
        return f"❌ 错误: 文件不存在 - {path}"
    if not p.is_file():
        return f"❌ 错误: 路径不是文件 - {path}"
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return f"❌ 读取文件失败: {exc}"


def register() -> dict[str, Any]:
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取指定路径文件的内容。适合查看代码、配置、文档等文本文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径（相对路径或绝对路径）",
                            }
                        },
                        "required": ["path"],
                    },
                },
            }
        ],
        "handlers": {"read_file": read_file},
        "safety": {"read_file": False},
    }
