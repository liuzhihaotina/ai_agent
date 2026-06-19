#!/usr/bin/env python3
"""AI Agent - 模块化可插拔版本。

每个能力都以独立工具模块的形式放在 tools/ 目录下，
新增、删除、替换工具模块时，无需修改 agent.py。
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


# ============================================================
# 配置加载
# ============================================================


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """加载配置文件，支持环境变量覆盖。"""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"

    config: dict[str, Any] = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # 环境变量优先级更高
    config["base_url"] = os.environ.get(
        "AGENT_BASE_URL", config.get("base_url", "https://api.openai.com/v1")
    )
    config["api_key"] = os.environ.get("AGENT_API_KEY", config.get("api_key", ""))
    config["model"] = os.environ.get("AGENT_MODEL", config.get("model", "gpt-4o"))
    config["max_iterations"] = int(
        os.environ.get("AGENT_MAX_ITER", config.get("max_iterations", 50))
    )
    config["tools_dir"] = os.environ.get(
        "AGENT_TOOLS_DIR", config.get("tools_dir", "tools")
    )
    auto_confirm_env = os.environ.get("AGENT_AUTO_CONFIRM", "").lower()
    if auto_confirm_env:
        config["auto_confirm"] = auto_confirm_env == "true"
    else:
        config["auto_confirm"] = bool(config.get("auto_confirm", False))

    return config


# ============================================================
# 工具加载器
# ============================================================


@dataclass
class LoadedTool:
    name: str
    description: str
    module_name: str
    dangerous: bool = False


class ToolRegistry:
    """自动扫描 tools/ 目录并加载工具模块。"""

    def __init__(self, console: Console, tools_dir: str):
        self.console = console
        self.tools_dir = Path(tools_dir)
        self.tool_schemas: list[dict[str, Any]] = []
        self.handlers: dict[str, Callable[..., str]] = {}
        self.safety: dict[str, bool] = {}
        self.loaded_tools: list[LoadedTool] = []

    def load(self) -> None:
        self.tool_schemas.clear()
        self.handlers.clear()
        self.safety.clear()
        self.loaded_tools.clear()

        if not self.tools_dir.exists():
            self.console.print(
                f"[yellow]⚠️ 工具目录不存在: {self.tools_dir}，将以空工具集启动[/yellow]"
            )
            return

        module_files = sorted(
            [
                p
                for p in self.tools_dir.glob("*.py")
                if p.is_file() and not p.name.startswith("_")
            ]
        )

        for module_path in module_files:
            self._load_module(module_path)

    def _load_module(self, module_path: Path) -> None:
        module_name = f"agent_tool_{module_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                self.console.print(
                    f"[yellow]⚠️ 无法加载工具模块: {module_path.name}[/yellow]"
                )
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as exc:
            self.console.print(
                f"[red]❌ 工具模块加载失败: {module_path.name} -> {exc}[/red]"
            )
            return

        if not hasattr(module, "register"):
            self.console.print(
                f"[yellow]⚠️ 工具模块缺少 register()，已跳过: {module_path.name}[/yellow]"
            )
            return

        try:
            plugin = module.register()
        except Exception as exc:
            self.console.print(
                f"[red]❌ 工具模块 register() 执行失败: {module_path.name} -> {exc}[/red]"
            )
            return

        self._merge_plugin(plugin, module_path.name)

    def _merge_plugin(self, plugin: Any, source_name: str) -> None:
        if not isinstance(plugin, dict):
            self.console.print(
                f"[yellow]⚠️ 工具模块返回值格式错误，已跳过: {source_name}[/yellow]"
            )
            return

        tools = plugin.get("tools")
        if tools is None and plugin.get("tool") is not None:
            tools = [plugin["tool"]]

        handlers = plugin.get("handlers", {})
        safety = plugin.get("safety", {})

        if not isinstance(tools, list) or not isinstance(handlers, dict) or not isinstance(safety, dict):
            self.console.print(
                f"[yellow]⚠️ 工具模块字段格式错误，已跳过: {source_name}[/yellow]"
            )
            return

        for schema in tools:
            if not isinstance(schema, dict):
                continue
            tool_name = self._extract_tool_name(schema)
            tool_desc = self._extract_tool_description(schema)
            if not tool_name:
                continue
            if tool_name in self.handlers:
                self.console.print(
                    f"[yellow]⚠️ 工具重复: {tool_name}，后加载模块将覆盖前者[/yellow]"
                )
            self.tool_schemas.append(schema)
            self.loaded_tools.append(
                LoadedTool(
                    name=tool_name,
                    description=tool_desc,
                    module_name=source_name,
                    dangerous=bool(safety.get(tool_name, False)),
                )
            )

        for tool_name, handler in handlers.items():
            if callable(handler):
                self.handlers[tool_name] = handler

        for tool_name, is_dangerous in safety.items():
            self.safety[tool_name] = bool(is_dangerous)

    @staticmethod
    def _extract_tool_name(schema: dict[str, Any]) -> str:
        if schema.get("type") == "function":
            function_spec = schema.get("function", {})
            return str(function_spec.get("name", "")).strip()
        return str(schema.get("name", "")).strip()

    @staticmethod
    def _extract_tool_description(schema: dict[str, Any]) -> str:
        if schema.get("type") == "function":
            function_spec = schema.get("function", {})
            return str(function_spec.get("description", "")).strip()
        return str(schema.get("description", "")).strip()

    def is_dangerous(self, tool_name: str) -> bool:
        return bool(self.safety.get(tool_name, False))

    def summary(self) -> str:
        if not self.loaded_tools:
            return "当前没有加载任何工具模块。"

        lines = []
        for item in self.loaded_tools:
            mark = "⚠️" if item.dangerous else "•"
            desc = f" - {item.description}" if item.description else ""
            lines.append(f"{mark} {item.name} ({item.module_name}){desc}")
        return "\n".join(lines)


# ============================================================
# 系统提示词
# ============================================================


def build_system_prompt(tool_schemas: list[dict[str, Any]]) -> str:
    tool_lines: list[str] = []
    for schema in tool_schemas:
        if schema.get("type") == "function":
            function_spec = schema.get("function", {})
            name = function_spec.get("name", "未知工具")
            desc = function_spec.get("description", "")
        else:
            name = schema.get("name", "未知工具")
            desc = schema.get("description", "")
        tool_lines.append(f"- {name}: {desc}" if desc else f"- {name}")

    tools_text = "\n".join(tool_lines) if tool_lines else "- 暂无可用工具"

    return f"""你是一个强大的模块化 AI 助手，目标是帮助用户完成任务，并在需要时自动调用工具。

