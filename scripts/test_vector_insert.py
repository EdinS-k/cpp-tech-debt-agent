"""测试多种「向量写入」写法，找出哪种能成功。

用法（项目根目录）：python scripts/test_vector_insert.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pyodbc

from config import sqlserver_conn_str
from resources.embedding import EMBED_DIM, embed_text

COLS = "(file_path, risk_level, location, problem, suggestion, content, embedding)"
ARGS = ("__t__.cpp", "低", "t()", "问题", "建议", "内容")


def try_insert(cur, label, sql, params):
    try:
        cur.execute(sql, params)
        cur.connection.commit()
        print(f"   [成功] {label}")
        return True
    except Exception as e:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        print(f"   [失败] {label}")
        print(f"          {type(e).__name__}: {str(e)[:180]}")
        return False


def main():
    conn = pyodbc.connect(sqlserver_conn_str(), timeout=5)
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.debt_memory WHERE file_path = '__t__.cpp'")
    conn.commit()

    raw = embed_text("测试文本")
    vec_long = "[" + ",".join(str(float(x)) for x in raw) + "]"
    vec_6 = "[" + ",".join(f"{float(x):.6f}" for x in raw) + "]"
    vec_5 = "[" + ",".join(f"{float(x):.5f}" for x in raw) + "]"

    print(f"向量长度：  原样={len(vec_long)}   6位小数={len(vec_6)}   5位小数={len(vec_5)}")
    print()

    base = f"INSERT INTO dbo.debt_memory {COLS} VALUES (?,?,?,?,?,?, %s)"

    print("逐个尝试：")
    try_insert(cur, "A) CAST(? AS VECTOR)                  原样向量",
               base % f"CAST(? AS VECTOR({EMBED_DIM}))", ARGS + (vec_long,))

    try_insert(cur, "B) CAST(? AS VECTOR)                  6位小数",
               base % f"CAST(? AS VECTOR({EMBED_DIM}))", ARGS + (vec_6,))

    try_insert(cur, "C) CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR)  原样向量",
               base % f"CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR({EMBED_DIM}))", ARGS + (vec_long,))

    try_insert(cur, "D) CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR)  6位小数",
               base % f"CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR({EMBED_DIM}))", ARGS + (vec_6,))

    try_insert(cur, "E) 内联字面量 CAST('<vec>' AS VECTOR)        原样向量",
               base % f"CAST('{vec_long}' AS VECTOR({EMBED_DIM}))", ARGS)

    try_insert(cur, "F) 内联字面量 CAST('<vec>' AS VECTOR)        5位小数",
               base % f"CAST('{vec_5}' AS VECTOR({EMBED_DIM}))", ARGS)

    print()
    cur.execute("SELECT COUNT(*) FROM dbo.debt_memory WHERE file_path = '__t__.cpp'")
    print(f"成功写入条数：{cur.fetchone()[0]}")

    cur.execute("DELETE FROM dbo.debt_memory WHERE file_path = '__t__.cpp'")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
