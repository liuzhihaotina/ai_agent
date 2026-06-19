from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, register_tool


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "精确替换文件中的指定内容。将 old_text 替换为 new_text。"
    properties = {
        "path": {
            "type": "string",
            "description": "文件路径",
        },
        "old_text": {
            "type": "string",
            "description": "要被替换的原始文本（必须精确匹配）",
        },
        "new_text": {
            "type": "string",
            "description": "替换后的新文本",
        },
    }
    required = ["path", "old_text", "new_text"]
    dangerous = True

    def run(self, path: str, old_text: str, new_text: str) -> str:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return f"❌ 错误: 文件不存在 - {path}"
            content = p.read_text(encoding="utf-8")
            if old_text not in content:
                return "❌ 错误: 未在文件中找到要替换的文本"
            new_content = content.replace(old_text, new_text, 1)
            p.write_text(new_content, encoding="utf-8")
            return f"✅ 文件编辑成功: {path}"
        except Exception as exc:
            return f"❌ 编辑文件失败: {exc}"


def register() -> dict:
    return register_tool(EditFileTool)
