from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, register_tool


class BatchFilePreviewTool(BaseTool):
    name = "batch_file_preview"
    description = "批量预览目录中的文本文件，输出前几行内容。"
    properties = {
        "directory": {
            "type": "string",
            "description": "要预览的目录",
        },
        "file_pattern": {
            "type": "string",
            "description": "文件匹配模式，例如 *.md",
            "default": "*",
        },
        "max_files": {
            "type": "integer",
            "description": "最多预览的文件数量",
            "default": 20,
        },
        "head_lines": {
            "type": "integer",
            "description": "每个文件输出的前几行",
            "default": 5,
        },
    }
    required = ["directory"]
    dangerous = False

    def run(self, directory: str, file_pattern: str = "*", max_files: int = 20, head_lines: int = 5) -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        files = [p for p in base.rglob(file_pattern) if p.is_file()]
        files.sort()
        if not files:
            return "(未找到文件)"

        lines: list[str] = []
        count = 0
        for file_path in files:
            if count >= max_files:
                break
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            preview = text.splitlines()[:head_lines]
            lines.append(f"[{file_path.relative_to(base)}]")
            if preview:
                for idx, line in enumerate(preview, start=1):
                    lines.append(f"{idx}: {line}")
            else:
                lines.append("(空文件)")
            lines.append("")
            count += 1

        if not lines:
            return "(没有可预览的文本文件)"
        if len(files) > count:
            lines.append(f"... 还有 {len(files) - count} 个文件未显示")
        return "\n".join(lines).rstrip()


def register() -> dict:
    return register_tool(BatchFilePreviewTool)
