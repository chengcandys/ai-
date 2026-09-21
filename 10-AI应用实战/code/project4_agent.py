"""
项目4：带工具的 Agent（最小 ReAct 循环：模型决策 → 执行工具 → 回喂结果 → 直到给出答案）
运行：python project4_agent.py
"""
import os
import json
from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"  # Ollama 改 http://localhost:11434/v1
API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
MODEL = "deepseek-chat"
MAX_STEPS = 8  # 防死循环第一招：最大步数

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ---------- 工具定义（模型可见的 schema） ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，需要精确计算时必用，不要心算",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "如 (238*47)/3"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气（演示用 mock 数据）",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
]


# ---------- 工具实现（模型不执行，由我们的代码执行） ----------
def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/().% ")
        if not set(expression) <= allowed:
            return "错误：表达式含非法字符"
        return str(eval(expression))  # 演示用；生产请用 ast 安全求值
    except Exception as e:
        return f"计算失败：{e}（请修正表达式后重试）"  # 错误信息要"模型可读"


def get_weather(city: str) -> str:
    mock = {"北京": "晴 26°C", "上海": "多云 29°C", "深圳": "雷阵雨 31°C"}
    return mock.get(city, f"{city}：暂无数据（支持北京/上海/深圳）")


DISPATCH = {"calculator": calculator, "get_weather": get_weather}


def run_agent(task: str):
    messages = [
        {"role": "system", "content": "你是 Agent，可使用工具完成任务。工具结果不足时换思路，最终给出结论。"},
        {"role": "user", "content": task},
    ]
    for step in range(1, MAX_STEPS + 1):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, temperature=0
        )
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:  # 无工具调用 = 给出最终答案，循环终止
            return msg.content

        for call in msg.tool_calls:  # 执行工具并回喂（role=tool）
            name, args = call.function.name, json.loads(call.function.arguments)
            if name not in DISPATCH:  # 防幻觉工具调用：白名单校验
                result = f"错误：工具 {name} 不存在，可用工具：{list(DISPATCH)}"
            else:
                result = DISPATCH[name](**args)
            print(f"  [step {step}] {name}({args}) -> {result}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return "已达最大步数，任务未完成（触发防死循环保护）"


if __name__ == "__main__":
    tasks = [
        "北京和上海今天天气如何？哪个更热？温差多少度？",
        "我们公司 238 人，每人预算 47 元团建，三个部门平摊，每部门多少钱？",
    ]
    for t in tasks:
        print(f"\n任务: {t}")
        print(f"结论: {run_agent(t)}")

# 改造作业：
# 1. 加第 3 个工具（如 read_file），体会"描述即接口"对调用准确率的影响
# 2. 实现重复动作检测（连续 2 次相同调用则退出）——防死循环第二招
# 3. 把 calculator 用 FastMCP 包装成 MCP Server，体会协议层与循环层的分离
