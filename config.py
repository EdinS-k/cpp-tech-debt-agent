# config.py
"""全局配置：统一从 .env 读取，集中管理路径与参数。"""
import os

from dotenv import load_dotenv

load_dotenv()

# ---------- LLM ----------
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

# ---------- 长期记忆（SQL Server：结构化 + 向量）----------
SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
SQLSERVER_SERVER = os.getenv("SQLSERVER_SERVER", "localhost,1433")
SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE", "tech_debt_db")
SQLSERVER_TRUSTED = os.getenv("SQLSERVER_TRUSTED", "yes")      # yes = 用 Windows 身份验证
SQLSERVER_ENCRYPT = os.getenv("SQLSERVER_ENCRYPT", "no")
SQLSERVER_TRUST_CERT = os.getenv("SQLSERVER_TRUST_CERT", "yes")


def sqlserver_conn_str(database: str = None) -> str:
    """拼 SQL Server 的 ODBC 连接字符串。

    默认连项目库；传 "master" 可连系统库（用于建库）。
    """
    db = database or SQLSERVER_DATABASE
    return (
        f"DRIVER={{{SQLSERVER_DRIVER}}};"
        f"SERVER={SQLSERVER_SERVER};"
        f"DATABASE={db};"
        f"Trusted_Connection={SQLSERVER_TRUSTED};"
        f"Encrypt={SQLSERVER_ENCRYPT};"
        f"TrustServerCertificate={SQLSERVER_TRUST_CERT};"
    )

# ---------- 检索 ----------
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "3"))

# ---------- 待分析源码 ----------
TEST_CODE_PATH = os.getenv("TEST_CODE_PATH", "./test_demo")

# ---------- 上传校验（防止非代码文件白白消耗 token）----------
# 允许分析的源码后缀
CODE_SUFFIXES = [
    s.strip().lower()
    for s in os.getenv("CODE_SUFFIXES", ".cpp,.h,.hpp,.cc").split(",")
    if s.strip()
]
# 上传文件最大字符数（超过直接拒绝）
MAX_UPLOAD_CHARS = int(os.getenv("MAX_UPLOAD_CHARS", "200000"))
# 送给大模型的代码最大字符数（超过就截断，控制 token）
MAX_CODE_CHARS = int(os.getenv("MAX_CODE_CHARS", "8000"))

if not LLM_API_KEY:
    raise RuntimeError("请在项目根目录创建 .env，填写 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME")
