# 深入专题 · LLM 应用开发实战（框架内幕与选型决策）

> 工具全景见 [README](./README.md)，可运行代码见 [10 目录 code/](../10-AI应用实战/code/README.md)。本篇讲框架的设计思想，而非 API 罗列。

## 1. 为什么"先裸写 SDK，再上框架"

LLM 应用的本质只有四件事：**拼 prompt → 调 API → 解析输出 → 循环/编排**。框架做的就是把这四件事抽象成组件。没裸写过就用框架，会被抽象层困住（出了问题不知道是模型、框架还是自己代码的锅）。

```python
# LLM 应用的最小本质（伪代码）
messages = build_prompt(system, history, retrieved_docs)
response = llm.chat(messages)          # 可能含 tool_calls
if response.tool_calls:
    results = execute(response.tool_calls)
    messages += results                # 回喂，进入下一轮
```

## 2. LangChain 的核心抽象（知其设计意图）

| 抽象 | 解决的问题 | 适用 |
|------|-----------|------|
| Model I/O（ChatModel） | 统一各家 API 差异 | 多模型切换 |
| Chain / LCEL | 声明式组合调用链 `prompt \| llm \| parser` | 线性流水线 |
| Retrieval（Retriever/VectorStore） | 统一向量库接口 | RAG |
| Tool / Toolkit | 工具封装与 schema 生成 | Agent |
| LangGraph | **图编排**：节点+边+状态+检查点 | 复杂 Agent（见下） |

**批评与应对**：LangChain 被批"过度抽象、版本动荡"——合理用法是只用 Model I/O 和 LangGraph，跳过中间层的过度封装；简单场景直接裸 SDK。

### LangGraph 为什么重要

把 Agent 建模为**状态图**：`State`（共享状态）→ `Node`（LLM/工具/人工节点）→ `Edge`（条件流转）→ `Checkpoint`（可中断、可恢复、可回溯）。这是生产级 Agent 编排的事实标准之一，与 [Graph Engineering](../06-AI-Agent智能体/Agent工程体系总览.md#4-graph-engineering图编排工程) 一脉相承。

## 3. LlamaIndex：RAG 专科生

- 专注"数据 → 索引 → 检索 → 查询引擎"全链路
- 杀手级抽象：`Document/Node`（带元数据的数据单元）、各种 Index（向量/摘要/知识图谱）、`QueryEngine` 一行出 RAG
- 与 LangChain 关系：竞争又互补——RAG 重就用 LlamaIndex，编排重就用 LangGraph，可混用

## 4. Ollama：本地模型的 Docker

```bash
ollama pull qwen3:8b        # 拉模型
ollama run qwen3:8b         # 对话
ollama serve                # 本地 API（兼容 OpenAI 接口，localhost:11434）
```

- 价值：隐私数据不出机、零成本实验、离线可用
- 兼容 OpenAI API → 业务代码零改动切换"本地/云端"
- 选型参考：8B 级模型 16GB 内存可跑（Q4 量化）；代码任务选专门的 coder 模型

## 5. MCP 开发实战（Client 与 Server 两端）

**Server 端**（把能力暴露给所有 Agent）：FastMCP 三个装饰器——`@mcp.tool()`、`@mcp.resource()`、`@mcp.prompt()`，详见 [题库 09](../12-AI面试题库/09-Agent-MCP-Skills专项题库.md) Q12。

**Client 端**（让自己的应用消费 MCP 生态）：
```python
# 伪代码：连接 MCP Server → 拿工具 → 喂给自己的 Agent
client = MultiServerMCPClient({"fs": {"command": "npx", "args": ["-y", "@mcp/fs", "/data"]}})
tools = await client.get_tools()     # 自动转为框架 Tool
agent = create_agent(model, tools)   # 接入你的 LangGraph/自研 Agent
```

**设计经验**：工具描述写给"模型"看不是写给"人"看；错误返回具体原因（帮助模型自我修正）；大结果分页。

## 6. 低代码平台（Dify/Coze）的定位

- 适合：业务验证期（1 天搭出知识库问答给业务方试用）、非研发主导的工具
- 不适合：深度定制（复杂编排、特殊权限、性能调优）、长期维护的核心系统
- 决策框架：**验证用低代码，沉淀用代码**——低代码验证价值成立 → 用代码重写核心链路 → 低代码退居边缘工具

## 7. 技术选型决策树

```
需求是聊天/总结等单轮任务？ → 裸 SDK（50 行搞定）
需要 RAG？ → LlamaIndex 或 裸 SDK + 向量库 SDK
需要多步 Agent/人工审批/可恢复？ → LangGraph / 自研 ReAct 循环
需要对接多种工具生态？ → MCP
给非技术同事用？ → Dify/Coze
数据敏感/离线？ → Ollama 本地模型
```

## 8. 动手作业

1. 用裸 SDK 写一个 20 行的对话脚本，再加 5 行实现"流式输出"
2. 把 [10 目录项目4](../10-AI应用实战/code/project4_agent.py) 的 Agent 加一个自己写的工具（如查天气 mock），观察 ReAct 循环日志
3. 用 FastMCP 把同一个工具包装成 MCP Server，接入 CodeBuddy 使用——体会"一次开发处处可用"
