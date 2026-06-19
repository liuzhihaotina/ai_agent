from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from tools.base import BaseTool, register_tool


class GitToolBase(BaseTool):
    repo_path: str = "."

    @staticmethod
    def _run_git(args: list[str], cwd: str | None = None) -> tuple[int, str]:
        try:
            result = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                cwd=cwd or None,
                timeout=30,
            )
            output = (result.stdout or "") + (f"\n{result.stderr}" if result.stderr else "")
            return result.returncode, output.strip()
        except subprocess.TimeoutExpired:
            return 1, "❌ Git 命令执行超时"
        except FileNotFoundError:
            return 1, "❌ 未找到 git 命令"
        except Exception as exc:
            return 1, f"❌ Git 执行失败: {exc}"


class GitStatusTool(GitToolBase):
    name = "git_status"
    description = "查看 Git 仓库当前状态。"
    properties = {
        "repo_path": {
            "type": "string",
            "description": "Git 仓库路径，默认为当前目录",
            "default": ".",
        }
    }
    required = []
    dangerous = False

    def run(self, repo_path: str = ".") -> str:
        code, output = self._run_git(["status", "--short", "--branch"], cwd=repo_path)
        return output if code == 0 else output


class GitBranchInfoTool(GitToolBase):
    name = "git_branch_info"
    description = "查看当前分支与远程分支信息。"
    properties = {
        "repo_path": {
            "type": "string",
            "description": "Git 仓库路径，默认为当前目录",
            "default": ".",
        }
    }
    required = []
    dangerous = False

    def run(self, repo_path: str = ".") -> str:
        parts = []
        code, branch = self._run_git(["branch", "--show-current"], cwd=repo_path)
        if code == 0 and branch:
            parts.append(f"当前分支: {branch}")

        code, remote = self._run_git(["remote", "-v"], cwd=repo_path)
        if code == 0 and remote:
            parts.append("远程信息:")
            parts.append(remote)

        code, upstream = self._run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=repo_path)
        if code == 0 and upstream:
            parts.append(f"上游分支: {upstream}")

        if not parts:
            return "(未能获取分支信息)"
        return "\n".join(parts)


class GitRecentCommitsTool(GitToolBase):
    name = "git_recent_commits"
    description = "查看最近的 Git 提交记录。"
    properties = {
        "repo_path": {
            "type": "string",
            "description": "Git 仓库路径，默认为当前目录",
            "default": ".",
        },
        "limit": {
            "type": "integer",
            "description": "显示的提交数量",
            "default": 10,
        },
    }
    required = []
    dangerous = False

    def run(self, repo_path: str = ".", limit: int = 10) -> str:
        code, output = self._run_git(
            ["log", f"-n{limit}", "--oneline", "--decorate", "--graph"],
            cwd=repo_path,
        )
        return output if code == 0 else output


class GitDiffSummaryTool(GitToolBase):
    name = "git_diff_summary"
    description = "查看当前工作区相对于 HEAD 的差异摘要。"
    properties = {
        "repo_path": {
            "type": "string",
            "description": "Git 仓库路径，默认为当前目录",
            "default": ".",
        },
        "cached": {
            "type": "boolean",
            "description": "是否查看暂存区差异",
            "default": False,
        },
    }
    required = []
    dangerous = False

    def run(self, repo_path: str = ".", cached: bool = False) -> str:
        args = ["diff", "--stat"]
        if cached:
            args.insert(1, "--cached")
        code, output = self._run_git(args, cwd=repo_path)
        if code != 0:
            return output
        if not output:
            return "(当前没有差异)"
        return output


def register() -> dict[str, Any]:
    tools = [
        GitStatusTool.schema(),
        GitBranchInfoTool.schema(),
        GitRecentCommitsTool.schema(),
        GitDiffSummaryTool.schema(),
    ]
    handlers = {
        GitStatusTool.name: GitStatusTool().run,
        GitBranchInfoTool.name: GitBranchInfoTool().run,
        GitRecentCommitsTool.name: GitRecentCommitsTool().run,
        GitDiffSummaryTool.name: GitDiffSummaryTool().run,
    }
    safety = {
        GitStatusTool.name: GitStatusTool.dangerous,
        GitBranchInfoTool.name: GitBranchInfoTool.dangerous,
        GitRecentCommitsTool.name: GitRecentCommitsTool.dangerous,
        GitDiffSummaryTool.name: GitDiffSummaryTool.dangerous,
    }
    return {"tools": tools, "handlers": handlers, "safety": safety}
