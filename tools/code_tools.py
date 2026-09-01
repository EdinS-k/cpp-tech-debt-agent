# tools/code_tools.py
"""工具层：代码读取 + 上传校验"""
import re
from pathlib import Path

from langchain.tools import tool

from config import CODE_SUFFIXES, MAX_UPLOAD_CHARS, TEST_CODE_PATH

# ---------- 「像不像代码」的特征 ----------
# 预处理指令：几乎所有 C/C++ 文件都有
_PREPROCESSOR = re.compile(r"^\s*#\s*(include|define|pragma|ifndef|ifdef|endif)", re.M)

# 函数定义/声明：类型 + 名字 + 左括号
_FUNC_DEF = re.compile(
    r"\b(?:int|void|char|float|double|bool|long|short|unsigned|signed|size_t|auto|"
    r"std::\w+|struct\s+\w+|class\s+\w+)\s+[\w:*&<>]+\s*\("
)


def looks_like_code(text: str) -> bool:
    """粗略判断一段文本是不是代码（而不是依赖清单 / 纯文本 / 文档）。

    宁松勿严：只要命中任一"强特征"就算代码。
    因为误拒一段真代码，比误放一段文本更糟。
    """
    if not text or not text.strip():
        return False

    # ① 强特征：C/C++ 预处理指令
    if _PREPROCESSOR.search(text):
        return True

    # ② 强特征：函数定义/声明
    if _FUNC_DEF.search(text):
        return True

    # ③ 中等特征：分号 + 大括号同时出现（像代码块）
    if text.count(";") >= 2 and "{" in text and "}" in text:
        return True

    # ④ 中等特征：return + 注释
    if "return" in text and ("//" in text or "/*" in text):
        return True

    return False


def validate_upload(file_name: str, code: str):
    """上传校验。通过返回 (True, "")；不通过返回 (False, 原因)。"""
    suffix = Path(file_name).suffix.lower()
    if suffix not in CODE_SUFFIXES:
        return False, (
            f"不支持的文件类型「{suffix or '无后缀'}」，"
            f"只接受：{', '.join(CODE_SUFFIXES)}"
        )

    if not code or not code.strip():
        return False, "文件内容为空"

    if len(code) > MAX_UPLOAD_CHARS:
        return False, (
            f"文件太大（{len(code):,} 字符，上限 {MAX_UPLOAD_CHARS:,}），请换小一点的文件"
        )

    if not looks_like_code(code):
        return False, "这个文件看起来不含代码（可能是依赖清单或纯文本），已拒绝分析"

    return True, ""


@tool
def scan_code_tool(file_name: str) -> str:
    """读取 test_demo 下的 C/C++ 源码文件内容，用于代码解析。"""
    target = Path(TEST_CODE_PATH) / file_name
    if not target.exists():
        return f"文件不存在: {file_name}"
    return target.read_text(encoding="utf-8")