你的能力来自动态加载的工具模块。新增、删除、替换工具模块时，Agent 入口无需改动。

当前可用工具：
{tools_text}

工作原则：
- 先了解当前状态再行动，避免盲目修改
- 对于复杂任务，分步骤执行
- 执行命令前考虑安全性
- 危险操作会由系统单独确认
- 当任务已经完成时，直接输出最终结果，不要为了继续执行而继续调用工具
- `max_iterations` 只是安全上限，不是必须用完的轮数
- 给出清晰、简洁、可执行的反馈
"""


# ============================================================
# Agent 主循环
# ============================================================


class AIAgent:
    """AI Agent 主类。"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.console = Console()
        self.client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])
        self.model = config["model"]
        self.max_iterations = config["max_iterations"]

        self.tool_registry = ToolRegistry(self.console, config["tools_dir"])
        self.tool_registry.load()

        self.console.print(f"[dim]最大迭代次数: {self.max_iterations}[/dim]")
        self.console.print(
            f"[dim]已加载工具: {len(self.tool_registry.loaded_tools)} 个，来自 {len({t.module_name for t in self.tool_registry.loaded_tools})} 个模块[/dim]"
        )
        self.messages = [{"role": "system", "content": build_system_prompt(self.tool_registry.tool_schemas)}]

    def _confirm(self, action: str) -> bool:
        if self.config["auto_confirm"]:
            return True
        self.console.print(f"[yellow]⚠️  即将执行: {action}[/yellow]")
        response = input("确认执行? (y/n): ").strip().lower()
        return response in ("y", "yes", "是")

    def _dispatch_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        handler = self.tool_registry.handlers.get(tool_name)
        if handler is None:
            return f"❌ 未知工具: {tool_name}"

        if self.tool_registry.is_dangerous(tool_name):
            if not self._confirm(f"执行工具: {tool_name}"):
                return "⚠️ 操作已取消"

        try:
            return handler(**arguments)
        except TypeError as exc:
            return f"❌ 工具参数错误: {exc}"
        except Exception as exc:
            return f"❌ 工具执行失败: {exc}"

    def chat(self, user_input: str) -> str:
        """处理一轮对话，包含可能的多次工具调用。"""
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tool_registry.tool_schemas,
                    tool_choice="auto",
                )
            except Exception as exc:
                error_msg = f"❌ API 调用失败: {exc}"
                self.console.print(f"[red]{error_msg}[/red]")
                return error_msg

            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return message.content or ""

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                self.console.print(f"\n[cyan]🔧 调用工具: {func_name}[/cyan]")
                if arguments:
                    display_args = {}
                    for key, value in arguments.items():
                        if isinstance(value, str) and len(value) > 200:
                            display_args[key] = value[:200] + "..."
                        else:
                            display_args[key] = value
                    self.console.print(
                        f"[dim]   参数: {json.dumps(display_args, ensure_ascii=False, indent=2)}[/dim]"
                    )

                result = self._dispatch_tool(func_name, arguments)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "⚠️ 达到最大迭代次数，已停止。"

    def reset(self) -> None:
        """重置对话历史。"""
        self.messages = [{"role": "system", "content": build_system_prompt(self.tool_registry.tool_schemas)}]
        self.console.print("[yellow]🔄 对话已重置[/yellow]")

    def print_tools(self) -> None:
        """打印当前加载的工具列表。"""
        self.console.print(Panel(self.tool_registry.summary(), title="已加载工具", border_style="green"))


