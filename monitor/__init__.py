"""
监控模块

提供实时监控爬取功能，包括：
- 定时轮询爬取新文章
- Rich 实时监控界面
- 状态管理与统计
- 跨平台键盘监听
"""

from .keyboard import KeyboardListener
from .scheduler import CrawlScheduler
from .state import ArticleRecord, MonitorState, PollRecord
from .ui import MonitorUI
from .utils import (
    PidFileManager,
    ThreadSafeSet,
    TokenBucketRateLimiter,
    check_disk_space,
    retry_with_backoff,
)

__all__ = [
    # 状态管理
    "ArticleRecord",
    "MonitorState",
    "PollRecord",
    # 调度器
    "CrawlScheduler",
    # UI
    "MonitorUI",
    "KeyboardListener",
    # 工具
    "PidFileManager",
    "ThreadSafeSet",
    "TokenBucketRateLimiter",
    "check_disk_space",
    "retry_with_backoff",
    # 入口
    "run_monitor",
]


def run_monitor(*args, **kwargs):
    """懒加载入口，避免 `python -m monitor.runner` 时包级预加载子模块。"""
    from .runner import run_monitor as _run_monitor

    return _run_monitor(*args, **kwargs)
