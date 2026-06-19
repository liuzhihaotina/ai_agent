from __future__ import annotations

from pathlib import Path
from typing import Any


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """按精确文本替换方式编辑文件。"""
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


def register() -> dict[str, Any]:
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "精确替换文件中的指定内容。将 old_text 替换为 new_text。",
                    "parameters": {
                        "type": "object",
                        "properties": {
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
                        },
                        "required": ["path", "old_text", "new_text"],
                    },
                },
            }
        ],
        "handlers": {"edit_file": edit_file},
        "safety": {"edit_file": True},
    }
