"""
项目3：个人知识库 RAG 问答（文档切分 → Embedding → 向量检索 → 生成带引用的回答）
运行：python project3_rag.py  （自动索引当前目录下的 .md 文件做演示）
"""
import os
import glob
import chromadb
from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"  # Ollama 改 http://localhost:11434/v1
API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
MODEL = "deepseek-chat"
EMBED_MODEL = "text-embedding-v3"  # 各家不同；Ollama 可换 bge-m3 等本地模型

llm = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def chunk_text(text, size=400, overlap=80):
    """按固定长度+重叠切分（生产建议用递归切分，见 07 目录）"""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]


def embed(texts):
    resp = llm.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def build_index(md_dir):
    docs, metas, ids = [], [], []
    for path in glob.glob(os.path.join(md_dir, "**/*.md"), recursive=True):
        text = open(path, encoding="utf-8").read()
        for i, chunk in enumerate(chunk_text(text)):
            docs.append(chunk)
            metas.append({"source": os.path.basename(path), "chunk": i})
            ids.append(f"{os.path.basename(path)}#{i}")
    db = chromadb.Client()  # 内存模式；生产改 PersistentClient(path="./db")
    col = db.get_or_create_collection("kb")
    col.add(ids=ids, documents=docs, embeddings=embed(docs), metadatas=metas)
    print(f"[索引完成] {len(docs)} 个文档块")
    return col


def answer(col, question, top_k=3):
    q_emb = embed([question])[0]
    hits = col.query(query_embeddings=[q_emb], n_results=top_k)
    context = "\n\n".join(
        f"[资料{i+1} 来源:{m['source']}]\n{d}"
        for i, (d, m) in enumerate(zip(hits["documents"][0], hits["metadatas"][0]))
    )
    prompt = (
        "仅根据以下资料回答问题，资料不足就说不知道，并在句末标注来源编号（如[资料1]）。\n\n"
        f"{context}\n\n问题：{question}"
    )
    resp = llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    col = build_index(os.path.join(os.path.dirname(__file__), "..", ".."))
    print("知识库问答就绪，/quit 退出\n")
    while True:
        q = input("问: ").strip()
        if q.lower() == "/quit":
            break
        if q:
            print(f"答: {answer(col, q)}\n")

# 改造作业（对应 07 目录进阶清单）：
# 1. 检索后打印命中文档块，人工评估 Recall@3（建 10 条测试问题）
# 2. 加 Rerank：检索 top_k=10，再让 LLM 选出最相关的 3 块
# 3. 换 PersistentClient 实现索引持久化，避免每次重建
