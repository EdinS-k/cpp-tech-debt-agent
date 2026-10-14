"""测试债务条目的批内去重（用假 store，不需要数据库）。

用法：python scripts/test_dedup.py
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeStore:
    """假存储：只记录"被要求写入什么"，不碰数据库。"""

    def __init__(self):
        self.saved = None

    def replace_file_debts(self, file_path, items):
        self.saved = items
        return len(items)


# ★ 依赖桩：必须在 import rag_pipeline 之前
_fake_mod = types.ModuleType("resources.sqlserver_store")
_fake_mod.sqlserver_store = FakeStore()
sys.modules["resources.sqlserver_store"] = _fake_mod

from resources.rag_pipeline import RagPipeline   # noqa: E402


def main():
    fake = FakeStore()
    pipe = RagPipeline(store=fake)

    items = [
        {"risk_level": "高", "location": "old_func()", "problem": "越界", "suggestion": "加检查"},
        {"risk_level": "高", "location": "old_func()", "problem": "越界", "suggestion": "加检查"},   # 完全重复
        {"risk_level": "中", "location": "mem_leak()", "problem": "内存泄漏", "suggestion": "free"},
        {"risk_level": "低", "location": "", "problem": "", "suggestion": ""},                       # 空条目
        {"risk_level": "", "location": "  x()  ", "problem": "  未初始化  ", "suggestion": ""},      # 空格 + 缺等级
    ]

    print("=" * 74)
    print(f"输入 {len(items)} 条（1 条完全重复 / 1 条全空 / 1 条带多余空格）")
    n = pipe.replace_debt_items("demo.cpp", items)
    print(f"实际写入 {n} 条：")
    print("-" * 74)
    for it in fake.saved:
        print(f"   [{it['risk_level']}] {it['location']!r} | {it['problem']!r} | {it['suggestion']!r}")
    print("=" * 74)


if __name__ == "__main__":
    main()
