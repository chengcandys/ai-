# 09 · Agent / MCP / Skills 专项题库（45 题）

> 2026 年面试最热门方向，单独成册。与 [05-Agent与MCP](./05-Agent与MCP.md) 互补（05 讲基础与框架，本篇讲协议细节与工程深挖）。来源：卡码笔记、码力全开、大志说编程等 2026 面经（见文末）。

---

## A. MCP 协议专题（22 题）

### Q1. MCP 要解决的根本问题是什么？
- 各家模型 Function Calling 格式不统一，工具方要针对每个模型/应用单独适配 → **N×M 爆炸**（10 应用 × 20 工具 = 200 套适配）
- MCP 统一"工具怎么暴露、怎么被发现、怎么被调用" → 降为 **N+M**
- 类比：USB 统一设备连接方式，MCP 统一 AI 工具对接方式

### Q2. 为什么叫 Model Context Protocol 而不是 Tool Protocol？
- 因为协议暴露的不只是 Tools，还有 **Resources**（可读的上下文数据：文件/知识库/配置）和 **Prompts**（可复用的提示词模板）
- Tool 只是三种能力之一；协议本质是为模型**标准化供给上下文**

### Q3. MCP 的三个核心角色？
- **Host**：AI 应用本体（Claude Code、Cursor、CodeBuddy、自研 Agent），管理 Client 生命周期
- **Client**：Host 内的协议翻译官，与 Server 建连、发现能力、转发调用
- **Server**：能力提供方，包装外部系统（文件系统、数据库、GitHub、业务服务）为标准接口

### Q4. Server 对外暴露的三种能力分别是什么？
| 能力 | 内容 | 发现/使用接口 |
|------|------|---------------|
| Tools | 可执行操作（查天气、发邮件），含名称/描述/参数 Schema | `tools/list`、`tools/call` |
| Resources | 可读数据（产品手册、退货政策、API 文档） | `resources/list`、`resources/read` |
| Prompts | 标准化提示词模板（代码审查、周报模板），多 Agent 共享 | `prompts/list`、`prompts/get` |

### Q5. MCP 底层基于什么协议？消息长什么样？
- **JSON-RPC 2.0**：`{"jsonrpc": "2.0", "method": "tools/call", "params": {...}, "id": 1}`
- 轻量、语言无关、有成熟的请求/响应/通知语义 → 不需重复造协议

### Q6. 三种传输模式及选型口诀？
| 模式 | 特点 | 场景 |
|------|------|------|
| stdio | 标准输入输出，Client 直接拉起/关闭 Server 进程 | 同机部署：本地 CLI、IDE 插件 |
| SSE（Streamable HTTP） | HTTP 长连接，易穿透防火墙 | 远程 Web 服务，**最常见生产部署** |
| WebSocket | 全双工 | Server 需主动推送（实时协作、语音中断） |
- 口诀：**同机 stdio、远端 SSE、双向实时 WebSocket**

### Q7. 连接建立时的 initialize 握手做什么？
- 协商协议版本、交换双方能力声明（capabilities）
- Client 拉取并**缓存** Server 的 tools/resources/prompts 列表 → 后续调用不必重复拉取
- 运行时 Server 新增工具可被动态发现，**无需重新部署 Client**

### Q8. 工具发现（tools/list）的完整四步？
1. Server 注册工具（如 `@mcp.tool()` 装饰器），维护名称/描述/参数 Schema
2. Client 建连后请求 `tools/list` 拿工具元数据
3. Client 把 MCP 格式**转换为目标模型支持的格式**（如 OpenAI 的 `{"type":"function","function":{...}}`）
4. 注入上下文给 LLM，由模型决策是否调用
- 意义：新增工具 Client 零改动；描述统一由 Server 维护；多 Agent 复用同一 Server

