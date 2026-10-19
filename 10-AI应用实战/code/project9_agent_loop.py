"""
项目9：Agent Loop 工程（Harness 六层框架落地，可离线运行，无模型依赖）

对应 06 目录《Harness工程实战》与《AgentLoop工程实战》："模型是大脑，代码是 Harness"。
本文件把六层检查框架落成一个可跑的 Agent Loop 引擎，并用 MockLLM 剧本演示三个场景：
  demo1 完整闭环：幻觉工具被 L6 拦截 → 修正 → 工具执行 → L5 独立验证 → 完成 → 断点续跑
  demo2 防死循环：同样的失败调用连续 2 次 → two-strike 升级人工（Stripe 实践）
  demo3 上下文交接：历史超阈值 → context reset + 结构化交接文档 → 紧凑上下文继续

六层映射（对照 Harness工程实战.md §2）：
  L1 信息边界  → build_context()：喂"任务状态 + 最近几步"，不堆全量历史
  L2 工具系统  → TOOLS 注册表，错误信息自带修复指令（错误即上下文）
  L3 执行编排  → AgentLoop.run()：决策 → 过闸 → 执行 → 验证 四拍循环
  L4 记忆状态  → ProgressState：JSON 进度文件落盘，断点续跑
  L5 评估观测  → Verifier：独立复算验证（不用 AI 眼睛查 AI 作业）+ trace 日志
  L6 约束恢复  → Gate 白名单拦截 / 重复检测 two-strike / 最大步数 / 升级人工

运行：python project9_agent_loop.py
产出：agent_loop_state.json（进度文件）、agent_loop_trace.log（观测日志）
"""
import json
import os
import sys
from datetime import datetime

# Windows GBK 控制台兼容：强制 UTF-8 输出，避免 emoji 打印报错
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(__file__)
TRACE_PATH = os.path.join(BASE_DIR, "agent_loop_trace.log")


def trace(event: str, **kw):
    """L5 观测：每个关键决策留痕（JSONL，grep 友好——Anthropic 实践）"""
    with open(TRACE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                            "event": event, **kw}, ensure_ascii=False) + "\n")


# ---------------- L2 工具系统：描述即接口，错误自带修复指令 ----------------
def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/().% ")
        if not set(expression) <= allowed:
            bad = set(expression) - allowed
            return f"错误：表达式含非法字符 {bad}。修复指令：只使用数字与 + - * / ( ) . % 空格"
        return str(round(eval(expression), 4))  # 演示用；生产请用 ast 安全求值
    except ZeroDivisionError:
        return "错误：除数为 0。修复指令：先核对分母数据来源，分母为 0 时应换口径而不是硬算"
    except Exception as e:
        return f"错误：{e}。修复指令：检查表达式语法后重试"


WEATHER = {"北京": "晴 26°C", "上海": "多云 29°C", "深圳": "雷阵雨 31°C",
           "广州": "晴 33°C", "杭州": "多云 28°C"}


def get_weather(city: str) -> str:
    if city in WEATHER:
        return f"{city}：{WEATHER[city]}"
    return f"错误：{city} 暂无数据。修复指令：仅支持 {'、'.join(WEATHER)}，请核对城市名"


TOOLS = {
    "calculator": {"fn": calculator, "desc": "精确计算数学表达式"},
    "get_weather": {"fn": get_weather, "desc": "查询城市实时天气（mock）"},
}


# ---------------- L4 记忆与状态：进度文件落盘，断点续跑 ----------------
class ProgressState:
    """结构化任务状态。上下文可以 reset，状态不能丢——这是交接零损失的前提"""
    PATH = os.path.join(BASE_DIR, "agent_loop_state.json")

    def __init__(self, task_id: str, goal: str):
        self.task_id, self.goal = task_id, goal
        self.status, self.rounds = "running", 0
        self.steps_done, self.failed = [], []

    @classmethod
    def load_or_init(cls, task_id: str, goal: str):
        if os.path.exists(cls.PATH):
            with open(cls.PATH, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("task_id") == task_id:      # 同一任务 → 恢复进度
                s = cls(task_id, data["goal"])
                s.status, s.rounds = data["status"], data["rounds"]
                s.steps_done, s.failed = data["steps_done"], data["failed"]
                return s
        return cls(task_id, goal)

    def record_step(self, text: str):
        self.steps_done.append(text)

    def record_fail(self, text: str):
        self.failed.append(text)

    def save(self):
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, ensure_ascii=False, indent=2)

    def handoff(self) -> dict:
        """结构化交接文档（目标/进度/失败原因/下一步）——context reset 的配套件"""
        return {"目标": self.goal, "已完成(已验证)": self.steps_done,
                "失败与原因": self.failed, "下一步": "从未完成步骤继续"}


