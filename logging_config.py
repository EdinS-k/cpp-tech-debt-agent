# logging_config.py
"""统一日志配置：同时输出到【控制台】和【文件】。

为什么值得单独一个文件？
  · 控制台看着爽，但窗口一关、或者被刷屏滚上去，就找不回来了
  · 文件日志能回查 —— "刚才那次分析，模型到底选了哪个工具？"

日志文件：logs/app.log
  · 超过 5MB 自动切割，最多保留 5 份历史（app.log.1 / .2 ...）
  · 控制台用精简格式（方便盯每一步）
  · 文件用详细格式（带模块名和行号，方便定位）
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "app.log"

_MAX_BYTES = 5 * 1024 * 1024   # 单个日志文件上限 5 MB
_BACKUPS = 5                   # 保留几份历史


def setup_logging(level=logging.INFO) -> Path:
    """初始化日志系统，返回日志文件路径。"""
    LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # 清掉已有 handler，避免重复输出（比如 uvicorn 重载时）
    for h in root.handlers[:]:
        root.removeHandler(h)

    # ---------- ① 控制台 ----------
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(console)

    # ---------- ② 文件（自动切割） ----------
    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUPS,
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s"
    ))
    root.addHandler(fh)

    return LOG_FILE
