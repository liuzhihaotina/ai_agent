from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.base import BaseTool, register_tool


@dataclass
class FunctionInfo:
    name: str
    lineno: int
    args: list[str]
    docstring: str | None


@dataclass
class ClassInfo:
    name: str
    lineno: int
    bases: list[str]
    docstring: str | None
    methods: list[FunctionInfo]


class PythonAnalysis:
    @staticmethod
    def safe_read(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def extract_python_file(path: Path) -> dict[str, Any]:
        source = PythonAnalysis.safe_read(path)
        tree = ast.parse(source, filename=str(path))

        imports: list[str] = []
        classes: list[ClassInfo] = []
        functions: list[FunctionInfo] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name if alias.asname is None else f"{alias.name} as {alias.asname}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    name = alias.name if alias.asname is None else f"{alias.name} as {alias.asname}"
                    imports.append(f"from {mod} import {name}")
            elif isinstance(node, ast.FunctionDef):
                functions.append(
                    FunctionInfo(
                        name=node.name,
                        lineno=node.lineno,
                        args=[arg.arg for arg in node.args.args],
                        docstring=ast.get_docstring(node),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                methods: list[FunctionInfo] = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(
                            FunctionInfo(
                                name=item.name,
                                lineno=item.lineno,
                                args=[arg.arg for arg in item.args.args],
                                docstring=ast.get_docstring(item),
                            )
                        )
                classes.append(
                    ClassInfo(
                        name=node.name,
                        lineno=node.lineno,
                        bases=[ast.unparse(base) for base in node.bases] if node.bases else [],
                        docstring=ast.get_docstring(node),
                        methods=methods,
                    )
                )

        return {
            "path": str(path),
            "imports": imports,
            "functions": [
                {
                    "name": item.name,
                    "lineno": item.lineno,
                    "args": item.args,
                    "docstring": item.docstring,
                }
                for item in functions
            ],
            "classes": [
                {
                    "name": item.name,
                    "lineno": item.lineno,
                    "bases": item.bases,
                    "docstring": item.docstring,
                    "methods": [
                        {
                            "name": method.name,
                            "lineno": method.lineno,
                            "args": method.args,
                            "docstring": method.docstring,
                        }
                        for method in item.methods
                    ],
                }
                for item in classes
            ],
        }

    @staticmethod
    def scan_directory(directory: Path, file_pattern: str = "*.py") -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for file_path in sorted(directory.rglob(file_pattern)):
            if not file_path.is_file():
                continue
            try:
                results.append(PythonAnalysis.extract_python_file(file_path))
            except SyntaxError as exc:
                results.append(
                    {
                        "path": str(file_path),
                        "error": f"语法错误: {exc}",
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "path": str(file_path),
                        "error": str(exc),
                    }
                )
        return results

    @staticmethod
    def find_symbol_usages(directory: Path, symbol: str, file_pattern: str = "*.py") -> list[dict[str, Any]]:
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
        results: list[dict[str, Any]] = []
        for file_path in sorted(directory.rglob(file_pattern)):
            if not file_path.is_file():
                continue
            try:
                lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue

            matches = []
            for idx, line in enumerate(lines, start=1):
                if pattern.search(line):
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 1)
                    context = []
                    for line_no in range(start, end):
                        context.append(f"{line_no + 1}: {lines[line_no]}")
                    matches.append({"line": idx, "context": context})
            if matches:
                results.append({"path": str(file_path), "matches": matches})
        return results


class AnalyzePythonFileTool(BaseTool):
    name = "analyze_python_file"
    description = "分析单个 Python 文件，提取导入、函数、类、方法和文档字符串。"
    properties = {
        "path": {
            "type": "string",
            "description": "Python 文件路径",
        }
    }
    required = ["path"]
    dangerous = False

    def run(self, path: str) -> str:
        p = Path(path).expanduser()
        if not p.exists():
            return f"❌ 错误: 文件不存在 - {path}"
        if not p.is_file():
            return f"❌ 错误: 路径不是文件 - {path}"
        try:
            data = PythonAnalysis.extract_python_file(p)
            return _format_python_analysis(data)
        except SyntaxError as exc:
            return f"❌ Python 语法错误: {exc}"
        except Exception as exc:
            return f"❌ 分析失败: {exc}"


class ScanPythonDefinitionsTool(BaseTool):
    name = "scan_python_definitions"
    description = "扫描目录下的 Python 文件，汇总函数和类定义。"
    properties = {
        "directory": {
            "type": "string",
            "description": "要扫描的目录",
        },
        "file_pattern": {
            "type": "string",
            "description": "文件匹配模式，例如 *.py",
            "default": "*.py",
        },
    }
    required = ["directory"]
    dangerous = False

    def run(self, directory: str, file_pattern: str = "*.py") -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        try:
            results = PythonAnalysis.scan_directory(base, file_pattern=file_pattern)
            return _format_directory_scan(results)
        except Exception as exc:
            return f"❌ 扫描失败: {exc}"


class FindSymbolUsagesTool(BaseTool):
    name = "find_symbol_usages"
    description = "在目录中查找某个符号的代码出现位置，并返回上下文。"
    properties = {
        "directory": {
            "type": "string",
            "description": "要搜索的目录",
        },
        "symbol": {
            "type": "string",
            "description": "要查找的符号名称",
        },
        "file_pattern": {
            "type": "string",
            "description": "文件匹配模式，例如 *.py",
            "default": "*.py",
        },
    }
    required = ["directory", "symbol"]
    dangerous = False

    def run(self, directory: str, symbol: str, file_pattern: str = "*.py") -> str:
        base = Path(directory).expanduser()
        if not base.exists():
            return f"❌ 错误: 目录不存在 - {directory}"
        if not base.is_dir():
            return f"❌ 错误: 路径不是目录 - {directory}"

        try:
            results = PythonAnalysis.find_symbol_usages(base, symbol, file_pattern=file_pattern)
            return _format_symbol_usages(symbol, results)
        except Exception as exc:
            return f"❌ 查找失败: {exc}"


def _format_python_analysis(data: dict[str, Any]) -> str:
    lines = [f"文件: {data['path']}"]

    imports = data.get("imports", [])
    if imports:
        lines.append("\n导入:")
        lines.extend([f"- {item}" for item in imports])

    classes = data.get("classes", [])
    if classes:
        lines.append("\n类定义:")
        for cls in classes:
            bases = f"({', '.join(cls['bases'])})" if cls.get("bases") else ""
            lines.append(f"- class {cls['name']}{bases} @ line {cls['lineno']}")
            if cls.get("docstring"):
                lines.append(f"  doc: {cls['docstring']}")
            methods = cls.get("methods", [])
            for method in methods:
                args = ", ".join(method.get("args", []))
                lines.append(f"  - def {method['name']}({args}) @ line {method['lineno']}")

    functions = data.get("functions", [])
    if functions:
        lines.append("\n函数定义:")
        for func in functions:
            args = ", ".join(func.get("args", []))
            lines.append(f"- def {func['name']}({args}) @ line {func['lineno']}")
            if func.get("docstring"):
                lines.append(f"  doc: {func['docstring']}")

    if len(lines) == 1:
        lines.append("(未发现函数或类定义)")

    return "\n".join(lines)


def _format_directory_scan(results: list[dict[str, Any]]) -> str:
    if not results:
        return "(未找到任何 Python 文件)"

    lines: list[str] = []
    for item in results:
        lines.append(f"[{item['path']}]")
        if "error" in item:
            lines.append(f"  ❌ {item['error']}")
            lines.append("")
            continue

        classes = item.get("classes", [])
        functions = item.get("functions", [])
        if classes:
            lines.append("  类:")
            for cls in classes:
                lines.append(f"    - {cls['name']} @ line {cls['lineno']}")
        if functions:
            lines.append("  函数:")
            for func in functions:
                lines.append(f"    - {func['name']} @ line {func['lineno']}")
        if not classes and not functions:
            lines.append("  (未发现定义)")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_symbol_usages(symbol: str, results: list[dict[str, Any]]) -> str:
    if not results:
        return f"(未找到符号: {symbol})"

    lines = [f"符号: {symbol}"]
    for item in results:
        lines.append(f"[{item['path']}]")
        for match in item.get("matches", [])[:20]:
            lines.append(f"  - line {match['line']}")
            lines.extend([f"    {ctx}" for ctx in match.get("context", [])])
        if len(item.get("matches", [])) > 20:
            lines.append(f"  ... 还有 {len(item['matches']) - 20} 处匹配")
        lines.append("")
    return "\n".join(lines).rstrip()


def register() -> dict[str, Any]:
    tools = [
        AnalyzePythonFileTool.schema(),
        ScanPythonDefinitionsTool.schema(),
        FindSymbolUsagesTool.schema(),
    ]
    handlers = {
        AnalyzePythonFileTool.name: AnalyzePythonFileTool().run,
        ScanPythonDefinitionsTool.name: ScanPythonDefinitionsTool().run,
        FindSymbolUsagesTool.name: FindSymbolUsagesTool().run,
    }
    safety = {
        AnalyzePythonFileTool.name: AnalyzePythonFileTool.dangerous,
        ScanPythonDefinitionsTool.name: ScanPythonDefinitionsTool.dangerous,
        FindSymbolUsagesTool.name: FindSymbolUsagesTool.dangerous,
    }
    return {"tools": tools, "handlers": handlers, "safety": safety}
