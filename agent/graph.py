# agent/graph.py
"""Agent 核心层：把节点编排成一张 LangGraph 状态图。

                      ┌─[不是代码]──────────────────────────────► END
    START ─► ⓪预检 ─┤
                      └─[是代码]─► ①代码解析 ─► ②风险评估 ─┬─[有高风险]─► ③详细总结 ─┐
                                                            └─[无高风险]─► 简短总结 ─┴─► END

"""
import logging

from langgraph.graph import StateGraph, START, END

from agent.state import GraphState
from agent.precheck import precheck_node, route_after_precheck
from agent.code_parser_agent import code_parser_node
from agent.risk_agent import risk_agent_node
from agent.summary_agent import summary_agent_node, quick_summary_node

logger = logging.getLogger(__name__)


def route_by_risk(state: GraphState):
    """路由函数：有[高]风险走详细报告，没有就走简短报告。"""
    for item in state.get("debt_items") or []:
        if item.get("risk_level") == "高":
            logger.info(">>> [路由] 发现高风险 → 走【详细报告】")
            return "detailed"
    logger.info(">>> [路由] 没有高风险 → 走【简短报告】")
    return "quick"

def build_graph(checkpointer=None):
    builder = StateGraph(GraphState)

    # 注册节点 1.检查2.代码解读3.风险分析4.总结【深度，轻度】
    builder.add_node("precheck", precheck_node)
    builder.add_node("code_parser", code_parser_node)
    builder.add_node("risk_agent", risk_agent_node)
    builder.add_node("summary_agent", summary_agent_node)
    builder.add_node("quick_summary", quick_summary_node)


    builder.add_edge(START, "precheck")
    #检查文件是否合规
    builder.add_conditional_edges(
        "precheck",
        route_after_precheck,
        {"go": "code_parser", "reject": END},
    )

    builder.add_edge("code_parser", "risk_agent")
    #判断风险大小选择总结难度
    builder.add_conditional_edges(
        "risk_agent",
        route_by_risk,
        {"detailed": "summary_agent", "quick": "quick_summary"},
    )

    builder.add_edge("summary_agent", END)
    builder.add_edge("quick_summary", END)

    return builder.compile(checkpointer=checkpointer)
