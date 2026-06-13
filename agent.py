#!/usr/bin/env python3
"""
AI Agent - 支持文件读写、终端命令执行、B 站搜索、任务看板读取/更新
"""

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


# ============================================================
# 输入处理
# ============================================================


def read_user_input(prompt: str) -> str:
    """读取用户输入；优先使用 prompt_toolkit 以兼容 Git Bash。"""

    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.enums import EditingMode
        from prompt_toolkit.key_binding import KeyBindings

        bindings = KeyBindings()

        @bindings.add("c-c")
        def _(event):
            raise KeyboardInterrupt

        return pt_prompt(
            prompt,
            key_bindings=bindings,
            editing_mode=EditingMode.EMACS,
            mouse_support=False,
        )
    except Exception:
        pass

    def char_display_width(ch: str) -> int:
        if unicodedata.combining(ch):
            return 0
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            return 2
        return 1

    def text_display_width(text: str) -> int:
        return sum(char_display_width(ch) for ch in text)

    if os.name == "nt":
        try:
            import msvcrt

            buffer = []
            cursor = 0
            pending_high_surrogate = None

            def redraw() -> None:
                rendered_before = prompt + "".join(buffer[:cursor])
                rendered_full = prompt + "".join(buffer)
                before_width = text_display_width(rendered_before)
                full_width = text_display_width(rendered_full)
                pad = max(0, full_width - before_width)
                sys.stdout.write("\r\x1b[2K" + rendered_full)
                if pad:
                    sys.stdout.write(" " * pad)
                back = max(0, full_width - before_width)
                if back:
                    sys.stdout.write("\b" * back)
                sys.stdout.flush()

            sys.stdout.write(prompt)
            sys.stdout.flush()

            while True:
                ch = msvcrt.getwch()

                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break

                if ch == "\x03":
                    raise KeyboardInterrupt

                if ch == "\x01":
                    cursor = 0
                    redraw()
                    continue

                if ch == "\x05":
                    cursor = len(buffer)
                    redraw()
                    continue

                if ch in ("\b", "\x7f"):
                    if pending_high_surrogate is not None:
                        pending_high_surrogate = None
                    elif cursor > 0:
                        cursor -= 1
                        buffer.pop(cursor)
                        redraw()
                    continue

                if ch in ("\x00", "\xe0"):
                    key = msvcrt.getwch()
                    if key == "K" and cursor > 0:
                        cursor -= 1
                        redraw()
                    elif key == "M" and cursor < len(buffer):
                        cursor += 1
                        redraw()
                    continue

                code_point = ord(ch)
                if 0xD800 <= code_point <= 0xDBFF:
                    pending_high_surrogate = ch
                    continue

                if 0xDC00 <= code_point <= 0xDFFF:
                    if pending_high_surrogate is not None:
                        high = ord(pending_high_surrogate) - 0xD800
                        low = code_point - 0xDC00
                        ch = chr((high << 10) + low + 0x10000)
                        pending_high_surrogate = None
                    else:
                        continue
                else:
                    pending_high_surrogate = None

                buffer.insert(cursor, ch)
                cursor += 1
                redraw()

            return "".join(buffer)
        except ImportError:
            pass

    return input(prompt)


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
# 工具定义
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
                    "path": {"type": "string", "description": "文件路径 (相对路径或绝对路径)"}
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
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的文件内容"},
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
                    "path": {"type": "string", "description": "文件路径"},
                    "old_text": {"type": "string", "description": "要被替换的原始文本 (必须精确匹配)"},
                    "new_text": {"type": "string", "description": "替换后的新文本"},
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
                    "command": {"type": "string", "description": "要执行的 shell 命令"},
                    "working_dir": {"type": "string", "description": "工作目录 (可选，默认为当前目录)"},
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒）；如果传入大于 1000 的值，将自动按毫秒换算",
                        "default": 120,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bilibili_search",
            "description": "调用 bilibili-agent 子项目，通过 Node.js 在 B 站搜索关键词并返回结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "B 站搜索关键词"},
                    "max_results": {"type": "integer", "description": "返回结果数量上限", "default": 10},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_list",
            "description": "访问 http://localhost:3000 的任务看板，列出当前所有任务或按关键词筛选后的任务及其状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "可选关键字，用于筛选创建人、任务名或状态", "default": ""},
                    "field": {"type": "string", "description": "可选，限定匹配字段：creator、name、status、any", "default": "any"},
                    "headless": {"type": "boolean", "description": "是否无头模式执行", "default": True},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_update",
            "description": "访问 http://localhost:3000 的任务看板，按创建人/任务名/状态筛选任务，并把匹配任务状态更新为目标状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "用于匹配任务的关键字，可匹配创建人、任务名或状态"},
                    "to_status": {"type": "string", "description": "要修改成的新状态，支持：待处理、进行中、已完成、已关闭"},
                    "from_status": {"type": "string", "description": "可选，只有当前状态匹配时才更新"},
                    "field": {"type": "string", "description": "可选，限定匹配字段：creator、name、status、any", "default": "any"},
                    "headless": {"type": "boolean", "description": "是否无头模式执行", "default": True},
                },
                "required": ["keyword", "to_status"],
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
                    "path": {"type": "string", "description": "目录路径，默认为当前目录"}
                },
                "required": [],
            },
        },
    },
]


