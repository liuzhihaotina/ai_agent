#!/usr/bin/env python3
"""
AI Agent - 支持文件读写和终端命令执行
可配置 URL、API Key 和 Model ID
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


# ============================================================
# 配置加载
# ============================================================

def load_config(config_path: str = None) -> dict:
    """加载配置文件，支持环境变量覆盖"""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"

    config = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # 环境变量优先级更高
    config["base_url"] = os.environ.get(
        "AGENT_BASE_URL", config.get("base_url", "https://api.openai.com/v1")
    )
    config["api_key"] = os.environ.get(
        "AGENT_API_KEY", config.get("api_key", "")
    )
    config["model"] = os.environ.get(
        "AGENT_MODEL", config.get("model", "gpt-4o")
    )
    config["max_iterations"] = int(
        os.environ.get("AGENT_MAX_ITER", config.get("max_iterations", 50))
    )
    auto_confirm_env = os.environ.get("AGENT_AUTO_CONFIRM", "").lower()
    if auto_confirm_env:
        config["auto_confirm"] = auto_confirm_env == "true"
    else:
        config["auto_confirm"] = bool(config.get("auto_confirm", False))

    return config


# ============================================================
# 工具定义 (OpenAI Function Calling 格式)
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径文件的内容。支持文本文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径 (相对路径或绝对路径)",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将内容写入指定文件。如果文件不存在则创建，如果存在则覆盖。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "编辑文件中的指定内容。将 old_text 替换为 new_text。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要被替换的原始文本 (必须精确匹配)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "替换后的新文本",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
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
                        "description": "工作目录 (可选，默认为当前目录)",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出指定目录中的文件和子目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径，默认为当前目录",
                    }
                },
                "required": [],
            },
        },
    },
]


# ============================================================
# 工具实现
# ================================================


class ToolExecutor:
    """工具执行器"""

    def __init__(self, console: Console, auto_confirm: bool = False):
        self.console = console
        self.auto_confirm = auto_confirm

    def _confirm(self, action: str) -> bool:
        """危险操作确认"""
        if self.auto_confirm:
            return True
        self.console.print(f"[yellow]⚠️  即将执行: {action}[/yellow]")
        response = input("确认执行? (y/n): ").strip().lower()
        return response in ("y", "yes", "是")

    def read_file(self, path: str) -> str:
        """读取文件"""
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return f"❌ 错误: 文件不存在 - {path}"
            if not p.is_file():
                return f"❌ 错误: 路径不是文件 - {path}"
            content = p.read_text(encoding="utf-8")
            self.console.print(f"[green]📄 已读取文件: {path} ({len(content)} 字符)[/green]")
            return content
        except Exception as e:
            return f"❌ 读取文件失败: {e}"

    def write_file(self, path: str, content: str) -> str:
        """写入文件"""
        if not self._confirm(f"写入文件: {path}"):
            return "⚠️ 操作已取消"
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            self.console.print(f"[green]✅ 已写入文件: {path} ({len(content)} 字符)[/green]")
            return f"✅ 文件写入成功: {path}"
        except Exception as e:
            return f"❌ 写入文件失败: {e}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """编辑文件 (查找替换)"""
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return f"❌ 错误: 文件不存在 - {path}"
            content = p.read_text(encoding="utf-8")
            if old_text not in content:
                return "❌ 错误: 未在文件中找到要替换的文本"

            if not self._confirm(f"编辑文件: {path}"):
                return "⚠️ 操作已取消"

            new_content = content.replace(old_text, new_text, 1)
            p.write_text(new_content, encoding="utf-8")
            self.console.print(f"[green]✅ 已编辑文件: {path}[/green]")
            return f"✅ 文件编辑成功: {path}"
        except Exception as e:
            return f"❌ 编辑文件失败: {e}"

    def execute_command(self, command: str, working_dir: str = None) -> str:
        """执行终端命令"""
        if not self._confirm(f"执行命令: {command}"):
            return "⚠️ 操作已取消"
        try:
            cwd = working_dir if working_dir else None
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=cwd,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[返回码: {result.returncode}]"

            self.console.print(f"[green]⚡ 命令执行完成 (返回码: {result.returncode})[/green]")
            return output.strip() if output.strip() else "(无输出)"
        except subprocess.TimeoutExpired:
            return "❌ 命令执行超时 (120秒)"
        except Exception as e:
            return f"❌ 命令执行失败: {e}"

    def list_directory(self, path: str = ".") -> str:
        """列出目录内容"""
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return f"❌ 错误: 目录不存在 - {path}"
            if not p.is_dir():
                return f"❌ 错误: 路径不是目录 - {path}"

            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            lines = []
            for item in items:
                prefix = "📁" if item.is_dir() else "📄"
                lines.append(f"  {prefix} {item.name}")

            self.console.print(f"[green]📂 目录: {path} ({len(items)} 项)[/green]")
            return "\n".join(lines) if lines else "(空目录)"
        except Exception as e:
            return f"❌ 列出目录失败: {e}"

    def dispatch(self, tool_name: str, arguments: dict) -> str:
        """分发工具调用"""
        handlers = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "edit_file": self.edit_file,
            "execute_command": self.execute_command,
            "list_directory": self.list_directory,
        }
        handler = handlers.get(tool_name)
        if handler:
            return handler(**arguments)
        return f"❌ 未知工具: {tool_name}"


# ============================================================
# Agent 主循环
# ================================================

SYSTEM_PROMPT = """你是一个强大的 AI 助手，可以帮助用户完成各种任务。

