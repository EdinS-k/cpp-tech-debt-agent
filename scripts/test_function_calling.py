"""测试 DeepSeek 的 function calling（工具调用）能力。

用法：python scripts/test_function_calling.py
（输出只用 ASCII，避免 GBK 控制台编码报错）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_core.tools import tool

from resources.llm import llm


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    return f"{city}：晴，25℃"


@tool
def get_population(city: str) -> int:
    """查询指定城市的人口。"""
    return 21893095


def main():
    print("=" * 64)
    print("[1] Bind tools to model ...")
    llm_with_tools = llm.bind_tools([get_weather, get_population])
    print("    OK (2 tools bound)")

    # ---------- [2] 绑定项目真实工具 ----------
    print()
    print("[2] Bind PROJECT tools ...")
    llm_proj = None
    try:
        from tools.memory_tools import query_history_tool
        from tools.retrieval_tools import bm25_search_tool, hybrid_search_tool, vector_search_tool

        project_tools = [vector_search_tool, bm25_search_tool, hybrid_search_tool, query_history_tool]
        for t in project_tools:
            print(f"    - {t.name:<22} args={list(t.args.keys())}")
        llm_proj = llm.bind_tools(project_tools)
        print("    OK (4 tools bound)")
    except Exception as e:
        print(f"    FAILED: {type(e).__name__}: {str(e)[:200]}")
        print("    (如果报 SQL Server 连接错误，说明是数据库没连上，不是工具的问题)")

    # ---------- [3] 测简单工具调用 ----------
    print()
    print("[3] Ask: '北京今天天气怎么样？'")
    try:
        resp = llm_with_tools.invoke("北京今天天气怎么样？")
        print(f"    content    : {resp.content!r}")
        print(f"    tool_calls : {resp.tool_calls}")
        if resp.tool_calls:
            print("    [OK] function calling supported")
        else:
            print("    [!] model did not call any tool")
    except Exception as e:
        print(f"    FAILED: {type(e).__name__}: {str(e)[:200]}")

    # ---------- [4] 测"自己选检索策略" ----------
    if llm_proj is not None:
        print()
        print("[4] Ask: 查 global_buf 的历史（精确标识符 -> 应该选 bm25）")
        try:
            resp = llm_proj.invoke(
                "请从长期记忆里查一下和 global_buf 相关的历史记录。"
                "注意：global_buf 是一个精确的变量名。"
            )
            print(f"    content : {str(resp.content)[:120]!r}")
            for tc in (resp.tool_calls or []):
                print(f"    -> chose tool: {tc['name']}   args={tc['args']}")
            if resp.tool_calls:
                print("    [OK] model chose a retrieval strategy by itself")
            else:
                print("    [!] no tool called")
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {str(e)[:200]}")

        print()
        print("[5] Ask: 查'内存安全问题'的历史（语义 -> 应该选 vector/hybrid）")
        try:
            resp = llm_proj.invoke("请查一下历史上关于内存安全问题的记录。")
            for tc in (resp.tool_calls or []):
                print(f"    -> chose tool: {tc['name']}   args={tc['args']}")
            if not resp.tool_calls:
                print("    [!] no tool called")
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {str(e)[:200]}")

    print("=" * 64)


if __name__ == "__main__":
    main()
