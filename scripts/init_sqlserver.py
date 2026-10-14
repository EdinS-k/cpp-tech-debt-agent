"""初始化 SQL Server：建库 + 建表。

用法：python scripts/init_sqlserver.py [--reset]
前提：已在「SQL Server 配置管理器」启用 TCP/IP 并重启服务。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pyodbc

from config import SQLSERVER_DATABASE, sqlserver_conn_str

EMBED_DIM = 384

CREATE_DEBT_TABLE = f"""
CREATE TABLE dbo.debt_memory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    file_path  NVARCHAR(255),
    risk_level NVARCHAR(10),
    location   NVARCHAR(255),
    problem    NVARCHAR(MAX),
    suggestion NVARCHAR(MAX),
    content    NVARCHAR(MAX),
    embedding  VECTOR({EMBED_DIM}),
    create_time DATETIME DEFAULT GETDATE()
)
"""


def main():
    reset = "--reset" in sys.argv

    # ---------- 1) 建库 ----------
    print("① 连接 master ...")
    with pyodbc.connect(sqlserver_conn_str("master"), timeout=5, autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute(
            f"IF DB_ID(N'{SQLSERVER_DATABASE}') IS NULL "
            f"CREATE DATABASE [{SQLSERVER_DATABASE}]"
        )
    print(f"   数据库 [{SQLSERVER_DATABASE}] 已就绪")

    # ---------- 2) 建表 ----------
    print(f"② 连接 [{SQLSERVER_DATABASE}] 处理表结构 ...")
    with pyodbc.connect(sqlserver_conn_str(), timeout=5, autocommit=True) as conn:
        cur = conn.cursor()

        if reset:
            cur.execute(
                "IF OBJECT_ID('dbo.debt_memory','U') IS NOT NULL DROP TABLE dbo.debt_memory"
            )
            print("   已删除旧表 dbo.debt_memory（--reset）")

        try:
            cur.execute(
                "IF OBJECT_ID('dbo.debt_memory','U') IS NULL BEGIN " + CREATE_DEBT_TABLE + " END"
            )
        except Exception as e:
            print(f"   ✗ 建表失败: {str(e)[:200]}")
            print("   如果提示 VECTOR 类型无效，先执行这句再重试：")
            print(f"     ALTER DATABASE [{SQLSERVER_DATABASE}] SET COMPATIBILITY_LEVEL = 170;")
            raise
        print("   表 dbo.debt_memory 已就绪")

        # ---------- 3) 老表升级：补缺失的列 ----------
        cur.execute(
            "SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('dbo.debt_memory')"
        )
        existing = {r[0] for r in cur.fetchall()}

        if "content" not in existing:
            cur.execute("ALTER TABLE dbo.debt_memory ADD content NVARCHAR(MAX)")
            print("   已补列 content")
        if "embedding" not in existing:
            cur.execute(f"ALTER TABLE dbo.debt_memory ADD embedding VECTOR({EMBED_DIM})")
            print("   已补列 embedding")

        # ---------- 4) 体检 ----------
        cur.execute("SELECT COUNT(*) FROM dbo.debt_memory")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM dbo.debt_memory WHERE embedding IS NULL")
        no_vec = cur.fetchone()[0]
        print(f"   当前债务记录：{total} 条（其中 {no_vec} 条没有向量）")

        if no_vec:
            print()
            print("   [提示] 有老记录没有向量，它们不会被语义检索召回。")
            print("          想清空重来：python scripts/clean_memory.py --delete-all")

    print()
    print("完成，可以启动项目了：python main.py")


if __name__ == "__main__":
    main()
