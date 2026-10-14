# agent/state.py
"""Agent 核心层：LangGraph 的状态定义（也就是各 Agent 共享的"黑板"）。
单独放一个文件，是为了让 3 个 Agent 和编排图都能引用它，又不产生循环 import。
"""
from typing import TypedDict, Annotated

from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    # ---------- 输入 ----------
    user_query: str        # 用户这次问的问题
    file_name: str         # 要分析的文件名
    code_content: str      # 代码内容（上传时直接带入；为空则用 scan_code_tool 从磁盘读）

    # ---------- 预检 ----------
    is_code: bool          # ⓪ 预检结论：输入到底是不是代码（不通过时原因写进 final_report）

    # ---------- 各 Agent 的产出 ----------
    parse_result: str      # ① 代码解析结果
    risk_result: str       # ② 风险评估结果
    final_report: str      # ③ 总结报告
    debt_items: list       # ② 解析出的结构化债务记录

    # ---------- 短期记忆 ----------
    messages: Annotated[list, add_messages]   # 结构化消息列表（多轮对话）
