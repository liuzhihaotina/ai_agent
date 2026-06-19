from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from tools.base import BaseTool, register_tool


class CopyFileTool(BaseTool):
    name = "copy_file"
    description = "复制文件或目录到目标路径。"
    properties = {
        "source": {
            "type": "string",
            "description": "源文件或目录路径",
        },
        "destination": {
            "type": "string",
            "description": "目标路径",
        },
        "overwrite": {
            "type": "boolean",
            "description": "目标已存在时是否覆盖",
            "default": False,
        },
    }
    required = ["source", "destination"]
    dangerous = True

    def run(self, source: str, destination: str, overwrite: bool = False) -> str:
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()

        if not src.exists():
            return f"❌ 错误: 源路径不存在 - {source}"

        try:
            if src.is_dir():
                if dst.exists() and overwrite:
                    if dst.is_file():
                        dst.unlink()
                    else:
                        shutil.rmtree(dst)
                if dst.exists():
                    return f"❌ 错误: 目标路径已存在 - {destination}"
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists() and not overwrite:
                    return f"❌ 错误: 目标文件已存在 - {destination}"
                shutil.copy2(src, dst)
            return f"✅ 复制成功: {source} -> {destination}"
        except Exception as exc:
            return f"❌ 复制失败: {exc}"


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "移动文件或目录到目标路径。"
    properties = {
        "source": {
            "type": "string",
            "description": "源文件或目录路径",
        },
        "destination": {
            "type": "string",
            "description": "目标路径",
        },
        "overwrite": {
            "type": "boolean",
            "description": "目标已存在时是否覆盖",
            "default": False,
        },
    }
    required = ["source", "destination"]
    dangerous = True

    def run(self, source: str, destination: str, overwrite: bool = False) -> str:
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()

        if not src.exists():
            return f"❌ 错误: 源路径不存在 - {source}"

        try:
            if dst.exists():
                if not overwrite:
                    return f"❌ 错误: 目标路径已存在 - {destination}"
                if dst.is_file() or dst.is_symlink():
                    dst.unlink()
                else:
                    shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"✅ 移动成功: {source} -> {destination}"
        except Exception as exc:
            return f"❌ 移动失败: {exc}"


class DeletePathTool(BaseTool):
    name = "delete_path"
    description = "删除文件或目录。目录删除支持递归。"
    properties = {
        "path": {
            "type": "string",
            "description": "要删除的文件或目录路径",
        },
        "recursive": {
            "type": "boolean",
            "description": "删除目录时是否递归删除",
            "default": False,
        },
    }
    required = ["path"]
    dangerous = True

    def run(self, path: str, recursive: bool = False) -> str:
        target = Path(path).expanduser()
        if not target.exists():
            return f"❌ 错误: 路径不存在 - {path}"

        try:
            if target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                else:
                    target.rmdir()
            else:
                target.unlink()
            return f"✅ 删除成功: {path}"
        except OSError as exc:
            return f"❌ 删除失败: {exc}"
        except Exception as exc:
            return f"❌ 删除失败: {exc}"


class BatchRenameTool(BaseTool):
    name = "batch_rename"
    description = "批量重命名目录中的文件或目录，支持字符串替换和正则替换。"
    properties = {
        "directory": {
            "type": "string",
            "description": "待处理目录",
        },
        "old_text": {
            "type": "string",
            "description": "要替换的旧文本或正则表达式",
        },
        "new_text": {
            "type": "string",
            "description": "替换后的新文本",
        },
        "use_regex": {
            "type": "boolean",
            "description": "是否将 old_text 视为正则表达式",
            "default": False,
        },
        "recursive": {
            "type": "boolean",
            "description": "是否递归处理子目录",
            "default": False,
        },
        "include_directories": {
            "type": "boolean",
            "description": "是否也重命名目录",
            "default": False,
        },
        "dry_run": {
            "type": "boolean",
            "description": "是否只预览不实际修改",
            "default": True,
        },
    }
    required = ["directory", "old_text", "new_text"]
    dangerous = True

    def run(
        self,
        directory: str,
        old_text: str,
        new_text: str,
        use_regex: bool = False,
        recursive: bool = False,
        include_directories: bool = False,
        dry_run: bool = True,
    ) -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        try:
            if use_regex:
                pattern = re.compile(old_text)
                rename_func = lambda name: pattern.sub(new_text, name)
            else:
                rename_func = lambda name: name.replace(old_text, new_text)
        except re.error as exc:
            return f"❌ 正则表达式错误: {exc}"

        candidates = list(base.rglob("*")) if recursive else list(base.iterdir())
        if include_directories:
            rename_targets = [p for p in candidates if p.exists() and p != base]
        else:
            rename_targets = [p for p in candidates if p.is_file()]

        # 先按路径深度倒序，避免先改父目录导致子项路径失效
        rename_targets.sort(key=lambda p: len(p.parts), reverse=True)

        operations: list[str] = []
        conflicts: list[str] = []
        for item in rename_targets:
            new_name = rename_func(item.name)
            if new_name == item.name:
                continue
            target = item.with_name(new_name)
            if target.exists() and target != item:
                conflicts.append(f"{item} -> {target}")
                continue
            operations.append(f"{item} -> {target}")
            if not dry_run:
                item.rename(target)

        if not operations and not conflicts:
            return "(没有需要重命名的项目)"

        lines = []
        lines.append(f"{'预览' if dry_run else '执行'}完成，共 {len(operations)} 个重命名候选")
        if operations:
            lines.append("重命名列表:")
            lines.extend([f"- {line}" for line in operations[:100]])
            if len(operations) > 100:
                lines.append(f"... 还有 {len(operations) - 100} 项")
        if conflicts:
            lines.append("")
            lines.append("冲突跳过:")
            lines.extend([f"- {line}" for line in conflicts[:50]])
            if len(conflicts) > 50:
                lines.append(f"... 还有 {len(conflicts) - 50} 项")
        return "\n".join(lines)


def register() -> dict[str, Any]:
    tools = [
        CopyFileTool.schema(),
        MoveFileTool.schema(),
        DeletePathTool.schema(),
        BatchRenameTool.schema(),
    ]
    handlers = {
        CopyFileTool.name: CopyFileTool().run,
        MoveFileTool.name: MoveFileTool().run,
        DeletePathTool.name: DeletePathTool().run,
        BatchRenameTool.name: BatchRenameTool().run,
    }
    safety = {
        CopyFileTool.name: CopyFileTool.dangerous,
        MoveFileTool.name: MoveFileTool.dangerous,
        DeletePathTool.name: DeletePathTool.dangerous,
        BatchRenameTool.name: BatchRenameTool.dangerous,
    }
    return {"tools": tools, "handlers": handlers, "safety": safety}
