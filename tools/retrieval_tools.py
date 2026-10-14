# tools/retrieval_tools.py
"""工具层：检索策略（向量 / BM25 / 混合）。"""
from langchain.tools import tool

from config import RETRIEVE_TOP_K
from resources.rag_pipeline import rag_pipeline


@tool
def vector_search_tool(query: str, top_k: int = RETRIEVE_TOP_K) -> str:
    """纯语义检索（向量库）。适合"意思相近"的描述性查询，例如"内存安全问题"。"""
    docs = rag_pipeline.dense_search(query, top_k)
    return "\n".join(docs) if docs else "无相关记录"


@tool
def bm25_search_tool(query: str, top_k: int = RETRIEVE_TOP_K) -> str:
    """纯关键词检索（BM25）。适合精确的函数名 / 变量名 / 术语，例如"global_buf"。"""
    docs = rag_pipeline.sparse_search(query, top_k)
    return "\n".join(docs) if docs else "无相关记录"


@tool
def hybrid_search_tool(query: str, top_k: int = RETRIEVE_TOP_K) -> str:
    """混合检索（向量 + BM25 → RRF 融合）。兼顾语义与关键词，最稳妥，默认用它。"""
    docs = rag_pipeline.hybrid_search(query, top_k)
    return "\n".join(docs) if docs else "无相关记录"
