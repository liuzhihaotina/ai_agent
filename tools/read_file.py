from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, register_tool


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "读取指定路径文件的内容。适合查看代码、配置、文档等文本文件。"
    properties = {
        "path": {
            "type": "string",
            "description": "文件路径（相对路径或绝对路径）",
        }
    }
    required = ["path"]
    dangerous = False

    def run(self, path: str) -> str:
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


def register() -> dict:
    return register_tool(ReadFileTool)
