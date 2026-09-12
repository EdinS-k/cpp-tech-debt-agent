# agent/summary_agent.py
"""Agent 核心层：③ 总结 Agent

职责：把前面的结果汇总成报告，并用本次结果【整体替换】该文件的长期记忆。

★ 两条分支都会写记忆：
  · 详细分支（有高风险）→ 调 LLM 生成完整报告
  · 简短分支（无高风险）→ 不调 LLM，直接给一句话结论

"""
import json
import logging

from langchain_core.messages import AIMessage

from agent.prompts import SUMMARY_AGENT_PROMPT
from agent.state import GraphState
from resources.llm import llm
from tools.memory_tools import save_debt_snapshot_tool

logger = logging.getLogger(__name__)


def _save_snapshot(state: GraphState):
    """把本次的债务条目整体写入长期记忆（两条分支共用）。"""
    file_name = state.get("file_name", "unknown")
    items = state.get("debt_items") or []

    # ---------- 安全网 ----------
    # 风险报告里明明有风险标记，却一条都没解析出来 => 疑似解析失败。
    # 这时【绝不能】用空列表去替换，否则会把原来的好数据误删。
    risk_text = state.get("risk_result") or ""
    if not items and any(m in risk_text for m in ("🔴", "🟡", "🟢")):
        logger.error(
            "解析出 0 条债务，但风险报告里有风险标记 —— 疑似解析失败，"
            "本次不替换长期记忆以免误删（文件：%s）",
            file_name,
        )
        return

    try:
        result = save_debt_snapshot_tool.invoke({
            "file_path": file_name,
            "debt_items_json": json.dumps(items, ensure_ascii=False),
        })
        logger.info("保存记忆 → %s", result)
    except Exception as e:
        logger.warning("保存记忆失败: %s", e)


def summary_agent_node(state: GraphState):
    # ---------- 第 1 步：生成报告 ----------
    prompt = SUMMARY_AGENT_PROMPT + "\n风险评估：" + state["risk_result"]
    resp = llm.invoke(prompt)
    report = resp.content or ""

    # ---------- 第 2 步：整体替换长期记忆 ----------
    _save_snapshot(state)

    # ---------- 第 3 步：追加到结构化消息列表（短期记忆） ----------
    return {"final_report": report, "messages": [AIMessage(content=report)]}


def quick_summary_node(state: GraphState):
    """[简短分支] 没有高风险走这条：不调 LLM，直接给一句话总结。

    但仍然要写记忆 —— 否则"债务已修复"永远反映不到长期记忆里。
    """
    report = "✅ 本次分析未发现高风险问题，代码整体良好。"
    _save_snapshot(state)
    return {"final_report": report, "messages": [AIMessage(content=report)]}
