"""
监控状态管理

提供线程安全的状态管理，包括：
- 运行状态跟踪
- 今日统计（自动每日重置）
- 最近爬取文章列表
- 轮询历史记录
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from crawl.pipeline import CrawlResult


@dataclass
class ArticleRecord:
    """单篇文章记录"""

    keyword: str
    article_id: str
    title: str
    publish_time: str
    crawl_time: datetime
    status: str  # "success" | "failed"


@dataclass
class PollRecord:
    """单次轮询记录"""

    keyword: str
    poll_time: datetime
    new_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    elapsed_seconds: float


class MonitorState:
    """
    监控状态管理器（线程安全）

    Attributes:
        status: 运行状态 ("idle" | "running" | "paused" | "error")
        last_error: 最近一次错误信息
        next_poll_time: 下次轮询时间
        today_*: 今日统计数据
        recent_articles: 最近爬取的文章列表
        poll_history: 轮询历史记录
    """

    def __init__(self, recent_limit: int = 20, poll_history_limit: int = 10) -> None:
        """
        初始化监控状态

        Args:
            recent_limit: 最近文章列表最大数量
            poll_history_limit: 轮询历史最大数量
        """
        self._lock = threading.RLock()
        self._recent_limit = recent_limit
        self._poll_history_limit = poll_history_limit
        self._last_reset_date = datetime.now().date()
        self._start_time = datetime.now()
        self._active_polls = 0
        self._paused = False
        self._next_poll_times: Dict[str, Optional[datetime]] = {}

        # 运行状态
        self.status: str = "idle"
        self.last_error: Optional[str] = None
        self.next_poll_time: Optional[datetime] = None

        # 今日统计
        self.today_total: int = 0
        self.today_success: int = 0
        self.today_failed: int = 0
        self.today_skipped: int = 0

        # 累计统计
        self.total_polls: int = 0

        # 列表数据
        self.recent_articles: List[ArticleRecord] = []
        self.poll_history: List[PollRecord] = []

    def _check_daily_reset(self, now: datetime) -> None:
        """检查并执行每日重置（需持锁）"""
        if now.date() != self._last_reset_date:
            self.today_total = 0
            self.today_success = 0
            self.today_failed = 0
            self.today_skipped = 0
            self._last_reset_date = now.date()
            print("📅 已重置今日统计（跨日）")

    def check_daily_reset(self) -> None:
        """主动触发日期检查"""
        with self._lock:
            self._check_daily_reset(datetime.now())

    def set_status(self, status: str) -> None:
        """
        更新运行状态

        Args:
            status: 新状态，可选值 "idle" | "running" | "paused" | "error"

        Note:
            当 status 不是 "error" 时，会自动清空 last_error。
        """
        with self._lock:
            self._check_daily_reset(datetime.now())
            self.status = status
            if status != "error":
                self.last_error = None

    def set_paused(self, paused: bool) -> None:
        """设置全局暂停状态"""
        with self._lock:
            self._check_daily_reset(datetime.now())
            self._paused = paused
            if self._active_polls > 0 or self.status == "error":
                return
            self.status = "paused" if paused else "idle"
            if self.status != "error":
                self.last_error = None

    def begin_poll(self) -> None:
        """开始一次轮询（并发安全）"""
        with self._lock:
            self._check_daily_reset(datetime.now())
            self._active_polls += 1
            self.status = "running"
            self.last_error = None

    def end_poll(self, had_error: bool = False) -> None:
        """结束一次轮询（并发安全）"""
        with self._lock:
            self._check_daily_reset(datetime.now())
            if self._active_polls > 0:
                self._active_polls -= 1
            if had_error or self.status == "error":
                return
            if self._active_polls == 0:
                self.status = "paused" if self._paused else "idle"
                self.last_error = None

    def set_error(self, message: str) -> None:
        """记录错误并切换为错误状态"""
        with self._lock:
            self._check_daily_reset(datetime.now())
            self.status = "error"
            self.last_error = message

    def set_next_poll_time(self, next_time: Optional[datetime]) -> None:
        """设置下次轮询时间"""
        with self._lock:
            self.next_poll_time = next_time

    def set_next_poll_time_for(
        self, keyword: str, next_time: Optional[datetime]
    ) -> None:
        """设置指定关键词的下次轮询时间，并同步全局最早时间"""
        with self._lock:
            if keyword:
                self._next_poll_times[keyword] = next_time
            next_times = [t for t in self._next_poll_times.values() if t is not None]
            self.next_poll_time = min(next_times) if next_times else None

    def record_article(
        self,
        article_id: str,
        title: str,
        publish_time: str,
        status: str,
        keyword: str = "",
    ) -> None:
        """
        记录单篇文章

        Args:
            article_id: 文章ID
            title: 文章标题
            publish_time: 发布时间
            status: 状态 ("success" | "failed")
        """
        now = datetime.now()
        with self._lock:
            self._check_daily_reset(now)

            record = ArticleRecord(
                keyword=keyword,
                article_id=article_id,
                title=title,
                publish_time=publish_time,
                crawl_time=now,
                status=status,
            )

            # 插入到列表开头
            self.recent_articles.insert(0, record)
            # 限制列表长度
            if len(self.recent_articles) > self._recent_limit:
                self.recent_articles = self.recent_articles[: self._recent_limit]

            # 更新今日统计
            self.today_total += 1
            if status == "success":
                self.today_success += 1
            else:
                self.today_failed += 1

    def record_poll(self, result: "CrawlResult", keyword: str = "") -> None:
        """
        记录一次轮询结果

        Args:
            result: 爬取结果
        """
        now = datetime.now()
        with self._lock:
            self._check_daily_reset(now)

            # 更新今日统计
            self.today_total += result.success_count + result.failed_count
            self.today_success += result.success_count
            self.today_failed += result.failed_count
            self.today_skipped += result.skipped_count

            # 更新累计统计
            self.total_polls += 1

            # 记录轮询历史
            poll_record = PollRecord(
                keyword=keyword,
                poll_time=now,
                new_count=result.success_count,
                success_count=result.success_count,
                failed_count=result.failed_count,
                skipped_count=result.skipped_count,
                elapsed_seconds=result.elapsed_time,
            )
            self.poll_history.insert(0, poll_record)
            if len(self.poll_history) > self._poll_history_limit:
                self.poll_history = self.poll_history[: self._poll_history_limit]

            # 记录新爬取的文章
            for article in result.new_articles:
                record = ArticleRecord(
                    keyword=keyword,
                    article_id=str(article.get("articleId", "")),
                    title=str(article.get("title", "")),
                    publish_time=str(article.get("publishTime", "")),
                    crawl_time=now,
                    status="success",
                )
                self.recent_articles.insert(0, record)

            # 限制最近文章列表长度
            if len(self.recent_articles) > self._recent_limit:
                self.recent_articles = self.recent_articles[: self._recent_limit]

    def clear_stats(self) -> None:
        """
        清除所有统计数据并重置运行时间

        Note:
            此方法会重置 _start_time，因此 get_uptime() 返回值也会重置为 0。
        """
        with self._lock:
            self.today_total = 0
            self.today_success = 0
            self.today_failed = 0
            self.today_skipped = 0
            self.total_polls = 0
            self.recent_articles.clear()
            self.poll_history.clear()
            self._start_time = datetime.now()

    def get_uptime(self) -> float:
        """获取运行时长（秒）"""
        return (datetime.now() - self._start_time).total_seconds()

    def get_recent_articles(self) -> List[ArticleRecord]:
        """
        获取最近文章列表的只读副本

        Returns:
            文章记录列表的浅拷贝
        """
        with self._lock:
            return list(self.recent_articles)

    def get_poll_history(self) -> List[PollRecord]:
        """
        获取轮询历史的只读副本

        Returns:
            轮询记录列表的浅拷贝
        """
        with self._lock:
            return list(self.poll_history)

    def get_snapshot(self) -> Dict[str, Any]:
        """
        获取状态快照（只读副本）

        Returns:
            包含所有状态信息的字典
        """
        with self._lock:
            self._check_daily_reset(datetime.now())
            return {
                "status": self.status,
                "last_error": self.last_error,
                "next_poll_time": self.next_poll_time,
                "today_total": self.today_total,
                "today_success": self.today_success,
                "today_failed": self.today_failed,
                "today_skipped": self.today_skipped,
                "total_polls": self.total_polls,
                "uptime_seconds": self.get_uptime(),
                "recent_articles": list(self.recent_articles),
                "poll_history": list(self.poll_history),
            }
