"""
项目2：API 聊天机器人（多轮对话 + 流式输出 + token 统计）
运行：python project2_chatbot.py
命令：输入 /temp 0.3 调温度，/quit 退出
"""
import os
from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"  # Ollama 改 http://localhost:11434/v1
API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
MODEL = "deepseek-chat"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

SYSTEM = "你是一个简洁专业的助手，回答控制在 200 字以内。"


def chat(messages, temperature):
    """流式调用并实时打印，返回完整回复与 token 用量"""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )
    reply, usage = "", None
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            piece = chunk.choices[0].delta.content
            print(piece, end="", flush=True)
            reply += piece
        if chunk.usage:
            usage = chunk.usage
    print()
    return reply, usage


def main():
    messages = [{"role": "system", "content": SYSTEM}]
    temperature = 0.7
    print(f"聊天机器人已启动（模型 {MODEL}，温度 {temperature}），/quit 退出\n")
    while True:
        user = input("你: ").strip()
        if user.lower() == "/quit":
            break
        if user.startswith("/temp"):
            temperature = float(user.split()[1])
            print(f"[温度已设为 {temperature}]\n")
            continue
        if not user:
            continue
        messages.append({"role": "user", "content": user})
        print("AI: ", end="")
        reply, usage = chat(messages, temperature)
        messages.append({"role": "assistant", "content": reply})
        if usage:
            print(f"[tokens: 输入 {usage.prompt_tokens} + 输出 {usage.completion_tokens}]\n")


if __name__ == "__main__":
    main()

# 改造作业：
# 1. 加 /save 命令把对话存成 Markdown 文件
# 2. 限制历史长度（超过 10 轮时摘要旧对话）——体会上下文工程
# 3. 统计本次会话累计 token 并估算费用