# ---------------- L1 信息边界：喂状态而非堆历史 ----------------
def build_context(state: ProgressState, history: list, budget: int):
    ctx = {"任务状态": {"目标": state.goal, "已验证进度": state.steps_done},
           "最近几步": history[-3:]}
    util = min(1.0, len(history) / budget)  # 演示用条数模拟 token 预算；生产按 tokenizer 计数
    return ctx, util


# ---------------- L6 约束校验：白名单 + 步数上限 ----------------
class Gate:
    def __init__(self, max_steps: int):
        self.max_steps = max_steps

    def check(self, action: dict):
        name = action.get("tool", "")
        if name != "final" and name not in TOOLS:
            return False, (f"工具 {name} 不存在，可用工具：{sorted(TOOLS) + ['final']}。"
                           f"修复指令：从白名单中重选")
        return True, ""


class EscalateToHuman(Exception):
    """two-strike / 超步数：停止自动重试，升级人工"""


# ---------------- L3 执行编排：四拍循环 ----------------
class AgentLoop:
    def __init__(self, llm, verifier, history_budget: int = 50, max_steps: int = 8):
        self.llm, self.verifier = llm, verifier
        self.history_budget = history_budget
        self.gate = Gate(max_steps)
        self.last_fail_sig, self.strikes = None, 0

    def run(self, state: ProgressState) -> str:
        if state.status == "done":
            print("  ⏭️  断点续跑：进度文件显示该任务已完成，跳过。")
            return "（断点续跑：无需重跑）"
        if state.status == "escalated":
            print("  ⏭️  断点续跑：该任务上次已升级人工，跳过。")
            return "（上次已升级人工）"
        trace("task_start", task_id=state.task_id)
        history = []
        try:
            for rnd in range(1, self.gate.max_steps + 1):
                state.rounds = rnd
                ctx, util = build_context(state, history, self.history_budget)
                if util > 0.5 and history:      # 上下文管理：超阈值 → reset + 交接
                    print(f"  📈 上下文利用率 {util:.0%} > 50% → context reset")
                    print("  📄 交接文档：" + json.dumps(state.handoff(), ensure_ascii=False))
                    trace("handoff", task_id=state.task_id, rounds=rnd)
                    history = []                 # 状态在 ProgressState 里，reset 零信息损失
                    util = 0.0
                action = self.llm.decide(ctx)
                print(f"  [round {rnd}] ctx利用率 {util:.0%} | 决策: "
                      f"{json.dumps(action, ensure_ascii=False)}")

                # L6：过闸（白名单拦截）
                ok, reason = self.gate.check(action)
                if not ok:
                    print(f"  🚫 [L6 拦截] {reason}")
                    state.record_fail(reason)
                    history.append({"role": "gate", "content": reason})
                    state.save()
                    trace("gate_block", task_id=state.task_id, tool=action.get("tool"))
                    continue

                if action["tool"] == "final":    # L5：独立验证，不信任模型自评
                    ok, detail = self.verifier(state, action.get("answer", ""))
                    if ok:
                        state.status = "done"
                        state.save()
                        trace("task_done", task_id=state.task_id, detail=detail)
                        print(f"  ✅ [L5 验证通过] {detail}")
                        return action["answer"]
                    print(f"  ❌ [L5 验证不通过] {detail} → 反馈给 LLM 重做")
                    state.record_fail(detail)
                    history.append({"role": "verifier", "content": detail})
                    continue

                # L2：执行工具（模型只出招，Harness 执行）
                result = TOOLS[action["tool"]]["fn"](**action["args"])
                sig = action["tool"] + ":" + json.dumps(action["args"],
                                                        sort_keys=True, ensure_ascii=False)
                if result.startswith("错误"):    # L6：重复失败检测 → two-strike
                    self.strikes = self.strikes + 1 if sig == self.last_fail_sig else 1
                    self.last_fail_sig = sig
                    if self.strikes >= 2:
                        raise EscalateToHuman(
                            f"连续 2 次相同失败调用 {sig}，停止重试，升级人工")
                else:
                    self.strikes, self.last_fail_sig = 0, None
                print(f"  🔧 [L2 执行] {action['tool']}({action['args']}) -> {result}")
                state.record_step(f"{action['tool']}{action['args']} => {result}")
                history.append({"role": "tool", "name": action["tool"], "content": result})
                state.save()
            raise EscalateToHuman("达到最大步数仍未完成（防死循环第三招）")
        except EscalateToHuman as e:
            state.status = "escalated"
            state.record_fail(str(e))
            state.save()
            trace("escalate", task_id=state.task_id, reason=str(e))
            print(f"  🚨 [L6 升级人工] {e}")
            return f"任务升级人工：{e}"


