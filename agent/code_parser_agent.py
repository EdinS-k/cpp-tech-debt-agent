# agent/code_parser_agent.py
"""Agent 核心层：① 代码解析 Agent

职责：拿到源码 → 提取函数清单 / 代码异味 / 技术债务线索。
"""
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from agent.prompts import CODE_PARSER_PROMPT
from agent.state import GraphState
from config import MAX_CODE_CHARS
from resources.llm import llm
from tools.code_tools import scan_code_tool

logger = logging.getLogger(__name__)


def code_parser_node(state: GraphState):
    # 优先用"上传/预置"的代码；没有才用工具从磁盘读
    code = state.get("code_content") or ""
    if not code:
        try:
            code = scan_code_tool.invoke({"file_name": state["file_name"]})
        except Exception as e:
            logger.warning("scan_code_tool 读取源码失败: %s", e)

    # 超长截断：只截断「送给模型的那一份」，state 里仍保留完整代码
    code_for_llm = code
    if len(code) > MAX_CODE_CHARS:
        logger.warning(
            "代码过长（%d 字符），只把前 %d 字符送给模型", len(code), MAX_CODE_CHARS
        )
        code_for_llm = code[:MAX_CODE_CHARS] + "\n\n// ...（代码过长，已截断）"

    # 用【结构化消息列表】作为上下文（含历史对话 + 当前提问）
    msgs = [SystemMessage(content=CODE_PARSER_PROMPT)]
    msgs += list(state.get("messages") or [])
    msgs.append(HumanMessage(content="要分析的代码：\n" + code_for_llm))

    resp = llm.invoke(msgs)
    return {"parse_result": resp.content, "code_content": code}
