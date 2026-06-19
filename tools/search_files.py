from __future__ import annotations

import re
from pathlib import Path

from tools.base import BaseTool, register_tool


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "在指定目录下递归搜索文件内容，支持正则表达式。"
    properties = {
        "path": {
            "type": "string",
            "description": "要搜索的目录路径",
        },
        "regex": {
            "type": "string",
            "description": "用于匹配文件内容的正则表达式",
        },
        "file_pattern": {
            "type": "string",
            "description": "文件名匹配模式，例如 *.py",
            "default": "*",
        },
    }
    required = ["path", "regex"]
    dangerous = False

    def run(self, path: str, regex: str, file_pattern: str = "*") -> str:
        base = Path(path).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {path}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {path}"

        try:
            pattern = re.compile(regex)
        except re.error as exc:
            return f"❌ 正则表达式错误: {exc}"

        results: list[str] = []
        matched_files = 0
        matched_lines = 0

        for file_path in sorted(base.rglob(file_pattern)):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            file_hits = []
            for idx, line in enumerate(content.splitlines(), start=1):
                if pattern.search(line):
                    file_hits.append(f"{idx}: {line.strip()}")
            if file_hits:
                matched_files += 1
                matched_lines += len(file_hits)
                results.append(f"[{file_path.relative_to(base)}]")
                results.extend(file_hits[:20])
                if len(file_hits) > 20:
                    results.append(f"... 还有 {len(file_hits) - 20} 条结果")
                results.append("")

        if not results:
            return "(未找到匹配结果)"

        header = f"找到 {matched_lines} 条匹配，涉及 {matched_files} 个文件"
        return "\n".join([header, *results]).rstrip()


def register() -> dict:
    return register_tool(SearchFilesTool)
