# 实战项目配套代码

> 全部代码可直接运行（Python 3.9+），默认使用 OpenAI 兼容接口（DeepSeek/通义/Ollama 均可，改 `BASE_URL` 和 `MODEL` 即可）。

## 准备

```powershell
pip install openai chromadb
# 设置密钥（以 DeepSeek 为例；用 Ollama 则无需密钥，BASE_URL 改为 http://localhost:11434/v1）
$env:OPENAI_API_KEY="sk-你的key"
```

| 文件 | 对应项目 | 运行 | 依赖 |
|------|----------|------|------|
| `project1_prompt_templates.md` | 项目1 Prompt 工具箱 | 直接用（复制到任意 AI 对话） | 无 |
| `project2_chatbot.py` | 项目2 API 聊天机器人 | `python project2_chatbot.py` | openai |
| `project3_rag.py` | 项目3 知识库 RAG 问答 | `python project3_rag.py` | openai, chromadb |
| `project4_agent.py` | 项目4 带工具的 Agent | `python project4_agent.py` | openai |
| `project5_multi_agent.py` | **扩展：多 Agent 协作**（主从编排+并行研究+去重+生成评审分离） | `python project5_multi_agent.py` | openai |
| `project6_hitl.py` | **扩展：人机交互 HITL**（澄清/计划确认/分级审批/升级转交/审计日志） | `python project6_hitl.py` | 无模型依赖（可离线跑） |
| `project7_agent_patterns.py` | **扩展：设计模式对比实验**（Chaining/Routing/Parallel/Reflection 同任务对比 token 成本） | `python project7_agent_patterns.py` | openai |
| `project8_dynamic_permissions.py` | **扩展：动态权限演示**（风险分级/PEP 拦截/权限滑块/JIT 三级授权记忆/注入自动降权/审计） | `python project8_dynamic_permissions.py` | 无模型依赖（可离线跑） |

> `project8` 审计日志写入 `code/permissions_audit.log`。

> `project5` 产出写入 `code/output/multi_agent_report.md`；`project6` 审计日志写入 `code/hitl_audit.log`。

## 配置说明

每个文件顶部的三个常量：

```python
BASE_URL = "https://api.deepseek.com/v1"   # DeepSeek；Ollama 用 http://localhost:11434/v1
API_KEY  = os.environ["OPENAI_API_KEY"]    # Ollama 可填任意字符串
MODEL    = "deepseek-chat"                 # Ollama 用 qwen3:8b 等本地模型名
```

## 学习建议

1. 先跑通，再逐行读懂，最后动手改（每个文件末尾有"改造作业"注释）
2. 项目 3 跑通后按 [RAG进阶实战](../../07-RAG与知识库/RAG进阶实战.md) §3 做增强实验
3. 遇到报错先自查三件套：API Key 是否有效、BASE_URL 是否带 `/v1`、模型名是否存在
