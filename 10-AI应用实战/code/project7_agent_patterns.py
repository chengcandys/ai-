"""
项目7：Agent 设计模式对比实验（4 种模式同一任务，对比产出与 token 成本）

实现模式：
1. Prompt Chaining  链式分解（提取 → 改写 → 校验，带质量闸门）
2. Routing          路由分发（先分类，再交给不同"专家"处理）
3. Parallelization  并行化（Sectioning 分段并行 + Voting 投票）
4. Reflection       反思循环（Generator ⇄ Evaluator，最多 3 轮）

运行：python project7_agent_patterns.py
观察重点：每种模式的 token 消耗差异 —— 模式复杂度是用成本换能力
"""
import os
import json
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"  # Ollama 改 http://localhost:11434/v1
API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
MODEL = "deepseek-chat"
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

usage_total = {"prompt": 0, "completion": 0}


def llm(system: str, user: str, temperature: float = 0.3, tag: str = "") -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
    )
    if resp.usage:
        usage_total["prompt"] += resp.usage.prompt_tokens
        usage_total["completion"] += resp.usage.completion_tokens
    return resp.choices[0].message.content


def report(pattern: str, result: str):
    print(f"\n{'─'*56}\n【{pattern}】token 消耗: {usage_total['prompt']}in/{usage_total['completion']}out")
    print(result[:400] + ("..." if len(result) > 400 else ""))
    usage_total.update(prompt=0, completion=0)


# ============ 模式1: Prompt Chaining（链式分解 + 质量闸门） ============
def pattern_prompt_chaining(text: str) -> str:
    print("\n[Chaining] 步骤1: 提取要点")
    points = llm("提取文本要点，每条一行，不遗漏关键信息。", text, tag="s1")

    # 质量闸门：步骤1 不合格就不进入步骤2（出错定位到具体环节）
    gate = llm("判断要点提取是否完整，只回答 PASS 或 FAIL:原因。",
               f"原文：{text[:300]}\n要点：{points}", tag="gate")
    print(f"[Chaining] 闸门: {gate[:60]}")
    if gate.startswith("FAIL"):
        points = llm("上次提取不完整，请重新完整提取。", f"原文：{text}\n问题：{gate}", tag="s1-retry")

    print("[Chaining] 步骤2: 改写为摘要")
    return llm("把要点改写成 100 字内的流畅摘要。", points, tag="s2")


# ============ 模式2: Routing（路由分发） ============
def pattern_routing(query: str) -> str:
    category = llm(
        "把用户问题分类为 one of: [技术, 账单, 闲聊]。只输出类别。",
        query, tag="router",
    ).strip()
    print(f"\n[Routing] 分类结果: {category}")
    experts = {
        "技术": "你是技术专家，回答专业、给出可操作建议。",
        "账单": "你是账单客服，回答谨慎，涉及金额提醒核对。",
        "闲聊": "你是轻松的聊天伙伴，回答简短幽默。",
    }
    return llm(experts.get(category, experts["闲聊"]), query, tag="expert")


# ============ 模式3: Parallelization（Sectioning + Voting） ============
def pattern_parallel(topic: str) -> str:
    # 3a. Sectioning：3 个独立子任务并行
    subs = ["优势", "风险", "适用场景"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        parts = list(pool.map(
            lambda s: llm("你是研究员，用 3 行内回答问题。", f"{topic} 的{s}是什么？", tag=f"sec-{s}"),
            subs,
        ))
    sectioned = "\n".join(parts)
    print(f"\n[Parallel-Sectioning] 3 个子任务并行完成")

    # 3b. Voting：同一问题跑 3 次，投票取多数（提高置信度）
    def judge(_):
        return llm("判断该说法是否准确，只回答 准确 或 不准确。",
                   f"说法：'{topic} 适合所有企业直接使用。'", temperature=0, tag="vote")
    with ThreadPoolExecutor(max_workers=3) as pool:
        votes = list(pool.map(judge, range(3)))
    verdict = "准确" if votes.count("准确") > 1 else "不准确"
    print(f"[Parallel-Voting] 3 票: {votes} → 结论: {verdict}")
    return f"[Sectioning 合并结果]\n{sectioned}\n\n[Voting 结论] 该说法: {verdict}"


# ============ 模式4: Reflection（生成 ⇄ 评审循环） ============
def pattern_reflection(task: str, max_rounds: int = 3) -> str:
    draft = llm("你是工程师，给出实现方案（结构、关键代码思路、风险）。", task, tag="gen-1")
    for i in range(1, max_rounds + 1):
        review = llm(
            "你是严格的技术评审。找出方案的缺陷（边界条件/性能/安全），"
            '只输出 JSON: {"pass": true/false, "issues": ["..."]}',
            f"任务：{task}\n方案：{draft}", tag=f"eval-{i}",
        )
        try:
            data = json.loads(review.strip().strip("```json").strip("```"))
        except Exception:
            data = {"pass": True, "issues": []}
        print(f"\n[Reflection] 第{i}轮评审: {'通过' if data['pass'] else '驳回 → ' + '; '.join(data['issues'][:2])}")
        if data["pass"]:
            break
        draft = llm(
            "你是工程师，根据评审意见修订方案（保留好的部分，修复指出的问题）。",
            f"任务：{task}\n原方案：{draft}\n评审意见：{data['issues']}", tag=f"gen-{i+1}",
        )
    return draft


if __name__ == "__main__":
    sample_text = (
        "公司决定在客服系统引入大模型。第一期目标是分流 60% 的常见问题，"
        "但合规部门要求所有对外回复必须留痕，涉及退款的对话必须人工复核，"
        "技术团队只有 3 个人，预算有限，希望三个月内上线 MVP。"
    )

    report("模式1 Prompt Chaining", pattern_prompt_chaining(sample_text))
    report("模式2 Routing", pattern_routing("我的账单这个月多扣了 200 块怎么回事"))
    report("模式3 Parallelization", pattern_parallel("大模型客服"))
    report("模式4 Reflection", pattern_reflection("设计一个每周自动分析竞品动态并邮件汇报的脚本"))

    print(f"\n{'='*56}")
    print("实验结论（配合笔记阅读）：")
    print("· Chaining：步骤少 token 最省，质量闸门只在小代价下拦截错误")
    print("· Routing：分类用轻量调用，专家分支各取所长")
    print("· Parallel：token ≈ 子任务数 × 单任务，但墙钟时间 = 最慢的一个")
    print("· Reflection：token 最高（生成+评审多轮），质量上限也最高 → 质量优先任务才用")

# 改造作业：
# 1. 给每种模式加失败注入（如让评审故意苛刻），观察循环是否正常收敛/退出
# 2. 把 Reflection 的评审换成"另一个模型"，对比自我评审 vs 交叉评审的差异
# 3. 给 Voting 加权重（规则视角权重 2，其他 1），观察结论变化
# 4. 统计每种模式的 P95 延迟（time.time 打点），画出"成本-质量-延迟"三角
