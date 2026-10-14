# agent/risk_agent.py
"""Agent 核心层：② 风险评估 Agent（自主调用工具版）
"""
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agent.prompts import RISK_AGENT_PROMPT
from agent.state import GraphState
from resources.llm import llm
from tools.memory_tools import query_history_tool
from tools.retrieval_tools import bm25_search_tool, hybrid_search_tool, vector_search_tool

logger = logging.getLogger(__name__)

# ★ 交给模型挑选的工具集合（想扩展就改这一行）
AGENT_TOOLS = [
    hybrid_search_tool,
    vector_search_tool,
    bm25_search_tool,
    query_history_tool,
]
TOOL_MAP = {t.name: t for t in AGENT_TOOLS}

MAX_TOOL_ROUNDS = 3   # 最多允许模型调几轮工具（防止无限循环）


def parse_risk_markdown(text: str):
    """把风险评估输出的 Markdown 解析成结构化债务记录列表。"""
    items = []
    blocks = re.split(r"\n\s*(?=###\s)", text or "")
    for block in blocks:
        head = re.match(r"###\s*([🔴🟡🟢⚪]?)\s*(高|中|低)?\s*风险\s*[:：]?\s*(.*)", block.strip())
        if not head:
            continue
        emoji = head.group(1) or ""
        level = head.group(2) or {"🔴": "高", "🟡": "中", "🟢": "低"}.get(emoji, "中")

        def field(name):
            m = re.search(r"\*{0,2}\s*" + name + r"\s*\*{0,2}\s*[:：]\s*(.*)", block)
            return m.group(1).strip() if m else ""

        location = field("位置")
        problem = field("原因") or field("问题")
        suggestion = field("建议")
        if location or problem:
            items.append({
                "risk_level": level,
                "location": location,
                "problem": problem,
                "suggestion": suggestion,
            })
    return items


def _execute_tools(tool_calls):
    """执行模型要求的工具调用，返回对应的 ToolMessage 列表。"""
    out = []
    for tc in tool_calls:
        name = tc.get("name")
        args = tc.get("args", {}) or {}
        tool = TOOL_MAP.get(name)

        if tool is None:
            logger.warning("模型调用了未注册的工具: %s", name)
            content = f"未知工具: {name}"
        else:
            try:
                content = tool.invoke(args)
            except Exception as e:
                logger.warning("工具 %s 调用失败: %s", name, e)
                content = f"工具调用失败: {e}"

        logger.info(">>> [工具] 模型选择了 %s(%s)", name, args)
        out.append(ToolMessage(content=str(content), tool_call_id=tc.get("id")))

    return out


def risk_agent_node(state: GraphState):
    llm_with_tools = llm.bind_tools(AGENT_TOOLS)

    messages = [
        SystemMessage(content=RISK_AGENT_PROMPT),
        HumanMessage(content=(
            "以下是待评估代码的解析结果：\n"
            f"{state['parse_result']}\n\n"
            "请按需调用工具检索历史项目记忆，然后输出风险评估。"
        )),
    ]

    resp = None
    for round_no in range(1, MAX_TOOL_ROUNDS + 1):
        resp = llm_with_tools.invoke(messages)

        if not resp.tool_calls:
            break                      # 模型不再要工具 → 说明在输出结论了

        logger.info(">>> [工具] 第 %d 轮：模型要求调用 %d 个工具", round_no, len(resp.tool_calls))
        messages.append(resp)
        messages.extend(_execute_tools(resp.tool_calls))
    else:
        # 轮次用完还在调工具 → 强制出结论
        logger.info(">>> [工具] 轮次已达上限，强制生成结论")
        messages.append(HumanMessage(content="不要再调用工具，请直接输出风险评估结果。"))
        resp = llm_with_tools.invoke(messages)

    risk_result = (resp.content if resp else "") or ""

    # 兜底：模型光调工具、没输出正文
    if not str(risk_result).strip():
        logger.warning("模型未输出正文，补一次纯文本调用")
        messages.append(HumanMessage(content="请直接输出风险评估结果。"))
        risk_result = llm.invoke(messages).content or ""

    # 解析成结构化记录，交给总结 Agent 入库
    return {"risk_result": risk_result, "debt_items": parse_risk_markdown(risk_result)}