你拥有以下能力：
1. **读取文件** (read_file) - 查看任意文本文件的内容
2. **写入文件** (write_file) - 创建或覆盖文件
3. **编辑文件** (edit_file) - 精确替换文件中的指定内容
4. **执行命令** (execute_command) - 在终端执行 shell 命令
5. **列出目录** (list_directory) - 查看目录结构

工作原则：
- 先了解当前状态再行动 (先读取再修改)
- 对于复杂任务，分步骤执行
- 执行命令前考虑安全性
- 当任务已经完成时，直接输出最终结果，不要为了继续执行而继续调用工具
- `max_iterations` 只是安全上限，不是必须用完的轮数
- 给出清晰的解释和反馈
"""


class AIAgent:
    """AI Agent 主类"""

    def __init__(self, config: dict):
        self.config = config
        self.console = Console()
        self.client = OpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )
        self.model = config["model"]
        self.max_iterations = config["max_iterations"]
        self.console.print(f"[dim]最大迭代次数: {self.max_iterations}[/dim]")
        self.tool_executor = ToolExecutor(self.console, config["auto_confirm"])
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        """处理一轮对话，包含可能的多次工具调用"""
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            # 调用 LLM
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                tools=TOOLS,
                tool_choice="auto",
                )
            except Exception as e:
                error_msg = f"❌ API 调用失败: {e}"
                self.console.print(f"[red]{error_msg}[/red]")
                return error_msg

            message = response.choices[0].message
            self.messages.append(message)

            # 如果没有工具调用，返回最终回复
            if not message.tool_calls:
                return message.content or ""

            # 处理工具调用
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                self.console.print(f"\n[cyan]🔧 调用工具: {func_name}[/cyan]")
                if arguments:
                    display_args = {}
                    for k, v in arguments.items():
                        if isinstance(v, str) and len(v) > 200:
                            display_args[k] = v[:200] + "..."
                        else:
                            display_args[k] = v
                    self.console.print(
                        f"[dim]   参数: {json.dumps(display_args, ensure_ascii=False, indent=2)}[/dim]"
                    )

                # 执行工具
                result = self.tool_executor.dispatch(func_name, arguments)

                # 添加工具结果到消息
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "⚠️ 达到最大迭代次数，已停止。"

    def reset(self):
        """重置对话历史"""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.console.print("[yellow]🔄 对话已重置[/yellow]")


# ============================================================
# 交互式主程序
# ============================================================


def main():
    console = Console()

    # 加载配置
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_path)

    # 检查 API Key
    if not config["api_key"] or config["api_key"] == "sk-your-api-key-here":
        console.print("[red]❌ 请先配置 API Key![/red]")
        console.print("   方法1: 编辑 config.yaml 中的 api_key")
        console.print("   方法2: 设置环境变量 AGENT_API_KEY")
        sys.exit(1)

    # 显示启动信息
    console.print(
        Panel.fit(
            f"[bold green]🤖 AI Agent 已启动[/bold green]\n\n"
            f"  模型: [cyan]{config['model']}[/cyan]\n"
            f"  API:  [cyan]{config['base_url']}[/cyan]\n"
            f"  自动确认: [cyan]{config['auto_confirm']}[/cyan]\n\n"
            f"[dim]输入 /help 查看命令, /quit 退出[/dim]",
            title="AI Agent",
            border_style="green",
        )
    )

    agent = AIAgent(config)

    while True:
        try:
            console.print()
            user_input = input("👤 You > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]👋 再见![/yellow]")
            break

        if not user_input:
            continue

        # 内置命令
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[yellow]👋 再见![/yellow]")
                break
            elif cmd in ("/reset", "/clear"):
                agent.reset()
                continue
            elif cmd == "/help":
                console.print(
                    Panel(
                        "[bold]可用命令:[/bold]\n\n"
                        "  /help   - 显示帮助\n"
                        "  /reset  - 重置对话历史\n"
                        "  /quit   - 退出程序\n\n"
                        "[bold]功能:[/bold]\n\n"
                        "  直接用自然语言描述你的需求即可。\n"
                        "  Agent 可以读写文件、执行命令来帮你完成任务。",
                        title="帮助",
                        border_style="blue",
                    )
                )
                continue
            else:
                console.print(f"[red]未知命令: {user_input}[/red]")
                continue

        # 调用 Agent
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