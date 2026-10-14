"""查看 / 清理长期记忆（debt_memory 表），裸 SQL 直连，不依赖项目代码。

用法：python scripts/clean_memory.py [--show 文件 | --delete 文件 | --delete-all]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pyodbc

from config import sqlserver_conn_str

LINE = "=" * 70


def connect():
    return pyodbc.connect(sqlserver_conn_str(), timeout=5)


# ==================== 默认：健康检查 + 按文件分组 ====================
def cmd_list():
    print(LINE)
    print("【长期记忆 debt_memory】")

    with connect() as conn:
        cur = conn.cursor()

        # ---------- 健康检查 ----------
        cur.execute("SELECT COUNT(*) FROM dbo.debt_memory")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM dbo.debt_memory WHERE embedding IS NOT NULL")
        with_vec = cur.fetchone()[0]

        print(f"  总记录数     : {total}")
        print(f"  带向量的记录 : {with_vec}")
        if total > with_vec:
            print(f"  [!] 有 {total - with_vec} 条没有向量 —— 它们不会被语义检索召回")

        if not total:
            print()
            print("  (表是空的 —— 去网页分析一次就会写入)")
            print(LINE)
            return

        # ---------- 按文件分组 ----------
        cur.execute(
            "SELECT file_path, COUNT(*) AS n, MAX(create_time) AS last_time "
            "FROM dbo.debt_memory GROUP BY file_path ORDER BY n DESC"
        )
        rows = cur.fetchall()
        print()
        print("  按文件分组：")
        print(f"  {'文件':<32}{'债务数':>7}   最后更新")
        print("  " + "-" * 66)
        for fp, n, t in rows:
            print(f"  {str(fp):<32}{n:>7}   {t}")

    print()
    print("  看明细：python scripts/clean_memory.py --show 文件名")
    print("  删记录：python scripts/clean_memory.py --delete 文件名")
    print("  清空表：python scripts/clean_memory.py --delete-all")
    print(LINE)


# ==================== --show ====================
def cmd_show(file_path: str):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, risk_level, location, problem, create_time "
            "FROM dbo.debt_memory WHERE file_path = ? ORDER BY id",
            (file_path,),
        )
        rows = cur.fetchall()
        if not rows:
            print(f"没有 file_path = {file_path} 的记录")
            return
        print(f"{file_path} 当前 {len(rows)} 条债务：")
        print("-" * 78)
        for r in rows:
            print(f"[{r[0]}] {str(r[1]):<2} | {str(r[2])[:24]:<24} | {str(r[3])[:38]}")


# ==================== --delete ====================
def cmd_delete(file_path: str):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM dbo.debt_memory WHERE file_path = ?", (file_path,)
        )
        n = cur.fetchone()[0]
        if not n:
            print(f"没有 file_path = {file_path} 的记录，无需删除")
            return
        cur.execute("DELETE FROM dbo.debt_memory WHERE file_path = ?", (file_path,))
        conn.commit()
        print(f"已删除 {n} 条记录（file_path = {file_path}）")


# ==================== --delete-all ====================
def cmd_delete_all():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dbo.debt_memory")
        n = cur.fetchone()[0]
        if not n:
            print("表本来就是空的")
            return
        cur.execute("DELETE FROM dbo.debt_memory")
        conn.commit()
        print(f"已清空 debt_memory：删掉 {n} 条记录")


def main():
    args = sys.argv[1:]
    try:
        if not args:
            cmd_list()
        elif args[0] == "--show" and len(args) > 1:
            cmd_show(args[1])
        elif args[0] == "--delete" and len(args) > 1:
            cmd_delete(args[1])
        elif args[0] == "--delete-all":
            cmd_delete_all()
        else:
            print(__doc__)
    except pyodbc.Error as e:
        print(LINE)
        print("连接 SQL Server 失败：")
        print(f"  {str(e)[:400]}")
        print()
        print("请依次确认：")
        print("  1) 已在「SQL Server 配置管理器」启用 TCP/IP 并重启服务")
        print("  2) 已运行：python scripts/init_sqlserver.py")
        print("  3) .env 里的 SQLSERVER_* 配置正确")
        print(LINE)


if __name__ == "__main__":
    main()
