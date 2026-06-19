from __future__ import annotations

import platform
import sys
from pathlib import Path

from tools.base import BaseTool, register_tool


class EnvironmentSnapshotTool(BaseTool):
    name = "environment_snapshot"
    description = "采集当前运行环境快照，包括 Python、系统和工作目录信息。"
    properties = {
        "include_path": {
            "type": "boolean",
            "description": "是否包含部分 Python 路径信息",
            "default": True,
        }
    }
    required = []
    dangerous = False

    def run(self, include_path: bool = True) -> str:
        lines = [
            f"Python: {sys.version.split()[0]}",
            f"Executable: {sys.executable}",
            f"Platform: {platform.platform()}",
            f"Machine: {platform.machine()}",
            f"Processor: {platform.processor() or '(unknown)'}",
            f"Current Working Directory: {Path.cwd()}",
        ]
        if include_path:
            lines.append("\nPython Path:")
            lines.extend([f"- {p}" for p in sys.path[:20]])
            if len(sys.path) > 20:
                lines.append(f"... 还有 {len(sys.path) - 20} 项")
        return "\n".join(lines)


def register() -> dict:
    return register_tool(EnvironmentSnapshotTool)