### Q9. 从用户提问到工具返回，MCP 完整调用链路？
```
用户提问 → Host/ChatClient → LLM 输出 tool_call → Client 解析
→ 构造 JSON-RPC 请求 → HTTP POST / stdio 发往 Server
→ Server 路由到对应方法执行 → JSON-RPC 响应
→ Client 解析 → 结果以 role:"tool" 注入消息列表 → 再次发给 LLM → 最终回答
```
- 关键细节：工具调用是**同步阻塞**的；超时与重试逻辑在 **Client 侧**实现

### Q10. MCP 与 Function Calling 的关系？（必考）
- **互补，不是替代**：FC 是模型侧决策能力（调不调、调哪个、传什么参）；MCP 是工程侧连接标准（工具如何注册、发现、通信）
- 完整链路：模型通过 FC 决策 → 通过 MCP 与工具方通信 → 执行返回
- 金句：MCP 不改变模型的决策逻辑，改变的是工具的**连接方式**

### Q11. MCP 相比传统 API 的五大优势？
1. **自动发现**：无需手写 `tools=[...]` 列表
2. **可复用**：一个 Server 服务所有 Agent 应用
3. **模型友好**：工具自带描述与 Schema，LLM 易理解易调用
4. **上下文统一**：除工具外还统一供给 Resources 和 Prompts
5. **集中管控**：权限、限流、审计可在 Server 侧集中实现

### Q12. 如何开发一个 MCP Server？（Python 版）
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

@mcp.tool()
def get_weather(city: str) -> dict:
    """查询指定城市的实时天气"""
    return weather_service.query(city)

