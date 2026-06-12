# ai_agent

AI Agent 自搭建。

## 项目简介

这是一个命令行 AI Agent，支持：

- 读取文件
- 写入文件
- 编辑文件
- 列出目录
- 执行终端命令
- 支持 OpenAI 兼容接口

## 项目目录

```text
ai_agent/
├── agent.py            # 主入口：AI Agent 命令行程序
├── config.example.yaml # 配置示例
├── requirements.txt    # Python 依赖
├── README.md           # 使用说明
└── .gitignore
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

项目通过 `config.yaml` 进行配置，也支持使用环境变量覆盖。

### 方式一：修改 `config.yaml`

```bash
cp config.example.yaml config.yaml
```

```yaml
base_url: "https://api.openai.com/v1"
api_key: "sk-your-api-key-here"
model: "gpt-4o"
max_iterations: 50
auto_confirm: false
```

### 方式二：使用环境变量

- `AGENT_BASE_URL`
- `AGENT_API_KEY`
- `AGENT_MODEL`
- `AGENT_MAX_ITER`（最大迭代次数，默认 50）
- `AGENT_AUTO_CONFIRM`

例如：

```bash
set AGENT_API_KEY=你的API_KEY
set AGENT_BASE_URL=https://api.openai.com/v1
set AGENT_MODEL=gpt-4o
```

## 使用方法

1. 安装依赖
2. 配置 `config.yaml` 或环境变量
3. 启动程序：

```bash
python agent.py
```

如果你想指定配置文件，也可以传入路径：

```bash
python agent.py config.yaml
```

## 交互命令

在程序启动后，可以输入以下内置命令：

- `/help`：显示帮助
- `/reset`：重置对话历史
- `/quit` 或 `/exit`：退出程序

## 示例

你可以直接用自然语言描述需求，例如：

- 帮我读取 `README.md`
- 新建一个 `test.txt` 文件并写入内容
- 列出当前目录下的文件
- 执行 `python --version`

## 注意事项

- 执行命令、写入文件等操作可能会修改本地文件，请谨慎使用。
- 建议先确认 `config.yaml` 中的 `api_key` 和 `base_url` 是否正确。
- 默认情况下，危险操作需要手动确认；如果将 `auto_confirm` 设置为 `true`，则会自动执行。
- `max_iterations` 只是安全上限，Agent 会在认为任务已经完成时主动结束。
