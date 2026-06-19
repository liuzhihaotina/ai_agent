from __future__ import annotations

import subprocess
from typing import Any


def execute_command(command: str, working_dir: str | None = None) -> str:
    """执行终端命令。"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=working_dir if working_dir else None,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[返回码: {result.returncode}]"
        return output.strip() if output.strip() else "(无输出)"
    except subprocess.TimeoutExpired:
        return "❌ 命令执行超时 (120秒)"
    except Exception as exc:
        return f"❌ 命令执行失败: {exc}"


def register() -> dict[str, Any]:
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "在终端中执行 shell 命令并返回输出结果。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的 shell 命令",
                            },
                            "working_dir": {
                                "type": "string",
                                "description": "工作目录（可选，默认为当前目录）",
                            },
                        },
                        "required": ["command"],
                    },
                },
            }
        ],
        "handlers": {"execute_command": execute_command},
        "safety": {"execute_command": True},
    }
