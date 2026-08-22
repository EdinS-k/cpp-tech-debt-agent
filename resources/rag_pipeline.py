# resources/rag_pipeline.py
"""底层资源层：RAG 流水线。

  · 向量检索 → SQL Server 的 VECTOR_DISTANCE（精确 kNN）
  · 关键词检索 → BM25（Python 侧计算，语料取自 SQL Server）
  · 融合 → RRF（倒数排名融合）
"""
import re

from rank_bm25 import BM25Okapi

# 注意：这里【故意不】在模块顶层 import sqlserver_store。
# 那会在 import 的瞬间就尝试连数据库，导致本模块无法脱离数据库被单独测试。
# 改成惰性 import —— 第一次真正需要时才连。


def tokenize(text: str):
    """BM25 分词：英文标识符 + 中文二元组(bigram)，兼顾代码与中文。"""
    text = (text or "").lower()
    tokens = re.findall(r"[a-z0-9_]+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    tokens += [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    return tokens


def rrf_fuse(ranked_lists, k: int = 60):
    """倒数排名融合(Reciprocal Rank Fusion)：把多路排名合并成一个。"""
    scores = {}
    for ranked in ranked_lists:
        for rank, idx in enumerate(ranked):
            scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


class RagPipeline:
    def __init__(self, store=None):
        if store is None:
            from resources.sqlserver_store import sqlserver_store
            store = sqlserver_store
        self.store = store

    # ---------------- 入库 ----------------
    def replace_debt_items(self, file_path: str, items: list) -> int:
        """把本次的债务条目【整体替换】进该文件的长期记忆。

        两点保护：
          1. 丢掉空条目（没位置也没问题描述的）
          2. 批内去重 —— 模型有时会把同一个问题说两遍
        """
        cleaned, seen = [], set()
        for it in items or []:
            problem = (it.get("problem") or "").strip()
            location = (it.get("location") or "").strip()
            if not (problem or location):
                continue
            key = (it.get("risk_level", ""), location, problem)
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({
                "risk_level": it.get("risk_level") or "中",
                "location": location,
                "problem": problem,
                "suggestion": (it.get("suggestion") or "").strip(),
            })

        return self.store.replace_file_debts(file_path, cleaned)

    # ---------------- 检索 ----------------
    def _sparse_rank(self, query: str, docs: list, top_k: int):
        """BM25 排名：只保留有词元命中的（score > 0），避免噪音污染融合结果"""
        if not docs:
            return []
        corpus = [tokenize(d) or ["<empty>"] for d in docs]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [i for i in ranked if scores[i] > 0][:top_k]

    def dense_search(self, query: str, top_k: int = 3):
        """策略①：向量语义检索（SQL Server VECTOR_DISTANCE）"""
        return self.store.vector_search(query, top_k)

    def sparse_search(self, query: str, top_k: int = 3):
        """策略②：BM25 关键词检索"""
        docs = self.store.all_documents()
        return [docs[i] for i in self._sparse_rank(query, docs, top_k)]

    def hybrid_search(self, query: str, top_k: int = 3, dense_k: int = 10, sparse_k: int = 10):
        """策略③：向量 + BM25 → RRF 融合"""
        docs = self.store.all_documents()
        if not docs:
            return []

        dense_docs = self.dense_search(query, dense_k)
        sparse_idx = self._sparse_rank(query, docs, sparse_k)

        # 文本 → 下标，复用 rrf_fuse
        idx_of = {}
        for i, d in enumerate(docs):
            idx_of.setdefault(d, i)

        dense_idx = [idx_of[d] for d in dense_docs if d in idx_of]
        fused = rrf_fuse([dense_idx, sparse_idx])
        return [docs[i] for i in fused[:top_k]]


# 单例
rag_pipeline = RagPipeline()
