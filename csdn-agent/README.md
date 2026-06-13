# csdn-agent

这是一个独立的 CSDN 博客知识库子项目，默认面向主页：

`https://blog.csdn.net/weixin_57166741`

## 目标

把你自己的 CSDN 博客当作本地可检索数据库使用，供上层 Agent 在回答问题时优先检索，再结合 AI 自身判断是否能够直接解决问题。

## 工作规则

- 用户提问时，**先搜索本地 CSDN 数据库**
- 如果命中的内容足够，优先按数据库内容回答
- 如果数据库内容不够完整，再由 AI 自己推理、补充或给出替代方案
- 抓取范围只允许 `weixin_57166741` 这个博客路径下的文章
- 不应把其他 CSDN 博主的文章混入索引

## 功能

- 抓取指定 CSDN 主页及其文章链接
- 直接列出该博主的所有文章链接
- 构建本地 JSON 索引
- 按关键词搜索本地知识库
- 支持清空索引、查看状态

## 目录结构

```text
csdn-agent/
├── AGENT_RULES.md
├── README.md
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── indexer.py
│   └── utils.py
└── storage/
    ├── crawl_state.json
    └── csdn_index.json
```

## 使用方式

### 1. 直接列出所有文章链接

```bash
python -m csdn_agent.src.cli links --max-pages 20
```

如果想要 JSON 输出：

```bash
python -m csdn_agent.src.cli links --max-pages 20 --json
```

### 2. 抓取并建立索引

```bash
python -m csdn_agent.src.cli crawl --max-articles 30 --max-pages 5
```

### 3. 搜索索引

```bash
python -m csdn_agent.src.cli query "Python" --limit 5
```

### 4. 查看状态

```bash
python -m csdn_agent.src.cli stats
```

### 5. 清空索引

```bash
python -m csdn_agent.src.cli clear
```

## 默认配置

- 默认主页：`https://blog.csdn.net/weixin_57166741`
- 索引文件：`csdn-agent/storage/csdn_index.json`
- 状态文件：`csdn-agent/storage/crawl_state.json`

## 说明

- 该子项目会优先把 CSDN 内容整理成可检索的本地数据库。
- 上层 Agent 可以先调用它搜索，再结合 AI 自己判断是否足以回答问题。
- 如果数据库里没有足够信息，AI 再自行推理或补充回答。
