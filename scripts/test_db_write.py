"""最终验证：用项目【真实代码路径】测试 写入 + 向量检索 + 混合检索。

用法（项目根目录）：python scripts/test_db_write.py
"""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pyodbc

from config import sqlserver_conn_str
from resources.rag_pipeline import rag_pipeline
from resources.sqlserver_store import sqlserver_store

TEST_FILE = "__test__.cpp"


def cleanup():
    with pyodbc.connect(sqlserver_conn_str(), timeout=5) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM dbo.debt_memory WHERE file_path = ?", (TEST_FILE,))
        conn.commit()


def main():
    print("=" * 66)

    # ---------- ① 写入（整体替换） ----------
    print("① 用真实代码写入一条测试记录 ...")
    try:
        n = sqlserver_store.replace_file_debts(TEST_FILE, [{
            "risk_level": "高",
            "location": "test_func()",
            "problem": "缓冲区溢出风险",
            "suggestion": "增加边界检查",
        }])
        print(f"   ✅ 写入成功（{n} 条）")
    except Exception:
        print("   ✗ 写入失败：")
        traceback.print_exc()
        return

    # ---------- ①b 再写一次，验证不会重复 ----------
    print("\n①b 再写一次同样内容，验证【整体替换】不产生重复 ...")
    try:
        sqlserver_store.replace_file_debts(TEST_FILE, [{
            "risk_level": "高",
            "location": "test_func()",
            "problem": "缓冲区溢出风险",
            "suggestion": "增加边界检查",
        }])
        cnt = len(sqlserver_store.query_history(TEST_FILE, limit=50))
        if cnt == 1:
            print("   ✅ 库里仍然只有 1 条 —— 没有重复！")
        else:
            print(f"   ❌ 变成了 {cnt} 条，去重失败")
    except Exception:
        print("   ✗ 失败：")
        traceback.print_exc()

    # ---------- ② 向量检索 ----------
    print("\n② 向量语义检索（VECTOR_DISTANCE）...")
    try:
        docs = sqlserver_store.vector_search("内存安全问题", top_k=3)
        print(f"   ✅ 检索成功，返回 {len(docs)} 条：")
        for d in docs:
            print(f"      · {str(d)[:72]}")
    except Exception:
        print("   ✗ 检索失败：")
        traceback.print_exc()

    # ---------- ③ 混合检索 ----------
    print("\n③ 混合检索（向量 + BM25 + RRF）...")
    try:
        docs = rag_pipeline.hybrid_search("缓冲区溢出", top_k=3)
        print(f"   ✅ 返回 {len(docs)} 条：")
        for d in docs:
            print(f"      · {str(d)[:72]}")
    except Exception:
        print("   ✗ 混合检索失败：")
        traceback.print_exc()

    # ---------- ④ 清理 + 统计 ----------
    print("\n④ 清理测试数据 + 统计 ...")
    try:
        cleanup()
        with pyodbc.connect(sqlserver_conn_str(), timeout=5) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM dbo.debt_memory")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM dbo.debt_memory WHERE embedding IS NOT NULL")
            vec_n = cur.fetchone()[0]
            print(f"   剩余记录: {total}，其中带向量: {vec_n}")
    except Exception:
        traceback.print_exc()

    print("=" * 66)


if __name__ == "__main__":
    main()
