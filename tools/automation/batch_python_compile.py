from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool, register_tool


class BatchPythonCompileTool(BaseTool):
    name = "batch_python_compile"
    description = "批量检查目录下 Python 文件的语法是否可通过编译。"
    properties = {
        "directory": {
            "type": "string",
            "description": "要检查的目录",
        },
        "file_pattern": {
            "type": "string",
            "description": "文件匹配模式，例如 *.py",
            "default": "*.py",
        },
        "max_files": {
            "type": "integer",
            "description": "最多检查的文件数量",
            "default": 200,
        },
    }
    required = ["directory"]
    dangerous = False

    def run(self, directory: str, file_pattern: str = "*.py", max_files: int = 200) -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        files = [p for p in base.rglob(file_pattern) if p.is_file()]
        files.sort()
        files = files[:max_files]
        if not files:
            return "(未找到 Python 文件)"

        import py_compile

        ok_count = 0
        failed: list[str] = []
        for file_path in files:
            try:
                py_compile.compile(str(file_path), doraise=True)
                ok_count += 1
            except Exception as exc:
                failed.append(f"{file_path.relative_to(base)}: {exc}")

        lines = [f"检查文件数: {len(files)}", f"通过: {ok_count}", f"失败: {len(failed)}"]
        if failed:
            lines.append("\n失败列表:")
            lines.extend([f"- {item}" for item in failed[:50]])
            if len(failed) > 50:
                lines.append(f"... 还有 {len(failed) - 50} 项")
        return "\n".join(lines)


def register() -> dict:
    return register_tool(BatchPythonCompileTool)
