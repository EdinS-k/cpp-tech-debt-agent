# agent/precheck.py
"""Agent 核心层：⓪ 预检节点（图的第一道闸门）
"""
import logging

from agent.state import GraphState
from tools.code_tools import looks_like_code

logger = logging.getLogger(__name__)


def precheck_node(state: GraphState):
    """检查输入；不通过就记下原因，交给条件边决定是否短路。"""
    code = state.get("code_content") or ""
    file_name = state.get("file_name") or "unknown"

    # 内容为空 => 可能是要走 scan_code_tool 从磁盘读（内置示例），放行
    if not code.strip():
        logger.info(">>> [预检] 无代码内容，交给解析节点从磁盘读取：%s", file_name)
        return {"is_code": True}

    if not looks_like_code(code):
        reason = (
            f"⚠️ 「{file_name}」看起来不含代码，已跳过后续分析。\n\n"
            f"（这样做是为了避免白白消耗大模型调用，也避免把无关内容写进长期记忆）"
        )
        logger.warning(">>> [预检] 未通过：%s（%d 字符）", file_name, len(code))
        return {"is_code": False, "final_report": reason}

    logger.info(">>> [预检] 通过：%s（%d 字符）", file_name, len(code))
    return {"is_code": True}


def route_after_precheck(state: GraphState):
    """条件边：是代码就去解析，不是就直接结束。"""
    return "go" if state.get("is_code", True) else "reject"