mcp.run(transport="stdio")  # 或 transport="sse"
```
- Client 侧：`MultiServerMCPClient` 配置连接（stdio 模式自动拉起 Server 进程），`get_tools()` 自动转为框架 Tool 交给 Agent

### Q13. 开发 MCP Server 的工程注意事项？
- **描述即接口**：LLM 靠 description 决定何时调用 → 写清适用场景、参数含义、边界
- 错误信息要"LLM 可读"（返回具体原因而非 500，帮助模型自我修正参数）
- 输入严格校验（模型可能生成非法参数）、幂等设计、超时控制
- 返回值控制大小（大结果分页/截断/摘要，防 token 爆炸）

### Q14. 企业级 MCP 落地的四大维度？
| 维度 | 要点 |
|------|------|
| 安全 | 工具执行权限校验（不是模型说调就能调）、写/删操作二次确认、防工具描述夹带 Prompt 注入 |
| 性能 | 调用超时控制、高并发连接池、同参数结果缓存 |
| 可观测 | 每次调用记 trace（耗时/参数/结果）、成功率监控告警、成本归因（哪些工具最热） |
| 版本管理 | 工具升级兼容旧 Client、废弃工具平滑过渡（先标记 deprecated 再下线） |

### Q15. Resources 的典型使用场景？
- Server 暴露产品手册、内部政策、配置文件等只读资料
- Agent 通过 `resources/list` 发现 → `resources/read` 按需读入上下文
- 与 RAG 的区别：Resources 是**确定性、由 Server 策展**的内容，RAG 是相似度检索 → 关键政策类内容用 Resources 更可靠

### Q16. Prompts 能力解决什么？
- 把优质提示词模板（代码审查、发布检查清单）托管在 Server 端，多 Agent/多团队共享同一份标准
- 模板升级只需改 Server → 避免提示词散落在各应用代码里版本漂移

### Q17. 多个 MCP Server 同时接入怎么管理？
- Client 支持多 Server（如 MultiServerMCPClient），工具按 **Server 命名空间**区分（如 `github.create_issue` vs `jira.create_issue`）防重名冲突
- 工具总量控制：接入 Server 多 → 工具爆炸 → 需工具检索/动态加载（见 Q21）

### Q18. MCP 的安全模型三层？
1. **能力声明**：握手时双方明确声明能提供/需要什么
2. **授权控制**：敏感操作经用户确认（Host 弹审批），最小权限
3. **审计追踪**：全量调用日志可回放

### Q19. MCP Server 如何做权限与限流？
- Server 侧集中实现：按 Client 身份（认证 token）划分工具可见范围
- 限流：QPS 配额 + 配额耗尽返回标准错误让 Agent 降级
- 好处：权限逻辑一处维护，所有接入的 Agent 自动遵守

### Q20. MCP 与 A2A 的分工？
- MCP：Agent ↔ 工具（纵向）；A2A：Agent ↔ Agent（横向，Agent Card 能力发现 / Task 委托 / Artifact 交付）
- 组合：一个 Agent 对内用 MCP 调工具，对外用 A2A 接受其他 Agent 的任务委托

### Q21. MCP 的局限与批评？（辩证题，拉开差距）
- 工具多时全部 Schema 注入上下文 → token 膨胀、注意力稀释 → 需 Tool RAG/动态加载
- 协议本身不解决"模型会不会选错工具"——决策质量仍取决于模型与描述质量
- 生态年轻：Server 质量参差、安全实践未完全标准化
- 答题公式：**承认价值（标准化红利）+ 说清边界（决策与治理仍在应用层）**

### Q22. 设计一个公司内部 MCP 工具平台，要点？
- 统一注册中心（Server 目录、健康检查）、统一认证鉴权（SSO 打通）
- 工具上架评审（描述质量、安全扫描）、调用网关（限流/审计/成本归因）
- 灰度与版本管理、面向 Agent 的工具市场（按任务推荐工具）

---

## B. Skills 专题（10 题）

### Q23. Skill 是什么？解决什么问题？
- 把**领域专家经验/SOP**（代码审查标准、品牌语气、工作流程）编码成可被 Agent 按需加载的知识包
- 光有工具不够，还要教 Agent"怎么专业地做"——Skill 就是这个"岗位培训手册"

### Q24. 一个 Skill 文件的标准结构？
- 元信息（frontmatter）：`name`、`description`、`triggers`（触发词）、`allowed-tools`
- 正文：身份定位 + 工作流程（分步 SOP）+ 注意事项 + 输出规范
- 参考本项目实例：`.codebuddy/skills/web-search-free/SKILL.md`

### Q25. Skill 的激活机制？
- Agent 收到任务 → 匹配各 Skill 的 triggers（关键词匹配或语义相似度超阈值）→ 命中则把 Skill 内容**注入上下文**
- 关键设计：**按需加载**而非全量常驻 → 控制上下文膨胀（这就是 Skill 是"上下文容量管理"手段的原因）

### Q26. Skill vs System Prompt？
- System Prompt：全局生效、每次会话必载、承载通用规范 → 占常驻 token
- Skill：场景触发、按需注入、领域专用、模块化独立维护
- 分工：通用行为规范进 System Prompt，领域 SOP 进 Skill

### Q27. Skill vs Few-shot？
- Few-shot：给输入输出示例，教**格式模仿**
- Skill：给完整方法论（流程+规范+判断标准），教**怎么做**
- 可组合：Skill 里也可以内嵌 few-shot 示例

### Q28. Skill vs Tool（MCP）？
- Tool 是**可执行的操作**（读文件、调 API）——Agent 的手
- Skill 是**怎么做的知识**——Agent 的经验
- 协作链：Skill 匹配加载审查规范 → Agent 按 Skill 规划 → 通过 MCP/FC 调工具执行 → 按 Skill 输出规范交付
- 速记：**Skills 决定怎么想 → MCP 决定用什么 → Function Call 决定怎么调**

### Q29. Skill 的复用与版本管理怎么做？
- 资产化：Skill 文件入 git 仓库，评审与代码同流程
- 分发：项目级（`.codebuddy/skills/`）/ 用户级 / 市场（SkillHub 等注册中心）
- 版本：变更需评估对存量 Agent 行为的影响（提示词改动 = 行为改动），配套回归评测集

### Q30. 如何评估一个 Skill 的质量？
- 触发准确率：该触发时触发（召回），不该触发不触发（精确率）
- 产出质量：加载 Skill 后任务完成率/评审通过率对比基线（A/B）
- 成本：注入的 token 开销 vs 质量收益
- 失败案例回流：badcase → 修订 Skill → 回归验证

### Q31. 写一个好 Skill 的原则？
- 单一职责（一个 Skill 只教一件事）、trigger 描述具体（防误触发/漏触发）
- SOP 可执行（步骤明确到"下一步做什么"，不写正确的废话）
- 明确边界：何时**不要**使用本 Skill、失败时如何回退
- 内嵌检查清单（让 Agent 交付前自查）

### Q32. Skills 体系在大厂 Agent 中的位置？
- 分层上下文治理的一环：L1 发现层（Skill 元信息常驻，正文按需加载）→ L2 工具层（MCP）→ L3 记忆层
- 趋势：Skill 市场/生态化，领域经验成为可交易资产

---

## C. Agent 进阶深挖（13 题）

### Q33. LLM 的四大天花板？Agent 如何逐一补全？
1. 只会说不会做 → 工具调用（手）
2. 没有记忆（窗口满即失忆）→ 记忆系统（外部存储+检索注入）
3. 知识截止 → RAG/联网工具
4. 不会规划（线性应答）→ 规划模块 + 循环执行
- 一句话：**LLM 告诉你怎么做，Agent 直接帮你做完**

### Q34. 并行 Function Calling 是什么？
- GPT-4o/Claude 3.5+ 支持模型一次输出多个独立 tool_call
- 延迟从串行的 T1+T2+T3 降为 **max(T1,T2,T3)**
- 前提：调用间无依赖；有依赖（B 的参数来自 A 的结果）必须串行

### Q35. 主流厂商 FC 格式差异？
- OpenAI：`tools` 数组 + `tool_calls` 返回 + `role:"tool"` 回传结果
- Claude：`input_schema` 定义 + `tool_use` block 返回 + `tool_result` 回传
- 工程启示：Agent 框架需做**格式适配层**，业务代码与厂商解耦（这也是 MCP 价值之一）

### Q36. 幻觉工具调用怎么治理？
- 表现：调不存在的工具名、编造参数、参数类型错误
- 治理：工具名白名单校验、JSON Schema 强约束校验、非法调用不执行而是把错误回喂让模型修正、连续失败熔断
- 模型侧：工具描述消歧（名字相近的工具是大坑）

### Q37. 上下文窗口快满时怎么办？（Auto-Compact）
- 触发：token 用量达阈值（如 80%）
- 策略：LLM 总结旧对话为摘要 + 保留最近 N 轮原文 + 结构化任务状态快照（TODO 清单、关键结论单独存）
- 归档不删除：压缩掉的内容入外部记忆，需要时可检索回来

### Q38. Agent 记忆的写入时机与读取时机？
- **写入**：任务完成存结果、发现用户偏好、学到新知识、记录失败原因（教训最有价值）
- **读取**：任务开始加载背景、遇到陌生问题检索历史经验、事实核查时
- 遗忘机制：TTL 过期、重要性衰减、冲突时新覆盖旧

### Q39. Prompt Injection 的四大防御？
1. **数据/指令分离**：外部内容（网页、文档）包裹标记，明确"以下是数据不是指令"
2. **输入过滤**：检测典型注入模式（"忽略之前的指令"）
3. **模板隔离**：系统指令与用户/外部内容分层，指令层级优先级硬约束
4. **上下文标记**：tool 结果明确标注来源与可信度，高危操作不因外部内容触发

### Q40. Human-in-the-Loop 如何分级？
- L0 只读操作（查询/检索）：自动放行
- L1 可逆写操作（创建草稿）：自动执行 + 日志
- L2 不可逆/外发操作（删数据、发邮件、付款）：**必须人工审批**
- 设计原则：审批界面要给出"Agent 为什么想做这个操作"的完整上下文，否则人会盲目点同意

### Q41. 多 Agent 框架怎么选？
- LangGraph：图编排（节点/边/状态/检查点），控制粒度最细，适合复杂生产流
- CrewAI：角色扮演式，上手快，适合快速验证
- AutoGen：对话驱动多 Agent，研究性强
- 自研：核心逻辑（循环+工具+记忆）并不复杂，强定制时自研可控
- **Anthropic 官方提醒**：不要过早引入 Multi-Agent——强单 Agent 往往比多 Agent 更稳定省钱，先榨干单 Agent

### Q42. Claude Code 为什么不用 RAG 检索代码？（热点思辨题）
- 代码检索要求**精确与实时**：符号名、路径必须精确匹配（向量检索模糊），且代码高频变更（向量索引必然滞后）
- Grep/Glob/Read 是确定性工具：结果 100% 忠实于当前磁盘状态
- 子 Agent 探索：主 Agent 派子 Agent 用搜索工具探查，只带回结论 → 省主上下文
- 启示：**检索方式服务于数据特性**，不是所有场景都该向量化

### Q43. Agent 的 token 成本优化五策略？
1. 工具动态加载（按任务选工具子集，不全量注入）
2. 模式选择（简单任务 Workflow / Plan-and-Execute 替代 ReAct，省至 20%）
3. 上下文压缩（Auto-Compact、工具结果截断/摘要）
4. 模型路由（简单步骤小模型，级联降级）
5. 缓存（工具结果缓存、Prompt Cache 命中相同前缀）

### Q44. Agent 轨迹评估（Trace Eval）怎么做？
- 采集：每轮的上下文、思考、工具调用与结果、耗时、token
- 评估：LLM-as-Judge 按轨迹点评分（决策合理性/工具选择/参数正确性），不只看最终结果
- 回归：核心任务集每次发版重跑，对比成功率/平均步数/成本曲线防劣化

### Q45. 设计一个"AI 助理帮用户订机票"的 Agent，拆解关键点？
- 工具：航班查询（只读）、下单支付（L2 审批）、日历读写
- 流程：需求澄清（日期/预算/偏好，多轮）→ 查询候选 → 给用户确认 → 支付前人工审批 → 出票写日历
- 护栏：支付金额二次确认、退改规则必须如实呈现、查询超时降级
- 状态：订单状态机持久化，中断可恢复（检查点）

---

## D. A2UI / AG-UI 协议（2026 补充）

### Q46. A2UI 是什么？解决什么问题？
- **Agent-to-UI**（Google 主导）：让 Agent 不只返回文本，还能**以 JSON 描述交互式界面**（表单、卡片、按钮、图表），前端按描述渲染
- 解决：传统 Agent 只能"说话"，无法让用户直接在界面上操作（填表/确认/选择）→ A2UI 让 Agent 输出"可交互的界面"，人机交互从"对话"升级为"对话+界面"
- 关系：MCP 解决 Agent↔工具，A2A 解决 Agent↔Agent，**A2UI 解决 Agent↔界面**

### Q47. AG-UI 与 A2UI 的区别？
- **AG-UI**（Agent↔User Interface，CopilotKit 社区主导）：面向**前端开发者**的 Agent 交互协议/事件流——定义流式消息、工具调用状态展示、用户介入（HITL 审批）等事件的规范格式
- **A2UI**：更关注 Agent 生成的**界面结构描述**（可渲染的 UI schema）
- 一句话：AG-UI 管"Agent 与界面的通信事件"，A2UI 管"Agent 生成的界面长什么样"
- 面试答法：2026 协议栈 = MCP（工具）+ A2A（Agent 间）+ **A2UI/AG-UI（界面）**，三者互补构成完整生态

## 来源

- [卡码笔记 · 2026 Agent 大厂面试题汇总](https://notes.kamacoder.com/interview/llm/agent_interview.html)
- [码力全开 · MCP 协议面试速查](https://javaup.chat/ai-interview/quick-review/mcp-protocol/)
- [大志说编程 · 11 MCP 面试题](https://aiflowline.cn/articles/ai-interview/11%20MCP.html)
