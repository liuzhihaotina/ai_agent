# ai_agent

AI Agent 自搭建。

这是一个面向扩展的命令行 AI Agent：
- 核心入口只负责加载配置、扫描工具模块、驱动对话循环
- 每个独立功能都放在 `tools/` 目录下的单独模块中
- 你可以随时删除、替换、增加某个功能模块，而无需修改 `agent.py`

## 核心能力

当前内置的基础工具模块包括：

- `read_file`：读取文本文件
- `write_file`：写入文件
- `edit_file`：按精确文本替换编辑文件
- `list_directory`：列出目录内容
- `execute_command`：执行终端命令
- `search_files`：在目录内递归搜索文件内容

## 目录结构

```text
ai_agent/
├── agent.py            # 统一入口：自动加载 tools/ 中的模块
├── config.example.yaml # 配置示例
├── requirements.txt    # Python 依赖
├── README.md           # 使用说明
├── .gitignore
└── tools/              # 独立功能模块目录
    ├── read_file.py
    ├── write_file.py
    ├── edit_file.py
    ├── list_directory.py
    ├── execute_command.py
    └── search_files.py
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

复制示例配置文件：

```bash
copy config.example.yaml config.yaml
```

或者使用你自己的 `config.yaml`。

### 配置项

```yaml
base_url: "https://api.openai.com/v1"
api_key: "sk-your-api-key-here"
model: "gpt-4o"
max_iterations: 20
auto_confirm: false
tools_dir: "tools"
```

说明：

- `base_url`：OpenAI 兼容接口地址
- `api_key`：接口密钥
- `model`：模型名称
- `max_iterations`：最大对话轮数
- `auto_confirm`：是否自动确认危险操作
- `tools_dir`：工具模块目录，默认就是 `tools`

也可以通过环境变量覆盖：

- `AGENT_BASE_URL`
- `AGENT_API_KEY`
- `AGENT_MODEL`
- `AGENT_MAX_ITER`
- `AGENT_AUTO_CONFIRM`
- `AGENT_TOOLS_DIR`

## 启动

```bash
python agent.py
```

如果想指定配置文件：

```bash
python agent.py config.yaml
```

## 交互命令

启动后可使用：

- `/help`：显示帮助
- `/reset`：重置对话历史
- `/tools`：查看当前加载的工具模块
- `/quit` 或 `/exit`：退出程序

## 如何扩展新功能

你只需要在 `tools/` 目录下新增一个 `.py` 文件，并实现一个 `register()` 函数即可。

### 推荐结构

```python
from typing import Any


def my_tool(arg1: str) -> str:
    return "..."


def register() -> dict[str, Any]:
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "my_tool",
                    "description": "工具描述",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "arg1": {"type": "string"},
                        },
                        "required": ["arg1"],
                    },
                },
            }
        ],
        "handlers": {"my_tool": my_tool},
        "safety": {"my_tool": False},
    }
```

### 约定

- `tools`：OpenAI function calling 的工具定义列表
- `handlers`：工具名到 Python 函数的映射
- `safety`：工具名到是否危险操作的映射

### 删除或替换功能

- 删除某个工具：直接删除对应的 `tools/*.py`
- 替换某个工具：直接改对应模块文件
- 新增某个工具：直接新增新模块文件

不需要修改 `agent.py`。

## 当前建议

如果你后续想继续增强这个 Agent，可以优先拆成这些方向：

- 文件系统工具集：复制、移动、删除、批量重命名
- 代码分析工具集：AST 分析、依赖搜索、接口提取
- 项目管理工具集：Git 状态、分支信息、变更摘要
- 知识检索工具集：全文索引、目录总结、结构概览
- 自动化工具集：定时任务、批处理、环境检查

## 注意事项

- `execute_command` 和写文件类工具具有一定风险，建议谨慎使用。
- 你可以通过 `auto_confirm` 控制是否自动确认危险操作。
- `search_files` 会递归扫描目录，目录很大时可能比较耗时。