# ============================================================
# 工具执行器
# ============================================================


class ToolExecutor:
    """工具执行器"""

    def __init__(self, console: Console, auto_confirm: bool = False):
        self.console = console
        self.auto_confirm = auto_confirm

    def _prompt_confirm(self, action: str) -> bool:
        if self.auto_confirm:
            return True
        self.console.print(f"[yellow]⚠️  即将执行: {action}[/yellow]")
        response = input("确认执行? (y/n): ").strip().lower()
        return response in ("y", "yes", "是")

    def _is_risky_command(self, command: str) -> bool:
        cmd = command.lower().strip()
        risky_patterns = [
            "rm -rf",
            "rm -fr",
            "del /s",
            "del /q",
            "rmdir /s",
            "rd /s",
            "format ",
            "shutdown",
            "reboot",
            "restart",
            "git reset --hard",
            "git clean -fd",
            "pip uninstall",
            "npm uninstall",
            "yarn remove",
            "sudo ",
            "> /dev/null 2>&1",
        ]
        return any(pattern in cmd for pattern in risky_patterns)

    def read_file(self, path: str) -> str:
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
        try:
            p = Path(path).expanduser()
            if p.exists() and not self._prompt_confirm(f"覆盖文件: {path}"):
                return "⚠️ 操作已取消"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            self.console.print(f"[green]✅ 已写入文件: {path} ({len(content)} 字符)[/green]")
            return f"✅ 文件写入成功: {path}"
        except Exception as e:
            return f"❌ 写入文件失败: {e}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return f"❌ 错误: 文件不存在 - {path}"
            content = p.read_text(encoding="utf-8")
            if old_text not in content:
                return "❌ 错误: 未在文件中找到要替换的文本"
            if not self._prompt_confirm(f"编辑文件: {path}"):
                return "⚠️ 操作已取消"
            new_content = content.replace(old_text, new_text, 1)
            p.write_text(new_content, encoding="utf-8")
            self.console.print(f"[green]✅ 已编辑文件: {path}[/green]")
            return f"✅ 文件编辑成功: {path}"
        except Exception as e:
            return f"❌ 编辑文件失败: {e}"

    def execute_command(self, command: str, working_dir: str = None, timeout: int = 120) -> str:
        if self._is_risky_command(command) and not self._prompt_confirm(f"执行高风险命令: {command}"):
            return "⚠️ 操作已取消"
        try:
            cwd = working_dir if working_dir else None
            timeout_seconds = timeout / 1000 if timeout and timeout > 1000 else timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
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

    def bilibili_search(self, keyword: str, max_results: int = 10) -> str:
        try:
            project_dir = Path(__file__).parent / "bilibili-agent"
            cli_path = project_dir / "src" / "cli.js"
            if not cli_path.exists():
                return f"❌ 找不到 B 站搜索入口: {cli_path}"
            result = subprocess.run(
                ["node", str(cli_path), keyword, str(max_results)],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            output = (result.stdout or "").strip()
            error_output = (result.stderr or "").strip()
            if result.returncode != 0:
                detail = error_output or output or f"返回码 {result.returncode}"
                return f"❌ B 站搜索失败: {detail}"
            return output or "(无返回结果)"
        except FileNotFoundError:
            return "❌ 未找到 node 命令，请先安装 Node.js 并确保 node 可用"
        except subprocess.TimeoutExpired:
            return "❌ B 站搜索超时 (300秒)"
        except Exception as e:
            return f"❌ B 站搜索失败: {e}"

    def task_list(self, keyword: str = "", field: str = "any", headless: bool = True) -> str:
        try:
            project_dir = Path(__file__).parent / "task-agent"
            cli_path = project_dir / "src" / "cli.js"
            if not cli_path.exists():
                return f"❌ 找不到任务列表入口: {cli_path}"

            cmd = ["node", str(cli_path), "--list"]
            if keyword:
                cmd.extend(["--keyword", keyword])
            if field and field != "any":
                cmd.extend(["--field", field])
            if not headless:
                cmd.append("--headed")

            result = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            output = (result.stdout or "").strip()
            error_output = (result.stderr or "").strip()
            if result.returncode != 0:
                detail = error_output or output or f"返回码 {result.returncode}"
                return f"❌ 任务列表获取失败: {detail}"
            return output or "(无返回结果)"
        except FileNotFoundError:
            return "❌ 未找到 node 命令，请先安装 Node.js 并确保 node 可用"
        except subprocess.TimeoutExpired:
            return "❌ 任务列表获取超时 (300秒)"
        except Exception as e:
            return f"❌ 任务列表获取失败: {e}"

    def task_update(self, keyword: str, to_status: str, from_status: str = "", field: str = "any", headless: bool = True) -> str:
        try:
            project_dir = Path(__file__).parent / "task-agent"
            cli_path = project_dir / "src" / "cli.js"
            if not cli_path.exists():
                return f"❌ 找不到任务更新入口: {cli_path}"

            cmd = ["node", str(cli_path), "--keyword", keyword, "--to", to_status]
            if from_status:
                cmd.extend(["--from", from_status])
            if field and field != "any":
                cmd.extend(["--field", field])
            if not headless:
                cmd.append("--headed")

            result = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            output = (result.stdout or "").strip()
            error_output = (result.stderr or "").strip()
            if result.returncode != 0:
                detail = error_output or output or f"返回码 {result.returncode}"
                return f"❌ 任务更新失败: {detail}"
            return output or "(无返回结果)"
        except FileNotFoundError:
            return "❌ 未找到 node 命令，请先安装 Node.js 并确保 node 可用"
        except subprocess.TimeoutExpired:
            return "❌ 任务更新超时 (300秒)"
        except Exception as e:
            return f"❌ 任务更新失败: {e}"

    def dispatch(self, tool_name: str, arguments: dict) -> str:
        handlers = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "edit_file": self.edit_file,
            "execute_command": self.execute_command,
            "bilibili_search": self.bilibili_search,
            "task_list": self.task_list,
            "task_update": self.task_update,
            "list_directory": self.list_directory,
        }
        handler = handlers.get(tool_name)
        if handler:
            return handler(**arguments)
        return f"❌ 未知工具: {tool_name}"


