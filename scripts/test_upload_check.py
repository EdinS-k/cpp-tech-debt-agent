"""测试上传校验逻辑（纯本地，不需要数据库）。

用法：python scripts/test_upload_check.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.code_tools import looks_like_code, validate_upload

CPP = '''
#include <iostream>
#include <cstring>

char global_buf[100];

void old_func() {
    strcpy(global_buf, "hello");
    return;
}

int main() {
    old_func();
    return 0;
}
'''

TXT_DEPS = """
numpy==1.24.0
pandas==2.0.1
requests==2.31.0
flask>=2.0
"""

PLAIN = """
这是一份说明文档。
本项目用于分析技术债务。
请阅读 README 了解详情。
"""

TINY_CPP = "int add(int a, int b) { return a + b; }"


def main():
    print("=" * 74)
    print("[1] looks_like_code() 单项测试")
    print("-" * 74)
    for label, text in [
        ("标准 C++ 代码", CPP),
        ("超短 C++", TINY_CPP),
        ("依赖清单 txt", TXT_DEPS),
        ("纯中文文档", PLAIN),
        ("空内容", ""),
    ]:
        print(f"    {label:<16} -> {looks_like_code(text)}")

    print()
    print("=" * 74)
    print("[2] validate_upload() 完整校验")
    print("-" * 74)
    cases = [
        ("正常 C++ 文件", "main.cpp", CPP),
        ("头文件", "utils.h", CPP),
        ("依赖清单 txt", "requirements.txt", TXT_DEPS),
        ("纯文档 txt", "readme.txt", PLAIN),
        ("超短 C++", "tiny.cpp", TINY_CPP),
        ("空文件", "empty.cpp", ""),
        ("超大文件", "big.cpp", CPP * 5000),
        ("后缀不对(内容像代码)", "main.py", CPP),
        ("无后缀", "Makefile", CPP),
    ]
    for label, fname, text in cases:
        ok, reason = validate_upload(fname, text)
        mark = "通过" if ok else "拒绝"
        print(f"    [{mark}] {label:<22} {reason}")
    print("=" * 74)


if __name__ == "__main__":
    main()
