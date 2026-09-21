"""
项目5：多 Agent 协作（主从编排 + 并行研究 + 生成/评审分离 + 去重）

架构：
    Lead（规划拆解）
      ├─ 研究员A ─┐
      ├─ 研究员B ─┴─ 并行执行（各自独立上下文，只回传结论）
      ↓ 去重合并（去重 Agent 职责）
      ├─ 撰稿人（生成初稿）
      ↓
      └─ 评审员（独立评审）→ 不通过则修订（最多 2 轮）

核心设计点：
1. 子 Agent 上下文隔离：每个 Agent 只拿到"任务 + 背景 + 验收标准"
2. 工件传递：用 state dict 传结论，不用对话历史
3. 去重：并行 Agent 结果必须合并去重
4. 生成/评审分离：评审 Agent 只看产物不看生成过程

运行：python project5_multi_agent.py
"""
import os
import json
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"  # Ollama 改 http://localhost:11434/v1
API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
MODEL = "deepseek-chat"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def llm(system: str, user: str, temperature: float = 0.3) -> str:
    """所有 Agent 共用的最小调用封装"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
    )
    return resp.choices[0].message.content


# ---------------- 模拟工具（真实场景换成搜索 API / MCP Server） ----------------
MOCK_WEB = {
    "大模型推理成本": "2025 年后 KV Cache 量化与投机采样把推理成本降低数倍",
    "Agent 落地瓶颈": "可靠性（错误累积）与成本（多 Agent 4~15 倍 token）是主要瓶颈",
    "RAG 效果提升": "混合检索 + Rerank 可把 Top-5 召回从约 70% 提升到约 90%",
    "Agent 成本优化": "工具动态加载、上下文压缩、模型路由、结果缓存、模式选择是五条主线",
}


def web_search(query: str) -> str:
    """模拟检索：返回与查询字面最相关的 2 条知识（演示用）"""
    hits = [v for k, v in MOCK_WEB.items() if any(ch in k for ch in query)][:2]
    return "\n".join(hits) if hits else "（本次检索无结果，请换关键词或说明资料不足）"


# ---------------- 各角色 Agent ----------------
def agent_lead_plan(topic: str) -> list[str]:
    """Lead：把大问题拆成互斥且穷尽的子问题"""
    out = llm(
        "你是团队 Lead，负责把研究主题拆解为 2-3 个互不重叠的子问题。",
        f"主题：{topic}\n只输出 JSON 数组，如 [\"子问题1\", \"子问题2\"]",
    )
    try:
        subs = json.loads(out.strip().strip("```json").strip("```"))
        return subs[:3] if isinstance(subs, list) else [topic]
    except Exception:
        return [topic]


def agent_researcher(sub_question: str) -> dict:
    """研究员：独立上下文，只回传结论+来源（不回传原始材料）"""
    raw = web_search(sub_question)
    points = llm(
        "你是研究员。基于给定资料提炼要点，资料不足要明说。"
        "每条要点一行，末尾标注来源关键词。",
        f"子问题：{sub_question}\n资料：\n{raw}",
    )
    return {"sub_question": sub_question, "points": [p for p in points.splitlines() if p.strip()]}


def agent_dedup(results: list[dict]) -> list[str]:
    """去重 Agent：并行研究的必需环节，合并重复结论"""
    merged = "\n".join(f"- {p}" for r in results for p in r["points"])
    out = llm(
        "你是信息去重员。合并重复观点，保留信息量最大的表述，不改写事实。"
        "每条一行，最多 8 条。",
        merged,
    )
    return [line.strip("- ").strip() for line in out.splitlines() if line.strip()]


def agent_writer(topic: str, points: list[str]) -> str:
    """撰稿人：只基于给定要点写作，不允许引入外部信息"""
    return llm(
        "你是技术撰稿人。仅使用提供的要点写作，不得引入新事实。"
        "结构：一句话结论 + 3-5 条要点解析 + 一句话建议。",
        f"主题：{topic}\n要点：\n" + "\n".join(f"- {p}" for p in points),
    )


def agent_critic(topic: str, draft: str) -> dict:
    """评审员：只看产物本身（生成/评审分离）"""
    out = llm(
        "你是严格的技术评审。检查：结论是否有支撑、是否遗漏关键权衡、是否有未标注的猜测。"
        '只输出 JSON：{"pass": true/false, "issues": ["问题1"]}',
        f"主题：{topic}\n待评审文稿：\n{draft}",
    )
    try:
        data = json.loads(out.strip().strip("```json").strip("```"))
        return {"pass": bool(data.get("pass")), "issues": data.get("issues", [])}
    except Exception:
        return {"pass": True, "issues": []}


# ---------------- 编排流程 ----------------
def run_team(topic: str, max_revise: int = 2) -> dict:
    print(f"\n{'='*60}\n[Lead] 主题：{topic}")
    subs = agent_lead_plan(topic)
    print(f"[Lead] 拆解出 {len(subs)} 个子问题：{subs}")

    # 并行研究（墙钟时间取最慢的那个，而非累加）
    with ThreadPoolExecutor(max_workers=len(subs)) as pool:
        results = list(pool.map(agent_researcher, subs))
    for r in results:
        print(f"[研究员] {r['sub_question']} → {len(r['points'])} 条要点")

    points = agent_dedup(results)
    print(f"[去重] 合并后 {len(points)} 条要点")

    draft = agent_writer(topic, points)
    state = {"topic": topic, "points": points, "draft": draft, "issues": []}

    for i in range(max_revise):  # 生成-评审循环
        review = agent_critic(topic, draft)
        print(f"[评审] 第{i+1}轮：{'通过' if review['pass'] else '不通过 → ' + '; '.join(review['issues'])}")
        state["issues"] = review["issues"]
        if review["pass"]:
            break
        draft = agent_writer(topic, points + [f"补充要求：{x}" for x in review["issues"]])
        state["draft"] = draft

    # 工件落盘（跨 Agent/跨会话共享状态用文件，不用对话历史）
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "multi_agent_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {topic}\n\n{draft}\n\n## 要点\n" + "\n".join(f"- {p}" for p in points))
    print(f"[Lead] 已产出：{path}")
    return state


if __name__ == "__main__":
    run_team("AI Agent 在企业的落地现状与成本优化")

# 改造作业：
# 1. 把 web_search 换成真实搜索（web-search-free skill / 搜索 API），观察结果质量变化
# 2. 把研究员数量加到 5 个，对比 token 消耗与报告质量——体会"多 Agent 的账"
# 3. 去掉去重环节，看报告中出现多少重复内容（验证"去重是必需组件"）
# 4. 给评审员加"成本意识"评分项（是否建议了更省的方案）
