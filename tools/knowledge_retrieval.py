from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from tools.base import BaseTool, register_tool


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".rst",
    ".csv",
    ".html",
    ".htm",
}


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{size}B"


class DirectoryKnowledgeSummaryTool(BaseTool):
    name = "directory_knowledge_summary"
    description = "生成目录知识摘要：文件分布、常见扩展名、重点文档和结构概览。"
    properties = {
        "directory": {
            "type": "string",
            "description": "要分析的目录",
        },
        "max_depth": {
            "type": "integer",
            "description": "目录树展示深度",
            "default": 2,
        },
        "max_items": {
            "type": "integer",
            "description": "每层最多展示的项目数",
            "default": 40,
        },
    }
    required = ["directory"]
    dangerous = False

    def run(self, directory: str, max_depth: int = 2, max_items: int = 40) -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        files: list[Path] = []
        dirs: list[Path] = []
        ext_counter: Counter[str] = Counter()
        total_size = 0

        for path in base.rglob("*"):
            if path.is_dir():
                dirs.append(path)
                continue
            if not path.is_file():
                continue
            files.append(path)
            total_size += path.stat().st_size
            ext_counter[path.suffix.lower() or "[no_ext]"] += 1

        files_sorted = sorted(files, key=lambda p: p.stat().st_size, reverse=True)
        important_docs = [
            p for p in files_sorted
            if p.suffix.lower() in {".md", ".txt", ".rst"} or p.name.lower().startswith(("readme", "changelog", "contributing"))
        ][:10]

        lines = [
            f"目录: {base}",
            f"文件数: {len(files)}",
            f"目录数: {len(dirs)}",
            f"总大小: {_format_size(total_size)}",
        ]

        if ext_counter:
            lines.append("\n常见扩展名:")
            for ext, count in ext_counter.most_common(10):
                lines.append(f"- {ext}: {count}")

        if important_docs:
            lines.append("\n重点文档:")
            for doc in important_docs:
                try:
                    first_line = _read_text(doc).splitlines()[0].strip() if _is_text_file(doc) and doc.stat().st_size else ""
                except Exception:
                    first_line = ""
                extra = f" — {first_line}" if first_line else ""
                lines.append(f"- {doc.relative_to(base)} ({_format_size(doc.stat().st_size)}){extra}")

        lines.append("\n目录树:")
        lines.extend(_render_tree(base, max_depth=max_depth, max_items=max_items))
        return "\n".join(lines)


class MarkdownOutlineTool(BaseTool):
    name = "markdown_outline"
    description = "提取 Markdown 文件或目录下 Markdown 文件的标题大纲。"
    properties = {
        "path": {
            "type": "string",
            "description": "Markdown 文件或目录路径",
        },
        "max_files": {
            "type": "integer",
            "description": "目录模式下最多扫描的 Markdown 文件数量",
            "default": 20,
        },
    }
    required = ["path"]
    dangerous = False

    def run(self, path: str, max_files: int = 20) -> str:
        target = Path(path).expanduser()
        if not target.exists():
            return f"❌ 错误: 路径不存在 - {path}"

        files: list[Path]
        if target.is_dir():
            files = sorted([p for p in target.rglob("*.md") if p.is_file()])[:max_files]
        else:
            if target.suffix.lower() != ".md":
                return f"❌ 错误: 不是 Markdown 文件 - {path}"
            files = [target]

        if not files:
            return "(未找到 Markdown 文件)"

        lines: list[str] = []
        for file_path in files:
            try:
                content = _read_text(file_path)
            except Exception as exc:
                lines.append(f"[{file_path}] 读取失败: {exc}")
                continue

            headings = []
            for idx, line in enumerate(content.splitlines(), start=1):
                m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
                if m:
                    level = len(m.group(1))
                    title = m.group(2).strip()
                    headings.append(f"{'  ' * (level - 1)}- L{level} {title} @ line {idx}")

            lines.append(f"[{file_path}]")
            if headings:
                lines.extend(headings)
            else:
                lines.append("- (未发现标题)")
            lines.append("")
        return "\n".join(lines).rstrip()