# ============================================================
# 交互式主程序
# ============================================================


def main() -> None:
    console = Console()

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_path)

    if not config["api_key"] or config["api_key"] == "sk-your-api-key-here":
        console.print("[red]❌ 请先配置 API Key![/red]")
        console.print("   方法1: 编辑 config.yaml 中的 api_key")
        console.print("   方法2: 设置环境变量 AGENT_API_KEY")
        sys.exit(1)

    agent = AIAgent(config)

    console.print(
        Panel.fit(
            f"[bold green]🤖 模块化 AI Agent 已启动[/bold green]\n\n"
            f"  模型: [cyan]{config['model']}[/cyan]\n"
            f"  API:  [cyan]{config['base_url']}[/cyan]\n"
            f"  工具目录: [cyan]{config['tools_dir']}[/cyan]\n"
            f"  自动确认: [cyan]{config['auto_confirm']}[/cyan]\n\n"
            f"[dim]输入 /help 查看命令, /tools 查看已加载模块, /quit 退出[/dim]",
            title="AI Agent",
            border_style="green",
        )
    )

    while True:
        try:
            console.print()
            user_input = input("👤 You > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]👋 再见![/yellow]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[yellow]👋 再见![/yellow]")
                break
            if cmd in ("/reset", "/clear"):
                agent.reset()
                continue
            if cmd == "/tools":
                agent.print_tools()
                continue
            if cmd == "/help":
                console.print(
                    Panel(
                        "[bold]可用命令:[/bold]\n\n"
                        "  /help   - 显示帮助\n"
                        "  /reset  - 重置对话历史\n"
                        "  /tools  - 查看当前加载的工具模块\n"
                        "  /quit   - 退出程序\n\n"
                        "[bold]功能:[/bold]\n\n"
                        "  直接用自然语言描述你的需求即可。\n"
                        "  Agent 会自动调用已加载的工具模块来完成任务。",
                        title="帮助",
                        border_style="blue",
                    )
                )
                continue

            console.print(f"[red]未知命令: {user_input}[/red]")
            continue

        console.print()
        response = agent.chat(user_input)

        if response:
            console.print()
            console.print(
                Panel(
                    Markdown(response),
                    title="🤖 Assistant",
                    border_style="blue",
                    padding=(1, 2),
                )
            )


if __name__ == "__main__":
    main()
