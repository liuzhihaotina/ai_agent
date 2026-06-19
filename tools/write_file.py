from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, register_tool


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "将内容写入指定文件。如果文件不存在则创建，如果存在则覆盖。"
    properties = {
        "path": {
            "type": "string",
            "description": "文件路径",
        },
        "content": {
            "type": "string",
            "description": "要写入的文件内容",
        },
    }
    required = ["path", "content"]
    dangerous = True

    def run(self, path: str, content: str) -> str:
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"✅ 文件写入成功: {path}"
        except Exception as exc:
            return f"❌ 写入文件失败: {exc}"


def register() -> dict:
    return register_tool(WriteFileTool)
