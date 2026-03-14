"""
调度器模块

封装 APScheduler BackgroundScheduler，负责：
- 定时增量爬取
- 状态更新与错误处理
- 重试控制
- 暂停/恢复/立即执行
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable, List, Optional, TypeVar, Union

from apscheduler.schedulers.background import BackgroundScheduler

from clients import OilChemCookiesManager
from config import get_settings
from convert import AsyncFormatConverter
from core import UniversalNamingSystem
from crawl.pipeline import CrawlResult, incremental_crawl
from monitor.state import MonitorState
from monitor.utils import ThreadSafeSet, TokenBucketRateLimiter, retry_with_backoff

T = TypeVar("T")


class CrawlScheduler:
    """
    增量爬取调度器

    基于 APScheduler BackgroundScheduler 实现定时轮询，
    支持暂停、恢复、立即执行等操作。

    Attributes:
        state: 监控状态管理器
        interval_minutes: 轮询间隔（分钟）
        keyword: 搜索关键词
    """

    def __init__(
        self,
        state: MonitorState,
        interval_minutes: Optional[int] = None,
        keyword: Optional[str] = None,
        cookies_manager: Optional[OilChemCookiesManager] = None,
        converter: Optional[AsyncFormatConverter] = None,
        existing_ids: Optional[Union[ThreadSafeSet, set]] = None,
        output_formats: Optional[List[str]] = None,
        max_pages: Optional[int] = None,
        early_stop_threshold: Optional[int] = None,
        validate_session_before_poll: Optional[bool] = None,
        max_retries: Optional[int] = None,
        retry_base_delay: Optional[float] = None,
        on_poll_complete: Optional[Callable[[CrawlResult], None]] = None,
        manage_state_pause: bool = True,
        request_gate: Optional[threading.Lock] = None,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
    ) -> None:
        """
        初始化调度器

        Args:
            state: 监控状态管理器
            interval_minutes: 轮询间隔，默认从配置读取
            keyword: 搜索关键词，默认从配置读取
            cookies_manager: Cookie 管理器（外部注入）
            converter: 格式转换器（外部注入）
            existing_ids: 已存在文章 ID 集合，默认从 CSV 加载
            output_formats: 输出格式列表
            max_pages: 每次轮询最大页数
            early_stop_threshold: 提前停止阈值
            validate_session_before_poll: 轮询前是否验证会话
            max_retries: 最大重试次数
            retry_base_delay: 重试基础延迟
            on_poll_complete: 轮询完成回调（可选）
        """
        settings = get_settings()
        monitor_cfg = settings.monitor

        self.state = state
        self._scheduler = BackgroundScheduler()
        self._job_id = "crawl_job"
        self._poll_lock = threading.Lock()
        self._poll_thread_id: Optional[int] = None  # 当前轮询线程ID
        self._paused = False
        self._running = False
        self._manage_state_pause = manage_state_pause
        self._request_gate = request_gate

        # 从配置加载默认值
        self.interval_minutes = interval_minutes or monitor_cfg.poll_interval_minutes
        self.keyword = keyword or monitor_cfg.default_keyword
        self.max_pages = max_pages or monitor_cfg.max_pages_per_poll
        self.early_stop_threshold = (
            early_stop_threshold
            if early_stop_threshold is not None
            else monitor_cfg.early_stop_threshold
        )
        self.output_formats = output_formats or settings.output.default_formats.copy()
        self.validate_session_before_poll = (
            validate_session_before_poll
            if validate_session_before_poll is not None
            else monitor_cfg.validate_session_before_poll
        )
        self.max_retries = (
            max_retries if max_retries is not None else monitor_cfg.max_retries
        )
        self.retry_base_delay = (
            retry_base_delay
            if retry_base_delay is not None
            else monitor_cfg.retry_base_delay
        )
        self._delay = settings.crawler.default_delay

        # M2: 初始化请求限流器
        self._rate_limiter = rate_limiter or TokenBucketRateLimiter(
            requests_per_minute=monitor_cfg.requests_per_minute,
            min_interval=monitor_cfg.min_request_interval,
        )

        # 外部注入的依赖
        self.cookies_manager = cookies_manager
        self.converter = converter
        self._on_poll_complete = on_poll_complete

        # 加载已存在的文章 ID（使用线程安全集合）
        if existing_ids is None:
            naming_system = UniversalNamingSystem(settings.crawler.project_code)
            self.existing_ids: ThreadSafeSet = ThreadSafeSet(
                naming_system.load_existing_article_ids()
            )
        elif isinstance(existing_ids, ThreadSafeSet):
            self.existing_ids = existing_ids
        else:
            # 将普通 set 转换为 ThreadSafeSet
            self.existing_ids = ThreadSafeSet(existing_ids)

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._running

    @property
    def is_paused(self) -> bool:
        """调度器是否已暂停"""
        return self._paused

    def start(self) -> None:
        """
        启动调度器

        立即执行第一次轮询，然后按间隔定时执行。
        """
        if self._running:
            print("⚠️ 调度器已在运行")
            return

        # 移除可能存在的旧任务
        if self._scheduler.get_job(self._job_id):
            self._scheduler.remove_job(self._job_id)

        # 添加定时任务
        self._scheduler.add_job(
            self._poll_job,
            trigger="interval",
            minutes=self.interval_minutes,
            id=self._job_id,
            max_instances=1,  # 防止任务重叠
            coalesce=True,  # 合并错过的任务
            misfire_grace_time=60,  # 错过执行的宽限时间
            next_run_time=datetime.now(),  # 立即执行第一次
        )

        self._scheduler.start()
        self._running = True
        self._paused = False
        self._sync_next_poll_time()

        print(f"🚀 调度器已启动，每 {self.interval_minutes} 分钟轮询一次")

        if self._manage_state_pause:
            self.state.set_status("idle")

    def stop(self, wait_for_job: bool = False, timeout: float = 60.0) -> None:
        """
        停止调度器

        Args:
            wait_for_job: 是否等待当前轮询完成
            timeout: 等待超时时间（秒）
        """
        if not self._running:
            return

        # 如果需要等待当前轮询
        if wait_for_job and self._poll_lock.locked():
            print("⏳ 等待当前轮询完成...")
            self._wait_for_current_poll(timeout)

        try:
            self._scheduler.shutdown(wait=False)
        except Exception as e:
            print(f"⚠️ 停止调度器时发生错误: {e}")

        self._running = False
        self._paused = False
        self._sync_next_poll_time()

        print("🛑 调度器已停止")

        if self._manage_state_pause:
            self.state.set_status("idle")

    def _wait_for_current_poll(self, timeout: float = 60.0) -> None:
        """
        等待当前轮询完成

        Args:
            timeout: 超时时间（秒）
        """
        # 避免在同一线程中等待自己
        current_thread = threading.get_ident()
        if self._poll_thread_id == current_thread:
            return

        start_time = time.time()
        while self._poll_lock.locked():
            if time.time() - start_time > timeout:
                print(f"⚠️ 等待轮询超时（{timeout}秒），强制停止")
                break
            time.sleep(0.5)

    def pause(self) -> None:
        """暂停调度任务"""
        if not self._running or self._paused:
            return

        job = self._scheduler.get_job(self._job_id)
        if job:
            job.pause()

        self._paused = True
        self._sync_next_poll_time()

        print("⏸️ 调度器已暂停")

        if self._manage_state_pause:
            self.state.set_paused(True)

    def resume(self) -> None:
        """恢复调度任务"""
        if not self._running or not self._paused:
            return

        job = self._scheduler.get_job(self._job_id)
        if job:
            job.resume()

        self._paused = False
        self._sync_next_poll_time()

        print("▶️ 调度器已恢复")

        if self._manage_state_pause:
            self.state.set_paused(False)

    def run_now(self) -> None:
        """
        立即执行一次轮询（在后台线程中）

        不影响正常的定时调度。
        """
        if self.state.status == "running":
            print("⚠️ 已有任务在执行中")
            return

        thread = threading.Thread(target=self._poll_job, daemon=True)
        thread.start()
        print("🔄 已触发立即执行")

    def get_next_run_time(self) -> Optional[datetime]:
        """获取下次执行时间"""
        if not self._running:
            return None

        job = self._scheduler.get_job(self._job_id)
        return job.next_run_time if job else None

    def _sync_next_poll_time(self) -> None:
        """同步下次轮询时间到状态管理器"""
        next_time = self.get_next_run_time()
        if hasattr(self.state, "set_next_poll_time_for"):
            self.state.set_next_poll_time_for(self.keyword, next_time)
        else:
            self.state.set_next_poll_time(next_time)

    def _poll_job(self) -> None:
        """
        轮询任务入口

        执行增量爬取，更新状态，处理错误。
        """
        # 尝试获取锁，防止重叠执行
        if not self._poll_lock.acquire(blocking=False):
            print("⚠️ 上一轮任务仍在执行，跳过本轮")
            return

        # 记录当前轮询线程ID（用于避免自等待死锁）
        self._poll_thread_id = threading.get_ident()

        had_error = False
        try:
            self.state.begin_poll()
            print(f"\n{'='*50}")
            print(f"🔍 开始轮询 ({datetime.now().strftime('%H:%M:%S')})")
            print(f"{'='*50}")

            # 验证 Cookie 会话
            if self.validate_session_before_poll and self.cookies_manager:
                if not self._run_with_request_gate(self._validate_session):
                    had_error = True
                    return

            # 执行增量爬取
            result = self._run_incremental_with_retry()

            # 记录轮询结果
            self.state.record_poll(result, keyword=self.keyword)

            # 回调通知
            if self._on_poll_complete:
                try:
                    self._on_poll_complete(result)
                except Exception as e:
                    print(f"⚠️ 轮询完成回调异常: {e}")

            # 打印摘要
            self._print_poll_summary(result)

        except Exception as exc:
            had_error = True
            error_msg = f"轮询异常: {exc}"
            self.state.set_error(error_msg)
            print(f"❌ {error_msg}")

        finally:
            self.state.end_poll(had_error)
            self._sync_next_poll_time()
            self._poll_thread_id = None  # 清除线程ID
            self._poll_lock.release()

    def _validate_session(self) -> bool:
        """验证 Cookie 会话是否有效"""
        print("🔐 验证 Cookie 会话...")

        if not self.cookies_manager:
            print("⚠️ 未配置 Cookie 管理器")
            return True  # 无管理器时跳过验证

        try:
            if self.cookies_manager.validate_session():
                print("✅ Cookie 会话有效")
                return True
            else:
                self.state.set_error("Cookie 已失效，请重新导入")
                print("❌ Cookie 已失效，请重新导入")
                return False
        except Exception as e:
            self.state.set_error(f"会话验证异常: {e}")
            print(f"❌ 会话验证异常: {e}")
            return False

    def _run_with_request_gate(self, func: Callable[[], T]) -> T:
        """在共享请求闸门下执行会话相关操作。"""
        if self._request_gate is None:
            return func()

        with self._request_gate:
            return func()

    def _run_incremental_with_retry(self) -> CrawlResult:
        """执行增量爬取（带重试）"""
        # M1: 校验 converter 是否已配置
        if self.converter is None:
            raise ValueError(
                "格式转换器 (converter) 未配置，无法执行增量爬取。"
                "请在初始化 CrawlScheduler 时传入有效的 AsyncFormatConverter 实例。"
            )

        def _run_once() -> CrawlResult:
            # M2: 在执行爬取前获取令牌，确保请求速率受控
            self._rate_limiter.acquire(blocking=True)
            return self._run_with_request_gate(
                lambda: incremental_crawl(
                    keyword=self.keyword,
                    existing_ids=self.existing_ids,
                    cookies_manager=self.cookies_manager,
                    converter=self.converter,
                    output_formats=self.output_formats,
                    max_pages=self.max_pages,
                    early_stop_threshold=self.early_stop_threshold,
                    delay=self._delay,
                )
            )

        # 无重试时直接执行
        if self.max_retries <= 0:
            return _run_once()

        # 使用重试装饰器
        wrapped = retry_with_backoff(
            max_retries=self.max_retries,
            base_delay=self.retry_base_delay,
        )(_run_once)

        return wrapped()

    @staticmethod
    def _print_poll_summary(result: CrawlResult) -> None:
        """打印轮询摘要"""
        print("\n📊 轮询完成:")
        print(f"   新增文章: {result.success_count}")
        print(f"   跳过已有: {result.skipped_count}")
        print(f"   失败数量: {result.failed_count}")
        print(f"   耗时: {result.elapsed_time:.2f}秒")


class MultiCrawlScheduler:
    """多关键词调度器封装"""

    def __init__(self, schedulers: List[CrawlScheduler], state: MonitorState) -> None:
        self._schedulers = schedulers
        self._state = state
        self._paused = False

    @property
    def keywords(self) -> List[str]:
        return [scheduler.keyword for scheduler in self._schedulers]

    @property
    def is_running(self) -> bool:
        return any(scheduler.is_running for scheduler in self._schedulers)

    @property
    def is_paused(self) -> bool:
        return self._paused

    def start(self) -> None:
        for scheduler in self._schedulers:
            scheduler.start()
        self._paused = False
        self._state.set_paused(False)

    def stop(self, wait_for_job: bool = False, timeout: float = 60.0) -> None:
        for scheduler in self._schedulers:
            scheduler.stop(wait_for_job=wait_for_job, timeout=timeout)
        self._paused = False
        self._state.set_paused(False)

    def pause(self) -> None:
        for scheduler in self._schedulers:
            scheduler.pause()
        self._paused = True
        self._state.set_paused(True)

    def resume(self) -> None:
        for scheduler in self._schedulers:
            scheduler.resume()
        self._paused = False
        self._state.set_paused(False)

    def run_now(self) -> None:
        for scheduler in self._schedulers:
            scheduler.run_now()