# ---------------- MockLLM：剧本式假模型，按序出招（真实 LLM 见改造作业 1） ----------------
class MockLLM:
    def __init__(self, script: list):
        self.script, self.i = list(script), 0

    def decide(self, ctx) -> dict:
        action = self.script[self.i]
        self.i += 1
        return action


# ---------------- L5 验证器：独立复算，不用同一双眼睛查作业 ----------------
def verify_settlement(state, answer):
    golden = round(238 * 47 / 3, 2)             # Harness 自己算，不问模型对不对
    return (str(golden) in answer.replace(" ", "")), f"独立复算结果 {golden} 元"


def verify_weather(state, answer):
    missing = [c for c in WEATHER if c not in answer]
    return (not missing), ("5 个城市数据全覆盖" if not missing else f"缺少城市: {missing}")


# ---------------- 三个演示场景 ----------------
SCRIPT_SETTLE = [
    {"tool": "search_web", "args": {"q": "团建预算怎么算"}},   # 幻觉工具 → L6 拦截
    {"tool": "calculator", "args": {"expression": "238*47"}},
    {"tool": "calculator", "args": {"expression": "11186/3"}},
    {"tool": "final", "answer": "总预算 238*47=11186 元，3 个部门平摊，每部门 3728.67 元"},
]
SCRIPT_FLAKY = [
    {"tool": "calculator", "args": {"expression": "500/0"}},
    {"tool": "calculator", "args": {"expression": "500/0"}},   # 同样失败再来一次 → two-strike
]
SCRIPT_WEATHER = [{"tool": "get_weather", "args": {"city": c}}
                  for c in ["北京", "上海", "深圳", "广州", "杭州"]] + [
    {"tool": "final", "answer": "北京晴26°C、上海多云29°C、深圳雷阵雨31°C、"
                                "广州晴33°C、杭州多云28°C；今天最热是广州 33°C"}]


def banner(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def demo1():
    banner("demo1 · 完整闭环：幻觉拦截 → 修正 → 执行 → 独立验证 → 断点续跑")
    loop = AgentLoop(MockLLM(SCRIPT_SETTLE), verifier=verify_settlement)
    state = ProgressState.load_or_init("settlement", "238 人每人 47 元团建，3 个部门平摊，求每部门金额")
    answer = loop.run(state)
    print(f"\n  最终答案: {answer}")
    print("\n  —— 同一任务再跑一次：进度文件已 done，断点续跑直接跳过 ——")
    AgentLoop(MockLLM([]), verifier=verify_settlement).run(
        ProgressState.load_or_init("settlement", "同上"))


def demo2():
    banner("demo2 · 防死循环：重复失败 two-strike 升级人工")
    loop = AgentLoop(MockLLM(SCRIPT_FLAKY), verifier=verify_settlement)
    state = ProgressState.load_or_init("flaky", "计算 500/0（分母为 0 的坏数据）")
    print(f"  结果: {loop.run(state)}")


def demo3():
    banner("demo3 · 上下文交接：历史超限 → reset + 交接文档 → 继续")
    loop = AgentLoop(MockLLM(SCRIPT_WEATHER), verifier=verify_weather, history_budget=3)
    state = ProgressState.load_or_init("weather", "查 5 个城市天气并汇总最热城市")
    answer = loop.run(state)
    print(f"\n  最终答案: {answer}")


if __name__ == "__main__":
    if os.path.exists(ProgressState.PATH):
        os.remove(ProgressState.PATH)   # 演示用：清掉上次状态保证脚本可重复跑；生产中应保留
    demo1()
    demo2()
    demo3()
    print(f"\n观测日志: {TRACE_PATH}（JSONL，可 grep）")

# 改造作业：
# 1. 把 MockLLM 换成真实 LLM：decide() 里调 OpenAI 兼容 API（参考 project4），
#    system prompt 只给 build_context() 的结构化状态——体会 L1 与堆历史的差异
# 2. 把 history_budget 换成真实 token 计数（tiktoken），并做压缩而非清空（保留最近 N 步）
# 3. 验证器加"AI 写的测试验证 AI 代码"反例：先用模型自评跑一次，再独立复算，对比差异
# 4. 给 ProgressState 加 schema 版本号，支持中断后由人工修改进度文件再续跑
