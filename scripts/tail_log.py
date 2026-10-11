"""实时跟踪日志文件（相当于 Linux 的 tail -f）。

用法（cmd / PowerShell 都能用）：
    python scripts/tail_log.py          # 显示最后 30 行 + 实时跟踪
    python scripts/tail_log.py 100      # 显示最后 100 行 + 实时跟踪

按 Ctrl+C 退出。
"""
import sys
import time
from pathlib import Path

# 让输出更宽容：万一遇到控制台编码不支持的字符（如 BOM），也只是显示成 ?，不会崩
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "app.log"

lines = 30
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    lines = int(sys.argv[1])


def main():
    if not LOG.exists():
        print(f"[!] 日志文件还不存在：{LOG}")
        print("    请先运行 python main.py，并在网页上做一次分析。")
        return

    print(f"实时跟踪：{LOG}")
    print(f"（先显示最后 {lines} 行，之后实时输出新日志；按 Ctrl+C 退出）")
    print("-" * 72)

    # utf-8-sig：兼容带 BOM 的文件（我们自己的日志没有 BOM，但多一层保险）
    with LOG.open("r", encoding="utf-8-sig", errors="replace") as f:
        for line in f.readlines()[-lines:]:
            print(line.rstrip())

        while True:
            line = f.readline()
            if line:
                print(line.rstrip(), flush=True)
            else:
                time.sleep(0.3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + "-" * 72)
        print("已退出")