# ============================================================
# Agent 主循环
# ============================================================

SYSTEM_PROMPT = """你是一个强大的 AI 助手，可以帮助用户完成各种任务。

你拥有以下能力：
1. **读取文件** (read_file) - 查看任意文本文件的内容
2. **写入文件** (write_file) - 创建或覆盖文件
3. **编辑文件** (edit_file) - 精确替换文件中的指定内容
4. **执行命令** (execute_command) - 在终端执行 shell 命令
5. **B 站搜索** (bilibili_search) - 调用 bilibili-agent 子项目搜索并返回结果
6. **任务列表** (task_list) - 访问 http://localhost:3000 列出任务及状态
7. **任务状态更新** (task_update) - 访问 http://localhost:3000 更新任务状态
8. **列出目录** (list_directory) - 查看目录结构

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
        self.client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])
        self.model = config["model"]
        self.max_iterations = config["max_iterations"]
        self.console.print(f"[dim]最大迭代次数: {self.max_iterations}[/dim]")
        self.tool_executor = ToolExecutor(self.console, config["auto_confirm"])
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
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
                    for k, v in arguments.items():
                        display_args[k] = v[:200] + "..." if isinstance(v, str) and len(v) > 200 else v
                    self.console.print(
                        f"[dim]   参数: {json.dumps(display_args, ensure_ascii=False, indent=2)}[/dim]"
                    )

                result = self.tool_executor.dispatch(func_name, arguments)
                self.messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

        return "⚠️ 达到最大迭代次数，已停止。"

    def reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.console.print("[yellow]🔄 对话已重置[/yellow]")


# ============================================================
# 交互式主程序
# ============================================================


def main():
    console = Console()

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_path)

    if not config["api_key"] or config["api_key"] == "sk-your-api-key-here":
        console.print("[red]❌ 请先配置 API Key![/red]")
        console.print("   方法1: 编辑 config.yaml 中的 api_key")
        console.print("   方法2: 设置环境变量 AGENT_API_KEY")
        sys.exit(1)

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
            user_input = read_user_input("👤 You > ").strip()
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
                        "  Agent 可以读写文件、执行命令，\n"
                        "  也可以列出/更新 localhost 任务看板。",
                        title="帮助",
                        border_style="blue",
                    )
                )
                continue
            else:
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
