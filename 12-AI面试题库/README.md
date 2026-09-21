# 12 · AI 面试题库

> 网上收集整理（来源见文末）+ 系统化补充，覆盖机器学习、深度学习、LLM 全栈高频面试题，共 150+ 题，均附回答要点。

## 题库索引

| 文件 | 专题 | 题量 |
|------|------|------|
| [01-机器学习与深度学习基础](./01-机器学习与深度学习基础.md) | 八股文核心：拟合、优化器、损失函数、CNN/RNN、评估指标 | 25 |
| [02-Transformer与LLM原理](./02-Transformer与LLM原理.md) | 注意力机制、位置编码、架构选择、KV Cache | 25 |
| [03-预训练微调与对齐](./03-预训练微调与对齐.md) | 预训练、SFT、RLHF、DPO、LoRA/QLoRA | 20 |
| [04-RAG与知识库](./04-RAG与知识库.md) | 切分、Embedding、混合检索、Rerank、GraphRAG、幻觉治理、ANN 索引 | 30 |
| [05-Agent与MCP](./05-Agent与MCP.md) | ReAct、Function Calling、MCP、多 Agent、漂移与成本治理 | 31 |
| [09-Agent-MCP-Skills专项题库](./09-Agent-MCP-Skills专项题库.md) | **MCP 协议 22 题 + Skills 10 题 + Agent 进阶 13 题**，2026 最热方向专项 | 45 |
| [06-推理部署与工程落地](./06-推理部署与工程落地.md) | 量化、推理加速、vLLM、系统设计题 | 20 |
| [07-项目与开放题](./07-项目与开放题.md) | 项目深挖清单、场景设计、行为面、反问环节 | 15+ |
| [08-核心题深度解析](./08-核心题深度解析.md) | **15 道最高频题的满分答题范本**：推导+追问链+答题框架 | 15（精读） |

## 大厂面试考察逻辑（先懂规则再刷题）

面试官重点看四个维度：

1. **基础认知扎实度** —— 是否理解本质，而非背话术（追问"为什么"）
2. **工程落地实战能力** —— 能否解决实际问题（"幻觉率从多少降到多少，怎么做的"）
3. **问题解决闭环思维** —— 拆解问题 → 设计方案 → 验证效果 → 迭代优化
4. **行业前瞻认知** —— 对新架构/趋势（MoE、Mamba/SSM、推理模型）有独立思考

## 不同岗位考察侧重点

| 岗位 | 高频考点 |
|------|----------|
| 预训练/对齐算法岗 | Transformer 演进、数据治理、RLHF/DPO、分布式训练、收敛优化 |
| 推理优化/工程岗 | 量化、注意力优化、KV Cache、批处理、端侧优化、推理框架二开 |
| 应用落地/解决方案岗 | RAG 全链路、Agent 架构、幻觉缓解、垂直领域适配、合规管控 |
| 多模态算法岗 | 视觉编码器选型、跨模态对齐、多模态幻觉、视频生成 |

## 刷题建议

1. 先按岗位方向锁定 2~3 个专题精读，其余泛读
2. 每题先自己口述答案再看要点，训练"讲得出来"而非"看得懂"
3. 配合 [07-项目与开放题](./07-项目与开放题.md) 准备自己的项目故事线
4. 面试前让「AI学习小能手」对本题库做模拟面试（它提问你回答，再点评）

## 资料来源（持续更新）

- [2026最全大模型面经汇总 · 卡码笔记/代码随想录](https://notes.kamacoder.com/interview/llm/)（Agent/RAG/Transformer/Vibe Coding 专题）
- [大语言模型高频面试题及答案汇总 · 极客日志](https://zeeklog.com/da-yu-yan-mo-xing-llm-gao-pin-mian-shi-ti-ji-da-an-hui-zong-zi-jie-a-li-teng-xun-aigang-tong-guan-bi-bei)
- [2025 大模型面试 50 题 · CSDN](https://blog.csdn.net/qq_46094651/article/details/149446967)
- [万字秋招算法岗深度学习八股文大全 · 知乎](https://zhuanlan.zhihu.com/p/667048896)
- [AI算法岗面试八股面经超全整理 · CSDN](https://blog.csdn.net/weixin_46570668/article/details/142419167)
- [2026 AI大模型面试题汇总 · 知乎](https://zhuanlan.zhihu.com/p/2049800621813917294)
- [LLM & Agent 面试准备 · GitHub](https://github.com/HyperAndy/llm-agent-interview-prep)

> 最新面经（如字节 Agent 岗 21 题）会随行业变化，建议定期让 agent 用 web-search-free 检索补充。