class DocumentKeywordSearchTool(BaseTool):
    name = "document_keyword_search"
    description = "在文档和代码中搜索关键词，并返回带上下文的命中结果。"
    properties = {
        "directory": {
            "type": "string",
            "description": "要搜索的目录",
        },
        "keyword": {
            "type": "string",
            "description": "关键词或正则表达式",
        },
        "use_regex": {
            "type": "boolean",
            "description": "是否将 keyword 视为正则表达式",
            "default": False,
        },
        "file_pattern": {
            "type": "string",
            "description": "文件匹配模式，例如 *.md",
            "default": "*",
        },
    }
    required = ["directory", "keyword"]
    dangerous = False

    def run(self, directory: str, keyword: str, use_regex: bool = False, file_pattern: str = "*") -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        try:
            pattern = re.compile(keyword if use_regex else re.escape(keyword), re.IGNORECASE)
        except re.error as exc:
            return f"❌ 正则表达式错误: {exc}"

        priority_ext = {".md", ".txt", ".rst", ".py", ".yaml", ".yml"}
        candidate_files = [p for p in base.rglob(file_pattern) if p.is_file()]
        candidate_files.sort(key=lambda p: (p.suffix.lower() not in priority_ext, str(p)))

        results: list[str] = []
        file_count = 0
        hit_count = 0
        for file_path in candidate_files:
            if not _is_text_file(file_path) and file_path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml"}:
                continue
            try:
                lines = _read_text(file_path).splitlines()
            except Exception:
                continue

            hits = []
            for idx, line in enumerate(lines, start=1):
                if pattern.search(line):
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 1)
                    context = [f"{no + 1}: {lines[no]}" for no in range(start, end)]
                    hits.append((idx, context))
            if hits:
                file_count += 1
                hit_count += len(hits)
                results.append(f"[{file_path.relative_to(base)}]")
                for idx, context in hits[:10]:
                    results.append(f"- line {idx}")
                    results.extend([f"  {ctx}" for ctx in context])
                if len(hits) > 10:
                    results.append(f"... 还有 {len(hits) - 10} 处匹配")
                results.append("")

        if not results:
            return "(未找到匹配结果)"

        header = f"找到 {hit_count} 处匹配，涉及 {file_count} 个文件"
        return "\n".join([header, *results]).rstrip()


def _render_tree(base: Path, max_depth: int = 2, max_items: int = 40) -> list[str]:
    entries = []
    for item in sorted(base.rglob("*")):
        try:
            rel = item.relative_to(base)
        except Exception:
            continue
        depth = len(rel.parts)
        if depth > max_depth:
            continue
        entries.append((rel, item.is_dir()))
        if len(entries) >= max_items:
            break

    if not entries:
        return ["(空目录)"]

    lines: list[str] = []
    for rel, is_dir in entries:
        indent = "  " * (len(rel.parts) - 1)
        suffix = "/" if is_dir else ""
        lines.append(f"{indent}- {rel.name}{suffix}")
    if len(list(base.rglob("*"))) > len(entries):
        lines.append("...")
    return lines


def register() -> dict[str, Any]:
    tools = [
        DirectoryKnowledgeSummaryTool.schema(),
        MarkdownOutlineTool.schema(),
        DocumentKeywordSearchTool.schema(),
    ]
    handlers = {
        DirectoryKnowledgeSummaryTool.name: DirectoryKnowledgeSummaryTool().run,
        MarkdownOutlineTool.name: MarkdownOutlineTool().run,
        DocumentKeywordSearchTool.name: DocumentKeywordSearchTool().run,
    }
    safety = {
        DirectoryKnowledgeSummaryTool.name: DirectoryKnowledgeSummaryTool.dangerous,
        MarkdownOutlineTool.name: MarkdownOutlineTool.dangerous,
        DocumentKeywordSearchTool.name: DocumentKeywordSearchTool.dangerous,
    }
    return {"tools": tools, "handlers": handlers, "safety": safety}
