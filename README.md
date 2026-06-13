# ai_agent
AI Agent 自搭建

# AI Agent

一个支持文件读写、目录查看和终端命令执行的命令行 AI Agent。

## 功能

- 读取文件
- 写入文件
- 编辑文件
- 列出目录
- 执行终端命令
- 调用 `bilibili_search` 搜索 B 站
- 调用 `csdn_search` 优先搜索你的 CSDN 博客知识库
- 调用 `csdn_refresh` 重新抓取并重建 CSDN 本地数据库
- 支持 OpenAI 兼容接口
- 项目脚本按用途分目录管理

## 项目目录

```text
ai_agent/
├── agent.py               # 主入口：AI Agent 命令行程序
├── bilibili-agent/        # 子项目：B 站登录/搜索自动化
├── config.yaml            # 默认配置
├── requirements.txt       # Python 依赖
├── README.md              # 使用说明
└── scripts/
    └── pdf/               # PDF 文本提取相关脚本
        ├── extract_pdf.py
        ├── extract_snippets.py
        └── tmp_extract_pdf.py
```

### scripts/pdf 目录里的脚本用途

- `extract_pdf.py`：把 PDF 每一页的完整文本提取到 `tmp/pdf_text.txt`
- `extract_snippets.py`：提取每页前若干行内容，生成更精简的页面摘要文本
- `tmp_extract_pdf.py`：临时调试脚本，用于快速查看 PDF 每页的文本内容和长度

## 安装依赖

```bash
pip install -r requirements.txt
```

## B 站子项目依赖

如果你要使用 B 站搜索功能，请先进入子项目安装依赖：

```bash
cd bilibili-agent
npm install
npx playwright install
```

如需先手动登录一次：

```bash
npm run login
```

## 配置

项目通过 `config.yaml` 进行配置，也支持使用环境变量覆盖。

### 方式一：修改 `config.yaml` 

```bash
cp config_your.yaml config.yaml
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
2. 进入 `bilibili-agent/` 执行 `npm install`
3. 进入 `bilibili-agent/` 执行 `npx playwright install`
4. 如需登录，先运行 `npm run login`
5. 配置 `config.yaml` 或环境变量
6. 启动程序（Agent 会在任务完成后自动结束，不需要强制跑满迭代次数）：

主程序入口是根目录下的 `agent.py`，其余 `.py` 工具脚本已整理到 `scripts/pdf/`。

```bash
python agent.py
```

如果你想指定配置文件，也可以传入路径：

```bash
python agent.py config.yaml
```

## B 站搜索

在主程序里，你可以直接让 Agent 调用 `bilibili_search`，例如：

- 帮我在 B 站搜索“人工智能”并返回前 5 条结果
- 调用 bilibili_search 搜索关键词“Python 教程”

也可以直接使用子项目命令：

```bash
cd bilibili-agent
npm run search -- "人工智能" 5
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
