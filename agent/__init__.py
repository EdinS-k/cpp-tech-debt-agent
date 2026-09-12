"""Agent 核心层：代码解析 / 风险评估 / 总结 三个 Agent，以及 LangGraph 编排。
-precheck.py               文档检查
- code_parser_agent.py  ① 代码解析 Agent
- risk_agent.py         ② 风险评估 Agent（带检索）
- summary_agent.py      ③ 总结 Agent（写入长期记忆）
- state.py              状态定义（黑板）
- prompts.py            三个 Agent 的提示词
- graph.py              编排图
"""
