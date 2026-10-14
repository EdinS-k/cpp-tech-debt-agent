# resources/embedding.py
"""底层资源层：文本向量化。
"""
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

EMBED_DIM = 384

_ef = DefaultEmbeddingFunction()


def embed_texts(texts):
    """批量：list[str] → list[list[float]]"""
    if not texts:
        return []
    return _ef(list(texts))


def embed_text(text: str):
    """单条：str → list[float]（384 维）"""
    return embed_texts([text])[0]


def to_sql_vector(vec):
    """转成 SQL Server 能 CAST 的 JSON 数组字符串，例如 '[0.1,0.2,0.3]'。

    只保留 6 位小数：float32 的有效精度约 7 位，再长都是噪音；
    缩短后还能省一半以上存储空间（8420 → 约 3650 字符）。
    """
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"
