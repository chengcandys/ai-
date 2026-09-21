# AI 核心术语表（速查手册）

> 按场景分组，一句话解释 + 类比。遇到生词先查这里，仍不懂就问「AI学习小能手」。

## 一、基础概念

| 术语 | 一句话解释 |
|------|-----------|
| Model 模型 | 训练得到的"智能程序"，本质是巨量参数构成的数学函数 |
| Parameter 参数 | 模型内部的可学习数值权重，规模常以 B（十亿）计 |
| Training 训练 | 用数据调整参数、降低损失的过程 |
| Inference 推理 | 用训练好的模型做预测/生成 |
| Token | 模型处理文本的最小单位（1 汉字 ≈ 1~2 token） |
| Prompt | 给模型的输入指令 |
| Context Window 上下文窗口 | 模型一次能看到的最大 token 数（类比：工作记忆/RAM） |
| Hallucination 幻觉 | 模型编造看似合理但错误的内容 |
| Emergent Ability 涌现能力 | 规模跨过阈值后突然出现的未显式训练的能力 |
| Alignment 对齐 | 让 AI 行为符合人类意图与价值观 |
| AGI | 通用人工智能，各领域达人类水平的假想 AI |
| Multimodal 多模态 | 同时处理文本/图像/音频/视频多种信息形态 |

## 二、模型与训练

| 术语 | 一句话解释 |
|------|-----------|
| Transformer | 现代 AI 基石架构，核心是自注意力机制 |
| Attention 注意力 | 让每个 token 动态计算对其他 token 的关联权重 |
| Q/K/V | 注意力的三要素：查询/键/值（"找什么/是什么/携带什么"） |
| RoPE | 旋转位置编码，主流位置编码方案，支持长文本外推 |
| KV Cache | 推理时缓存历史 K/V，避免重复计算（换显存） |
| Pretrain 预训练 | 海量文本自监督学习"预测下一个词" |
| SFT | 监督微调，用指令数据教模型对话格式 |
| RLHF | 人类反馈强化学习，用偏好数据对齐 |
| DPO | 直接偏好优化，免奖励模型的简化对齐法 |
| GRPO | 组相对策略优化，DeepSeek-R1 训推理能力用的 RL 算法 |
| LoRA | 低秩适配微调：冻结原权重只训小矩阵，成本骤降 |
| QLoRA | 基座 4bit 量化 + LoRA，单卡微调大模型 |
| MoE 混合专家 | 每 token 只激活部分"专家"参数，总参大激活小 |
| Distillation 蒸馏 | 用大模型的输出教小模型 |
| Scaling Law | 性能与参数/数据/算力的幂律关系 |
| Chinchilla 定律 | 参数与数据应同步扩（约 1:20 token/参数） |
| Catastrophic Forgetting 灾难性遗忘 | 微调后丢失预训练的通用能力 |
| 冷启动 | 用少量 CoT 数据 SFT 后再上 RL（R1 路线） |

## 三、推理与部署

| 术语 | 一句话解释 |
|------|-----------|
| Temperature 温度 | 采样随机性：0 稳定保守，越大越发散 |
| Top-p / Top-k | 采样候选池截断策略（核采样/前 k 采样） |
| Beam Search | 保留多条候选路径的解码（翻译类任务常用） |
| Greedy 贪心解码 | 每步取概率最高 token，稳定但易复读 |
| Quantization 量化 | 权重降精度（FP16→INT8/4），省显存提速 |
| Prefill / Decode | 推理两阶段：并行处理输入 / 逐 token 生成 |
| TTFT / TPOT | 首 token 延迟 / 每 token 延迟 |
| Throughput 吞吐 | 单位时间处理的 token 数 |
| vLLM | 高吞吐推理框架，核心创新 PagedAttention |
| PagedAttention | 借鉴操作系统分页管理 KV Cache，减少显存碎片 |
| Continuous Batching | 连续批处理：请求随到随插，提高 GPU 利用率 |
| Speculative Decoding 投机采样 | 小模型草拟、大模型验证，无损加速 2-3 倍 |
| Ollama | 本地跑开源模型的工具 |

## 四、应用与工程

| 术语 | 一句话解释 |
|------|-----------|
| RAG | 检索增强生成：先检索资料再让模型作答（开卷考试） |
| Embedding | 文本的向量化表示，语义近则向量近（"语义坐标"） |
| Chunking 切分 | 把文档切成小段入库，大小影响检索质量 |
| Rerank 重排序 | 粗排后精细重排（Bi-Encoder → Cross-Encoder） |
| Hybrid Search 混合检索 | 向量语义 + BM25 关键词双路召回 |
| GraphRAG | 知识图谱增强的 RAG，擅长全局性问题 |
| Agent 智能体 | LLM + 规划 + 记忆 + 工具，能自主多步执行 |
| Function Calling | 模型输出结构化工具调用请求（模型不执行，只表达意图） |
| MCP | 模型上下文协议，统一工具接入标准（AI 界的 USB-C） |
| A2A | Agent 间协作协议（横向），与 MCP（纵向）互补 |
| Skill | 按需加载的领域 SOP 知识包（"岗位培训手册"） |
| ReAct | 思考→行动→观察的 Agent 经典循环模式 |
| Workflow vs Agent | 流程写死在代码 vs 路径由模型自主决策 |
| HITL | 人在回路：高风险操作人工审批 |
| Prompt Injection 提示注入 | 外部内容夹带恶意指令劫持 Agent |
| Context Engineering 上下文工程 | 在合适时机给模型看正确且必要的信息 |
| Harness 外壳工程 | 模型之外的整套系统工程（Agent = Model + Harness） |
| Loop Engineering 循环工程 | Agent 自我触发、跨会话自主运行（cron/事件驱动） |
| AGENTS.md | 给 Agent 看的项目说明书（目录式，每行对应一个历史坑） |

## 五、评估与安全

| 术语 | 一句话解释 |
|------|-----------|
| Benchmark 基准 | 标准化评测集（MMLU、HumanEval、C-Eval） |
| Perplexity 困惑度 | 语言模型指标，"平均在几个词间犹豫"，越低越好 |
| LLM-as-Judge | 用强模型给输出自动打分 |
| Faithfulness 忠实度 | RAG 答案与检索内容的一致程度 |
| Red Teaming 红队 | 上线前系统性攻击自己的模型找漏洞 |
| Jailbreak 越狱 | 绕过安全限制诱导模型输出违禁内容 |
| Reward Hacking | 模型钻奖励函数空子而非真正变好 |
| Guardrail 护栏 | 输入输出的安全过滤与规则拦截 |
| Deepfake 深度伪造 | AI 生成的以假乱真音视频 |
| Data Contamination 数据污染 | 评测集泄露进训练数据导致分数虚高 |

## 使用建议

1. 第一遍通读混个脸熟，之后当字典查
2. 每个术语都能在主目录找到深入讲解（见词尾分类对应 01~13 目录）
3. 自测：随机抽 10 个术语，能用自己的话讲清楚 + 举一个应用场景即过关
