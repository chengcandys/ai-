# 05 · Agent 与 MCP（25 题）

## Agent 基础

### Q1. 什么是 AI Agent？与纯 LLM 调用的区别？
- Agent = LLM（大脑）+ 规划 + 记忆 + 工具调用 + 多步执行的闭环系统
- 纯 LLM：一问一答，无状态无行动；Agent：感知-决策-行动-观察循环，直到完成任务

### Q2. ReAct 模式是什么？
- Reasoning + Acting：循环执行 `思考(Thought) → 行动(Action) → 观察(Observation)`
- 思考决定调什么工具，观察结果再决定下一步 → 把"推理"和"行动"交织
- 面试追问：ReAct vs Plan-and-Execute（先整体规划再逐步执行，适合步骤明确的任务；ReAct 更灵活应对不确定环境）

### Q3. Agent Loop 到底在循环什么？（Loop Engineering）
- 五类治理对象：**上下文**（每轮塞什么）、**状态**（任务进度快照）、**预算**（token/轮次/成本上限）、**工具**（本轮可用哪些）、**终止条件**（何时停）
- 答题结构：循环本身简单，工程难点在这五个治理维度

### Q4. Agent 的核心组件有哪些？
- 规划 Planning（任务拆解、反思 Reflexion、自我批评）
- 记忆 Memory（短期=上下文窗口；长期=向量库/结构化存储）
- 工具 Tools（Function Calling、MCP）
- 行动与观测（执行结果回注上下文）

### Q5. Agent 的记忆系统怎么设计？（字节面经真题：三层记忆）
- **短期记忆**：当前会话上下文（需 Auto-Compact 压缩防溢出）
- **中期/情景记忆**：会话摘要、任务状态快照，可跨轮恢复
- **长期记忆**：用户偏好、历史结论，向量库存储 + 检索注入
- 关键问题：写什么、何时写、如何检索、如何遗忘（TTL/重要性衰减）

## Function Calling 与工具

### Q6. Function Calling 的原理？
1. 把工具 schema（名称/参数/描述）注入 prompt
2. LLM 判断需要工具时输出结构化调用请求（JSON）
3. 外层程序真正执行，把结果喂回 LLM
4. LLM 基于结果继续生成
- 考点：**LLM 只生成调用意图，不执行**；执行与权限控制在外层

### Q7. 工具调用失败怎么兜底？
- 重试（指数退避）+ 参数自修正（把报错回喂让 LLM 改参数）
- 降级链：主工具失败 → 备用工具 → 返回"无法完成"并说明原因
- 关键：所有工具调用要幂等设计、超时控制、结果校验

### Q8. 工具数量很多时怎么办？
- 全量塞进 prompt 会稀释注意力 + 烧 token
- 方案：工具检索（Tool RAG，按任务语义选 Top-N 工具）、分层工具命名空间、路由 Agent 分派

### Q9. 如何防止 Agent 调用工具造成危险操作？
- 权限分级：只读工具默认放行，写/删/支付类需人工审批（Human-in-the-Loop）
- 参数校验 + 白名单；沙箱执行（代码解释器隔离环境）
- 完整审计日志（谁在何时因为什么调用了什么）

## MCP

### Q10. MCP 是什么？解决什么问题？
- Model Context Protocol：Anthropic 提出的开放协议，统一 LLM/Agent 与外部工具、数据源的连接标准（类比 USB-C）
- 解决 N×M 问题：M 个模型对接 N 个工具不再需要 M×N 个定制集成，各实现一次协议即可互通

### Q11. MCP 的架构组成？
- **MCP Host/Client**：Agent 端（如 CodeBuddy、Claude Desktop），发现与调用能力
- **MCP Server**：暴露三类能力——Tools（可执行操作）、Resources（可读数据）、Prompts（提示模板）
- 传输：stdio（本地进程）/ HTTP+SSE（远程）

### Q12. MCP 与 Function Calling 的关系？
- 互补不替代：Function Calling 是 LLM 表达"我要调工具"的能力；MCP 是工具被标准化封装与分发的协议
- 实践中：Agent 通过 MCP 发现工具 → 转为 Function Calling schema 给 LLM → LLM 决策调用 → Client 转发给 MCP Server 执行

### Q13. 自己实现一个 MCP Server 要注意什么？
- 工具描述写清楚（LLM 靠描述决定何时调用）、参数 schema 严格、错误信息要"LLM 可读"（帮助它自我修正）
- 安全：输入校验、最小权限、超时控制

## 多 Agent

### Q14. 为什么需要多 Agent？单 Agent 不够吗？
- 单 Agent 上下文有限，装不下所有领域知识；职责混杂导致 prompt 臃肿、质量下降
- 多 Agent：分角色（研究/编码/评审）→ 各自上下文聚焦、可并行、可插拔
- 代价：通信开销、状态一致性、成本翻倍 → **能单 Agent 别硬上多 Agent**

### Q15. 多 Agent 编排模式有哪些？
- **主从式（Orchestrator-Worker）**：Lead 拆解分派，Worker 汇报（Claude Code 子代理、CodeBuddy Team）
- **流水线式**：A 的输出是 B 的输入（写稿→审校→排版）
- **对等协作/辩论式**：多 Agent 互相 critique 提升质量
- 图编排（Graph Engineering）：节点=Agent/工具，边=流转条件，支持检查点、并行、人工审批

### Q16. 多 Agent 之间怎么通信？
- 消息机制：异步信箱/消息队列，主 Agent 路由
- 共享状态：黑板模式（共同读写结构化状态）
- 考点：通信协议要结构化（防自由文本误解）、控制广播风暴

## 生产化难点

