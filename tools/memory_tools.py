# tools/memory_tools.py
"""工具层：长期记忆的写入与查询（都落在 SQL Server）"""
import json

from langchain.tools import tool

from resources.rag_pipeline import rag_pipeline
from resources.sqlserver_store import sqlserver_store


@tool
def save_debt_snapshot_tool(file_path: str, debt_items_json: str) -> str:
    """把本次分析出的债务条目【整体替换】进长期记忆。

    debt_items_json 是 JSON 数组字符串，例如：
        [{"risk_level":"高","location":"old_func()","problem":"越界","suggestion":"加检查"}]

    注意是「整体替换」不是「追加」——
    同一个文件重复分析不会产生重复记录，记忆里始终是它【当前】的债务清单。
    """
    try:
        items = json.loads(debt_items_json or "[]")
    except Exception as e:
        return f"债务条目的 JSON 解析失败: {e}"

    if not isinstance(items, list):
        return "债务条目格式不对：应该是 JSON 数组"

    try:
        n = rag_pipeline.replace_debt_items(file_path, items)
        return f"已更新长期记忆：{file_path} 现有 {n} 条债务"
    except Exception as e:
        return f"保存失败: {e}"


@tool
def query_history_tool(file_path: str, limit: int = 10) -> str:
    """查询某个文件【当前】的债务记录（SQL Server）。"""
    records = sqlserver_store.query_history(file_path, limit=limit)
    if not records:
        return "无历史记录"
    return "\n".join(
        f"[{r['risk_level']}] 位置：{r['location']}；问题：{r['problem']}；建议：{r['suggestion']}"
        for r in records
    )
