"""
项目6：人机交互（HITL）—— 档位分层 + 四类交互模式的可运行实现

覆盖：
1. 审批检查点：不可逆动作前暂停，展示"做什么+为什么+影响+回滚方式"
2. 主动澄清：需求模糊时给选项让用户选（而非开放提问），且有轮次上限
3. 计划确认：先出计划让人批准，再执行（最便宜的纠偏点）
4. 升级转交：连续失败/超权限时主动升级，带完整上下文
5. 审计日志：所有决策留痕（信任四要素之"可验证"）

运行：python project6_hitl.py
"""
import os
import json
import time
from datetime import datetime
from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"
API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
MODEL = "deepseek-chat"
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ---------- 风险分级：档位由动作风险决定，而非由 Agent 心情决定 ----------
RISK = {
    "read_files": "L0",     # 只读 → 自动放行
    "write_draft": "L1",    # 可逆写入 → 自动 + 日志
    "delete_files": "L2",   # 不可逆 → 必须审批
    "send_email": "L2",     # 对外代表用户 → 必须审批
}
AUTO_LEVELS = {"L0", "L1"}  # 自动放行档位；L2 需人工审批

AUDIT_PATH = os.path.join(os.path.dirname(__file__), "hitl_audit.log")


def audit(event: str, detail: dict):
    """审计日志：可追溯是信任的基础"""
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(), "event": event, **detail},
                           ensure_ascii=False) + "\n")


# ---------- 交互模式 1：审批检查点 ----------
def request_approval(action: str, why: str, impact: str, rollback: str) -> bool:
    level = RISK.get(action, "L2")
    if level in AUTO_LEVELS:
        print(f"  ✅ [{level}] 自动放行：{action}")
        audit("auto_allow", {"action": action, "level": level})
        return True

    print(f"\n  ⏸️  需人工审批 [{level}]：{action}")
    print(f"     为什么：{why}")
    print(f"     影响面：{impact}")
    print(f"     回滚方式：{rollback}")
    ans = input("     批准？[y=批准 / n=拒绝 / e=我先改一下] ").strip().lower()
    audit("approval", {"action": action, "decision": ans, "why": why})
    if ans == "e":
        note = input("     请输入你的修改意见（将带回给 Agent）：").strip()
        print(f"     [Agent] 收到修改意见，将调整方案后重新申请：{note}")
        return False
    return ans == "y"


# ---------- 交互模式 2：主动澄清（给选项 + 轮次上限） ----------
def ask_clarification(question: str, options: list[str], max_rounds: int = 2, round_no: int = 1) -> str:
    if round_no > max_rounds:
        print("  [Agent] 澄清轮次已达上限，我将按最合理的默认方案继续，并标注假设。")
        return "DEFAULT"
    print(f"\n  ❓ 需要确认（第 {round_no}/{max_rounds} 轮）：{question}")
    for i, opt in enumerate(options, 1):
        print(f"     {i}. {opt}")
    choice = input("     请选择编号或直接输入你的要求：").strip()
    audit("clarify", {"question": question, "choice": choice})
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return choice


# ---------- 交互模式 3：计划确认 ----------
def confirm_plan(plan: list[str]) -> bool:
    print("\n  📋 Agent 执行计划：")
    for i, step in enumerate(plan, 1):
        print(f"     {i}. {step}")
    ans = input("     批准执行？[y/n] ").strip().lower()
    audit("plan_approval", {"plan": plan, "decision": ans})
    if ans != "y":
        print("     [Agent] 计划被否决。请输入调整方向（或回车退出）：")
        feedback = input("     > ").strip()
        if feedback:
            print(f"     [Agent] 按你的方向重排计划：{feedback}")
        return False
    return True


# ---------- 交互模式 4：升级转交 ----------
def escalate(reason: str, context: dict):
    print("\n  🔺 主动升级人工")
    print(f"     原因：{reason}")
    print(f"     已完成：{context.get('done')}")
    print(f"     卡在哪：{context.get('blocked')}")
    print(f"     已尝试：{context.get('tried')}")
    print("     （交接带完整上下文，人不必从零排查）")
    audit("escalation", {"reason": reason, **context})


# ---------- 业务：一个"整理资料并清理文件"的 Agent ----------
def run_agent(user_request: str):
    state = {"done": [], "blocked": None, "tried": [], "assumptions": []}

    # 1) 澄清：需求里的模糊点先问清（给选项，最多 2 轮）
    scope = ask_clarification(
        "你说的“资料”范围是？",
        ["只处理 .md 文件", "处理 .md 和 .txt", "处理当前目录全部文件"],
        round_no=1,
    )
    state["assumptions"].append(f"处理范围 = {scope}")

    # 2) 计划确认：动手前先给计划（最便宜的纠偏点）
    plan = ["扫描目标文件（只读）", "生成整理后的草稿（可逆）", "删除临时文件（不可逆）", "发送汇总邮件（对外）"]
    if not confirm_plan(plan):
        print("\n流程中止：计划未被批准（这正是计划确认的价值——省下了 3 个步骤的成本）")
        return

    # 3) 执行：不同风险动作走不同档位
    print("\n  ▶ 执行中：")
    request_approval("read_files", "需要统计文件数量与大小", "无（只读）", "无需回滚")
    state["done"].append("扫描文件完成（12 个文件）")

    request_approval("write_draft", "生成整理后的草稿文件", "新增 1 个文件（不影响原文件）", "删除该草稿即可")
    state["done"].append("草稿已生成：draft.md")

    # 不可逆动作：审批 + 失败重试 + 连续失败则升级
    tries = 0
    while tries < 2:  # two-strike 规则
        ok = request_approval(
            "delete_files",
            "清理 3 个临时文件",
            "删除 2.1MB 临时数据（不可恢复）",
            "已生成回收站快照 backup.zip，可恢复",
        )
        if ok:
            state["done"].append("临时文件已删除（含备份）")
            break
        tries += 1
        state["tried"].append(f"第 {tries} 次请求删除被拒/修改")
        if tries >= 2:  # 连续失败 → 升级而非无限重试
            state["blocked"] = "删除操作未获批准"
            escalate("删除动作连续 2 次未获批准", state)
            return

    request_approval("send_email", "把汇总发给相关同事", "对外发送（无法撤回）", "可发补充说明邮件")
    state["done"].append("邮件已发送（经审批）")

    print(f"\n  ✅ 任务完成：{state['done']}")
    print(f"  📝 审计日志：{AUDIT_PATH}")


if __name__ == "__main__":
    print("=== HITL 演示：Agent 会主动澄清、先给计划、按风险分级请求审批 ===")
    print("（提示：试试全部选 n，观察它如何按 two-strike 规则升级而非死循环）\n")
    run_agent("把最近的资料整理一下，清理掉没用的临时文件，然后发邮件汇总给我同事")

# 改造作业：
# 1. 加第 5 种模式：中途纠偏（执行中按 Ctrl+C 或输入指令调整方向后继续）
# 2. 实现"记住选择"：同类低风险审批批准一次后自动放行（防审批疲劳）
# 3. 把审批改为"批量审批"：一次列出 3 个待批动作让用户勾选
# 4. 统计并报告：审批总耗时 / 用户拒绝率 / 自动放行占比（监督模式的看板指标）