### Q17. Agent 漂移（Drift）与幻觉怎么识别和治理？
- **任务漂移**：多轮后偏离原始目标 → 定期回看原始需求（goal re-anchoring）、任务清单（TODO）机制
- **上下文幻觉**：上下文中错误信息被当成事实持续放大 → 状态快照、关键事实结构化存储而非依赖长文本
- **注意力稀释**：上下文过长工具描述被忽略 → 上下文压缩、工具动态加载
- 兜底：输出校验器（schema 校验/规则检查）、关键步骤人工审批

### Q18. Agent 的成本怎么治理？
- 预算机制：单任务 token/轮次/时长上限，超限终止或降级
- 模型路由：简单步骤用小模型（规则路由/模型路由/混合级联），难步骤才上大模型
- 缓存：重复子任务结果缓存；并行化减少总时长

### Q19. 如何评估一个 Agent 系统？
- 轨迹评估（Trace）：每一步决策是否合理，而非只看最终结果
- 端到端：任务完成率、平均步数、token 成本、人工介入率
- 工具层：调用成功率、参数正确率
- 方法：LLM-as-Judge 评轨迹 + 关键指标回归测试集（防 Prompt 改动劣化）

### Q20. Agent 可观测性怎么做？
- 记录完整 Trace：每轮输入上下文、思考、工具调用与结果、耗时、token 消耗
- 可回放调试；按 trace 聚合找高频失败点
- 工具：LangSmith、Langfuse、OpenTelemetry

### Q21. 什么是 Skill（技能）机制？
- 把领域 SOP/知识/脚本打包成可被 Agent 按需加载的技能包（如本项目 `.codebuddy/skills/`）
- 价值：prompt 资产化复用、按需加载省上下文、版本化管理
- 考点：Skill vs Tool——Tool 是可执行操作，Skill 是"教 Agent 怎么做事"的知识包

### Q22. Prompt Engineering → Context Engineering → Harness Engineering 的演进？
- Prompt：写好一段话；Context：动态管理每轮喂给模型的全部信息（记忆/检索/工具结果/历史压缩）
- Harness（脚手架）：围绕模型的整套系统工程——工具治理、状态管理、循环控制、可观测、评测闭环
- 金句：**模型能力趋同后，竞争力在 Harness 工程**

### Q23. 设计一个能自动修复 bug 的 coding Agent，架构怎么设计？（系统设计）
- 循环：读报错 → 检索相关代码 → 生成补丁 → 跑测试 → 失败则分析新报错重试（限轮次）
- 关键点：代码检索（为什么 Claude Code 用 Grep/Glob 而非 RAG——代码检索需要精确与实时，向量索引滞后）、沙箱跑测试、变更最小化、git 分支隔离与回滚

### Q24. Vibe Coding 落地最大的坑？（AI 编程热点题）
- 无审查直接提交 → 必须 diff review；AI 改数据库/删文件 → 备份与权限
- 上下文不足导致"看着对其实错" → Spec-Driven Development：先写规格/计划/任务再让 AI 实现，验证驱动
- Token 成本失控 → 小步任务拆分、及时新开会话

### Q25. Agent 时代程序员的核心竞争力是什么？（开放题）
- 需求拆解与规格表达能力（把模糊需求变成可验证的任务）
- 审查与验证能力（AI 产出的质量守门员）
- 系统设计能力（AI 擅长局部实现，架构权衡仍靠人）
- 领域深度（判断 AI 答案对错的前提）

## 2026 新增真题（联网补充）

### Q26. Agent 和 Workflow 的本质区别？
- 控制权：Workflow 在代码（流程写死，LLM 是节点处理器）；Agent 在 LLM（自主决策每步）
- 量化：Agent token 消耗约为 Workflow 的 4~8 倍
- 生产主流是**混合架构**：Workflow 保底主链路 + Agent 处理开放分支 + 高危节点人工审批
- 判断标准："路径可枚举性"——步骤能预先枚举用 Workflow，依赖中间结果动态决策用 Agent

### Q27. ReAct 死循环怎么防？
1. **最大步数限制**（常用 15 步，超限强制总结退出）
2. **重复动作检测**（连续 3 次相同 tool+args 判定卡死）
3. **超时控制**（墙钟上限）
- 配套：简单固定任务用 Plan-and-Execute，token 消耗约为 ReAct 的 20%

### Q28. Reflection（反思）模式是什么？适用场景？
- 生成 Agent 产出 → 评审 Agent 批判 → 生成 Agent 修订，循环至达标
- 适用：质量优先于成本的任务（代码生成、法律文书）；也可用于幻觉自校正
- 代价：token 翻倍、延迟翻倍 → 不适合实时对话

### Q29. A2A 协议是什么？与 MCP 的关系？
- MCP 解决 Agent↔工具（纵向），A2A 解决 Agent↔Agent（横向）：能力发现（Agent Card）、任务委托（Task 生命周期）、成果交付（Artifact）
- 关系：互补——Agent 内部用 MCP 调工具，Agent 之间用 A2A 协作；均基于 HTTP+JSON+SSE

### Q30. Skills 与 System Prompt、Few-shot 的区别？
- System Prompt：全局生效、每次加载、通用规范
- Skills：**按需激活**（trigger 匹配）、领域方法论（工作流程+规范+标准）、模块化独立维护
- Few-shot 教格式（给示例模仿），Skills 教方法论（完整 SOP）

### Q31. 生产环境 Agent 五大坑？
1. 死循环 → 步数上限+重复检测
2. 幻觉工具调用（调不存在的工具）→ 工具名严格校验、schema 强约束
3. 上下文污染 → 任务边界重置、状态快照
4. Token 爆炸（工具返回超大数据）→ 输出截断+分页
5. Prompt Injection → 数据/指令分离、内容标记、高危操作审批
