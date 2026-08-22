# resources/sqlserver_store.py
"""底层资源层：SQL Server 长期记忆（结构化 + 向量，一张表搞定）。

表 dbo.debt_memory 同时承担三件事：
  · 结构化字段（风险等级/位置/问题/建议） → 精确查询
  · content 全文                          → BM25 关键词检索
  · embedding VECTOR(384)                 → 向量语义检索（VECTOR_DISTANCE）

★ 写入语义是【整体替换】：
    每次分析完某个文件，就用本次结果替换掉它原有的记录。
    为什么要替换而不是追加？
      同一文件反复分析会不断堆积副本，检索 top-3 会被自己的副本占满，
      等于什么都没召回。所以记忆里始终只保留它【当前】的债务清单。

注：SQL Server 2025 的 vector 类型与 VECTOR_DISTANCE 是正式版功能；
    数据量 < 5 万条时用精确搜索即可，无需预览版的向量索引。
"""
import pyodbc

from config import sqlserver_conn_str
from resources.embedding import EMBED_DIM, embed_text, to_sql_vector

_INSERT_SQL = (
    "INSERT INTO dbo.debt_memory "
    "(file_path, risk_level, location, problem, suggestion, content, embedding) "
    # 必须是「两次 CAST」：pyodbc 把 Python 字符串参数当 ntext，
    # 而 SQL Server 不允许 ntext -> vector，所以要先转 NVARCHAR(MAX)。
    f"VALUES (?,?,?,?,?,?, CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR({EMBED_DIM})))"
)


class SqlServerStore:
    def __init__(self):
        self.conn_str = sqlserver_conn_str()
        try:
            self._init_table()
        except Exception as e:
            raise RuntimeError(
                "无法连接 SQL Server。请依次确认：\n"
                "  1) 已在「SQL Server 配置管理器」里启用 TCP/IP 并重启服务\n"
                "  2) 已运行：python scripts/init_sqlserver.py  （建库 + 建表）\n"
                "  3) .env 里的 SQLSERVER_* 配置是否正确\n"
                f"连接串：{self.conn_str}\n"
                f"原始错误：{e}"
            ) from e

    def _connect(self):
        return pyodbc.connect(self.conn_str, timeout=5)

    def _init_table(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                IF OBJECT_ID('dbo.debt_memory', 'U') IS NULL
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
            """)
            conn.commit()

    # ================= 写入：整体替换 =================
    @staticmethod
    def _to_content(item: dict) -> str:
        return (
            f"风险等级：{item['risk_level']}；位置：{item['location']}；"
            f"问题：{item['problem']}；建议：{item['suggestion']}"
        )

    def replace_file_debts(self, file_path: str, items: list) -> int:
        """用本次分析结果【整体替换】该文件的债务记录。

        先删后插，**在同一个事务里** —— 中途出错会整体回滚，
        绝不会出现"旧记录删了、新记录却没写上"。返回实际写入条数。
        """
        with self._connect() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "DELETE FROM dbo.debt_memory WHERE file_path = ?", (file_path,)
                )
                for it in items:
                    content = self._to_content(it)
                    vec = to_sql_vector(embed_text(content))
                    cur.execute(_INSERT_SQL, (
                        file_path,
                        it["risk_level"],
                        it["location"],
                        it["problem"],
                        it["suggestion"],
                        content,
                        vec,
                    ))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return len(items)

    # ================= 查询 =================
    def query_history(self, file_path: str, limit: int = 10):
        """查某文件当前的债务记录（供 query_history_tool）"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT TOP (?) risk_level, location, problem, suggestion "
                "FROM dbo.debt_memory WHERE file_path = ? ORDER BY id DESC",
                (limit, file_path),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def all_documents(self):
        """取全部全文（供 BM25 用）"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT content FROM dbo.debt_memory WHERE content IS NOT NULL")
            return [r[0] for r in cur.fetchall()]

    def vector_search(self, query: str, top_k: int = 3):
        """用 SQL Server 的 VECTOR_DISTANCE 做精确 kNN 语义检索。"""
        qv = to_sql_vector(embed_text(query))
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT TOP (?) content, "
                # 同样要「两次 CAST」：ntext 不能直接转 vector
                f"VECTOR_DISTANCE('cosine', CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR({EMBED_DIM})), embedding) AS distance "
                "FROM dbo.debt_memory WHERE embedding IS NOT NULL ORDER BY distance",
                (top_k, qv),
            )
            return [r[0] for r in cur.fetchall()]


# 单例
sqlserver_store = SqlServerStore()
