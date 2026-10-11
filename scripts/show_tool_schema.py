"""展示 function calling 实际发给模型的 JSON Schema。

用法：python scripts/show_tool_schema.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_core.utils.function_calling import convert_to_openai_tool


def show(tool):
    print(f"---------- {tool.name} ----------")
    print(json.dumps(convert_to_openai_tool(tool), ensure_ascii=False, indent=2))
    print()


def main():
    print("=" * 70)
    print("这就是 bind_tools() 塞进 HTTP 请求 tools 字段的内容")
    print("=" * 70)
    print()

    tools = []
    try:
        from tools.memory_tools import query_history_tool
        from tools.retrieval_tools import bm25_search_tool, hybrid_search_tool, vector_search_tool

        tools = [hybrid_search_tool, vector_search_tool, bm25_search_tool, query_history_tool]
        print(f"[OK] 加载了项目真实工具 {len(tools)} 个")
        print()
    except Exception as e:
        from langchain_core.tools import tool

        @tool
        def hybrid_search_tool(query: str, top_k: int = 3) -> str:
            """混合检索（向量 + BM25 → RRF 融合）。兼顾语义与关键词，最稳妥，默认用它。"""
            return ""

        tools = [hybrid_search_tool]
        print(f"[!] 项目工具加载失败（{str(e)[:70]}）")
        print("    用等价示例工具演示（Schema 结构完全一样）")
        print()

    for t in tools:
        show(t)


if __name__ == "__main__":
    main()
