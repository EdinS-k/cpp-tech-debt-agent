"""性能观测：分别计时各部分耗时，找出瓶颈在哪。

用法（项目根目录）：python scripts/bench.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def tick(label, fn, *args, **kwargs):
    """跑一次 fn，打印耗时（毫秒）"""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  {label:<38} {dt:>9.1f} ms")
    return result


def main():
    print("=" * 68)
    print("【各部分耗时实测】单位：毫秒")
    print("-" * 68)

    # ---------- 0) 导入 + 初始化（会连数据库、加载模型）----------
    t0 = time.perf_counter()
    from resources.embedding import embed_text
    from resources.llm import llm
    from resources.rag_pipeline import rag_pipeline
    from resources.sqlserver_store import sqlserver_store
    dt = (time.perf_counter() - t0) * 1000
    print(f"  {'导入 + 连数据库 + 加载模型':<38} {dt:>9.1f} ms   ← 只发生一次")

    print("-" * 68)

    # ---------- 1) 算向量 ----------
    tick("算 1 条向量（第一次，含模型预热）",
         embed_text, "风险等级：高；位置：old_func；问题：缓冲区溢出")
    tick("算 1 条向量（第二次，已预热）",
         embed_text, "风险等级：高；位置：old_func；问题：缓冲区溢出")

    # ---------- 2) 三种检索 ----------
    tick("向量检索（SQL Server VECTOR_DISTANCE）",
         sqlserver_store.vector_search, "内存安全问题", 3)
    tick("BM25 检索", rag_pipeline.sparse_search, "缓冲区溢出", 3)
    tick("混合检索（向量 + BM25 + RRF）",
         rag_pipeline.hybrid_search, "缓冲区溢出", 3)

    # ---------- 3) 结构化查询 ----------
    tick("结构化查询（SQL Server）",
         sqlserver_store.query_history, "main.cpp", 5)

    # ---------- 4) 调一次大模型 ----------
    print("-" * 68)
    print("  正在调用 DeepSeek（一次分析要调 3 次）...")
    tick("调 1 次 LLM（DeepSeek）",
         lambda: llm.invoke("用一句话解释什么是技术债务"))

    print("=" * 68)
    print("提示：把上面最大那个数字 × 3，就是一次分析的 LLM 总耗时。")
    print("=" * 68)


if __name__ == "__main__":
    main()
