"""
具体监控适配器实现
"""

import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.adapter import MonitorAdapter, MonitorStatus
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor
from crawl.investing_monitor import InvestingMonitor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WSJ_OUTPUT_DIR = PROJECT_ROOT / "output" / "report" / "cleaned"


class WallStreetCNAdapter(MonitorAdapter):
    """华尔街见闻监控适配器"""

    def __init__(
        self,
        channels: List[str],
        interval: int = 30,
        important_only: bool = False,
        output_dir: Optional[str] = None,
    ):
        super().__init__(name="华尔街见闻")
        self.channels = channels
        self.interval = interval
        self.important_only = important_only
        self.output_dir = str(output_dir or DEFAULT_WSJ_OUTPUT_DIR)
        self._monitors = []
        self._state_lock = threading.Lock()
        self._run_now_generation = 0
        self._channel_states = {
            channel: self._build_channel_state() for channel in channels
        }
        self._configure_runtime_metadata(
            mode="multi-thread",
            worker_count=len(channels),
        )
        self._state.extra["channels"] = channels
        self._state.extra["interval"] = interval
        self._state.extra["interval_unit"] = "seconds"
        self._state.extra["important_only"] = important_only
        self._state.extra["output_dir"] = self.output_dir
        self._state.extra["channel_stats"] = {}
        self._state.extra["channel_statuses"] = {
            channel: "idle" for channel in channels
        }
        self._state.extra["failed_channels"] = []
        self._state.extra["consecutive_failures"] = 0
        self._state.extra["backoff_seconds"] = 0

    @staticmethod
    def _build_channel_state() -> dict:
        return {
            "status": "idle",
            "next_run_at": None,
            "last_success_at": None,
            "last_poll_started_at": None,
            "last_poll_finished_at": None,
            "last_round_duration_seconds": 0.0,
            "last_round_new": 0,
            "consecutive_failures": 0,
            "backoff_seconds": 0,
            "last_error": None,
        }

    def _before_start(self) -> None:
        with self._state_lock:
            self._monitors = []
            self._run_now_generation = 0
            self._channel_states = {
                channel: self._build_channel_state() for channel in self.channels
            }
            self._state.items_count = 0
            self._state.last_error = None
            self._state.extra["failed_channels"] = []
            self._state.extra["consecutive_failures"] = 0
            self._state.extra["backoff_seconds"] = 0
            self._state.extra["next_run_at"] = None
            self._state.extra["last_success_at"] = None
            self._state.extra["last_poll_started_at"] = None
            self._state.extra["last_poll_finished_at"] = None
            self._state.extra["last_round_duration_seconds"] = 0.0
            self._state.extra["last_round_new"] = 0
            self._state.extra["channel_statuses"] = {
                channel: "idle" for channel in self.channels
            }
            self._state.extra["recent_items"] = []
            self._state.extra["last_items"] = []

    def _after_stop(self) -> None:
        with self._state_lock:
            for channel_state in self._channel_states.values():
                channel_state["status"] = "stopped"
                channel_state["next_run_at"] = None
            self._sync_channel_aggregate_state()

    def _sync_runtime_metadata(self) -> None:
        with self._state_lock:
            active_workers = sum(
                1
                for data in self._channel_states.values()
                if data.get("status") not in {"idle", "stopped"}
            )
            if self.is_running() and active_workers == 0:
                active_workers = len(self.channels)
            self._state.extra["runtime_active_workers"] = active_workers

    def _consume_run_now_broadcast(self, last_seen_generation: int) -> Optional[int]:
        """返回尚未消费的 run-now 广播代次。"""
        with self._state_lock:
            if self._run_now_generation > last_seen_generation:
                return self._run_now_generation
        return None

    def _sync_channel_aggregate_state(self) -> None:
        """将各频道轮询状态聚合到统一控制台状态。"""
        channel_statuses = {
            channel: data.get("status", "idle")
            for channel, data in self._channel_states.items()
        }
        failed_channels = sorted(
            channel
            for channel, data in self._channel_states.items()
            if data.get("status") == "error"
        )
        next_run_times = [
            data.get("next_run_at")
            for data in self._channel_states.values()
            if data.get("next_run_at") is not None
        ]
        last_success_times = [
            data.get("last_success_at")
            for data in self._channel_states.values()
            if data.get("last_success_at") is not None
        ]
        last_started_times = [
            data.get("last_poll_started_at")
            for data in self._channel_states.values()
            if data.get("last_poll_started_at") is not None
        ]
        last_finished_times = [
            data.get("last_poll_finished_at")
            for data in self._channel_states.values()
            if data.get("last_poll_finished_at") is not None
        ]

        self._state.extra["channel_statuses"] = channel_statuses
        self._state.extra["failed_channels"] = failed_channels
        self._state.extra["next_run_at"] = (
            min(next_run_times) if next_run_times else None
        )
        self._state.extra["last_success_at"] = (
            max(last_success_times) if last_success_times else None
        )
        self._state.extra["last_poll_started_at"] = (
            max(last_started_times) if last_started_times else None
        )
        self._state.extra["last_poll_finished_at"] = (
            max(last_finished_times) if last_finished_times else None
        )
        self._state.extra["consecutive_failures"] = max(
            (
                int(data.get("consecutive_failures", 0))
                for data in self._channel_states.values()
            ),
            default=0,
        )
        self._state.extra["backoff_seconds"] = max(
            (
                int(data.get("backoff_seconds", 0))
                for data in self._channel_states.values()
            ),
            default=0,
        )

        if failed_channels:
            self._state.status = MonitorStatus.ERROR
        elif self.is_paused():
            self._state.status = MonitorStatus.PAUSED
        elif self.is_running() or any(
            status == "running" for status in channel_statuses.values()
        ):
            self._state.status = MonitorStatus.RUNNING

        if not failed_channels and self._state.last_error:
            self._state.last_error = None

    def _record_channel_poll_result(
        self,
        channel: str,
        started_at: datetime,
        finished_at: datetime,
        new_count: int,
        next_run_at: Optional[datetime],
        error: Optional[Exception] = None,
    ) -> None:
        """记录单频道轮询结果并刷新聚合状态。"""
        duration = max((finished_at - started_at).total_seconds(), 0.0)
        with self._state_lock:
            channel_state = self._channel_states.setdefault(
                channel,
                self._build_channel_state(),
            )
            channel_state["last_poll_started_at"] = started_at
            channel_state["last_poll_finished_at"] = finished_at
            channel_state["last_round_duration_seconds"] = duration
            channel_state["last_round_new"] = new_count
            channel_state["next_run_at"] = next_run_at

            self._state.last_run = finished_at
            self._state.items_count = new_count
            self._state.extra["last_channel"] = channel
            self._state.extra["last_round_new"] = new_count
            self._state.extra["last_round_duration_seconds"] = duration

            if error is None:
                channel_state["status"] = "running"
                channel_state["last_success_at"] = finished_at
                channel_state["consecutive_failures"] = 0
                channel_state["backoff_seconds"] = 0
                channel_state["last_error"] = None
            else:
                channel_state["status"] = "error"
                channel_state["consecutive_failures"] = (
                    int(channel_state.get("consecutive_failures", 0)) + 1
                )
                channel_state["backoff_seconds"] = max(
                    (
                        int((next_run_at - finished_at).total_seconds())
                        if next_run_at is not None
                        else 0
                    ),
                    0,
                )
                channel_state["last_error"] = str(error)
                self._state.last_error = f"{channel}: {error}"

            self._sync_channel_aggregate_state()

    def _on_new_items(self, channel_name: str, items: list):
        """处理新快讯"""
        if items:
            self._state.total_items += len(items)
            self._state.extra["last_channel"] = channel_name
            channel_stats = self._state.extra.setdefault("channel_stats", {})
            channel_stats[channel_name] = channel_stats.get(channel_name, 0) + len(
                items
            )
            recent_items = [
                {
                    "title": item.get("title", "")[:50],
                    "time": item.get("display_time_str", ""),
                }
                for item in items[:5]
            ]
            self._state.extra["last_items"] = recent_items
            self._state.extra["recent_items"] = recent_items

    def _wait_for_channel_interval(
        self,
        seconds: int,
        last_seen_generation: int,
        poll_interval: float = 0.2,
    ) -> tuple[bool, int]:
        """等待频道下一轮轮询，同时支持源级 run-now 广播。"""
        deadline = time.time() + max(seconds, 0)
        while not self.should_stop():
            if not self.wait_if_paused(poll_interval=poll_interval):
                return False, last_seen_generation

            generation = self._consume_run_now_broadcast(last_seen_generation)
            if generation is not None:
                return True, generation

            remaining = deadline - time.time()
            if remaining <= 0:
                return True, last_seen_generation
            time.sleep(min(poll_interval, remaining))

        return False, last_seen_generation

    def pause(self):
        """暂停并同步源级聚合状态。"""
        super().pause()
        with self._state_lock:
            self._sync_channel_aggregate_state()

    def resume(self):
        """恢复并同步源级聚合状态。"""
        super().resume()
        with self._state_lock:
            self._sync_channel_aggregate_state()

    def run_now(self):
        """广播一次源级立即执行信号。"""
        with self._state_lock:
            self._run_now_generation += 1
            self._state.extra["next_run_at"] = datetime.now()

    def _run(self):
        """运行监控"""
        from crawl.multi_commodity_monitor import save_to_json

        def monitor_channel(channel):
            """监控单个频道"""
            crawler = WallStreetCNLiveCrawler()
            monitor = WallStreetCNMonitor(
                crawler=crawler,
                poll_interval=self.interval,
                channel=channel,
                important_only=self.important_only,
            )

            def callback(items):
                self._on_new_items(channel, items)
                if items:
                    save_to_json(items, self.output_dir)

            self._monitors.append(monitor)

            # 初始化，获取基线
            try:
                initial_items = crawler.fetch_incremental(
                    channel=channel,
                    limit=10,
                    important_only=self.important_only,
                )

                if initial_items:
                    # 安全获取最大ID
                    ids = [item["id"] for item in initial_items if item.get("id")]
                    if ids:
                        monitor.last_id = max(ids)
                        # 首次也触发回调，让用户看到初始数据
                        callback(initial_items)
            except Exception as e:
                self._state.status = MonitorStatus.ERROR
                self._state.last_error = f"初始化失败: {e}"
                return

            # 轮询循环 - 首次不延迟
            first_run = True
            last_seen_generation = 0
            while not self.should_stop():
                started_at = None
                try:
                    if first_run:
                        if not self.wait_if_paused():
                            break
                    else:
                        should_run, last_seen_generation = (
                            self._wait_for_channel_interval(
                                self.interval,
                                last_seen_generation,
                            )
                        )
                        if not should_run:
                            break
                    first_run = False

                    started_at = datetime.now()
                    new_items = monitor._fetch_new_items_for_poll()

                    if new_items:
                        callback(new_items)
                        ids = [item["id"] for item in new_items if item.get("id")]
                        if ids:
                            monitor.last_id = max(ids)

                    finished_at = datetime.now()
                    self._record_channel_poll_result(
                        channel=channel,
                        started_at=started_at,
                        finished_at=finished_at,
                        new_count=len(new_items),
                        next_run_at=finished_at + timedelta(seconds=self.interval),
                    )

                except Exception as e:
                    finished_at = datetime.now()
                    self._record_channel_poll_result(
                        channel=channel,
                        started_at=started_at or finished_at,
                        finished_at=finished_at,
                        new_count=0,
                        next_run_at=finished_at + timedelta(seconds=5),
                        error=e,
                    )
                    should_retry, last_seen_generation = (
                        self._wait_for_channel_interval(
                            5,
                            last_seen_generation,
                        )
                    )
                    if not should_retry:
                        break
                    first_run = True

        # 为每个频道创建线程
        threads = []
        for channel in self.channels:
            t = threading.Thread(target=monitor_channel, args=(channel,), daemon=True)
            t.start()
            threads.append(t)
            time.sleep(1)

        # 等待停止信号
        while not self.should_stop():
            time.sleep(1)

        # 等待所有线程结束
        for t in threads:
            t.join(timeout=5)


class InvestingAdapter(MonitorAdapter):
    """Investing.com 监控适配器"""

    def __init__(
        self,
        channels: List[str],
        interval: int = 300,
        proxy: str = None,
        output_dir: str = None,
        delay: float = 3.0,
        max_pages: int = 3,
        workers: int = 3,
        adaptive_interval: bool = False,
        max_interval: int = 180,
    ):
        super().__init__(name="Investing.com")
        self.channels = channels
        self.interval = interval
        self.proxy = proxy
        self.output_dir = output_dir
        self.delay = delay
        self.max_pages = max_pages
        self.workers = workers
        self.adaptive_interval = adaptive_interval
        self.max_interval = max(max_interval, interval)
        self._monitor = InvestingMonitor(
            output_dir=output_dir,
            proxy=proxy,
            max_workers=workers,
            rate_limit=delay,
        )
        self._state.extra["channels"] = channels
        self._state.extra["interval"] = interval
        self._state.extra["interval_unit"] = "seconds"
        self._state.extra["proxy"] = proxy
        self._state.extra["output_dir"] = output_dir
        self._state.extra["delay"] = delay
        self._state.extra["max_pages"] = max_pages
        self._state.extra["workers"] = workers
        self._state.extra["adaptive_interval"] = adaptive_interval
        self._state.extra["adaptive_max_interval"] = self.max_interval
        self._state.extra["max_interval"] = self.max_interval
        self._state.extra["adaptive_idle_rounds"] = 0
        self._state.extra["adaptive_next_interval"] = interval
        self._state.extra["channel_stats"] = {}
        self._state.extra["active_channels"] = []
        self._state.extra["consecutive_failures"] = 0
        self._state.extra["backoff_seconds"] = 0
        self._configure_runtime_metadata(
            mode="single-loop",
            worker_count=1,
        )

    def _before_start(self) -> None:
        self._state.items_count = 0
        self._state.last_error = None
        self._state.extra["next_run_at"] = None
        self._state.extra["last_success_at"] = None
        self._state.extra["last_poll_started_at"] = None
        self._state.extra["last_poll_finished_at"] = None
        self._state.extra["last_round_duration_seconds"] = 0.0
        self._state.extra["last_round_new"] = 0
        self._state.extra["channel_stats"] = {}
        self._state.extra["stats"] = {}
        self._state.extra["active_channels"] = []
        self._state.extra["consecutive_failures"] = 0
        self._state.extra["backoff_seconds"] = 0
        self._state.extra["recent_items"] = []
        self._state.extra["adaptive_idle_rounds"] = 0
        self._state.extra["adaptive_next_interval"] = self.interval

    def _sync_runtime_metadata(self) -> None:
        self._state.extra["runtime_active_workers"] = 1 if self.is_running() else 0

    def _compute_next_wait_seconds(self, total_new: int) -> int:
        if not self.adaptive_interval:
            self._state.extra["adaptive_idle_rounds"] = 0
            self._state.extra["adaptive_next_interval"] = self.interval
            return self.interval

        idle_rounds = int(self._state.extra.get("adaptive_idle_rounds", 0))
        if total_new > 0:
            idle_rounds = 0
            next_interval = self.interval
        else:
            idle_rounds += 1
            next_interval = min(
                self.max_interval,
                max(self.interval, self.interval * (2**idle_rounds)),
            )

        self._state.extra["adaptive_idle_rounds"] = idle_rounds
        self._state.extra["adaptive_next_interval"] = int(next_interval)
        return int(next_interval)

    def _record_poll_result(
        self,
        started_at: datetime,
        finished_at: datetime,
        round_num: int,
        stats: Optional[dict] = None,
        error: Optional[Exception] = None,
        backoff_seconds: int = 0,
        wait_seconds: Optional[int] = None,
    ) -> None:
        """记录 Investing 单轮轮询结果。"""
        if backoff_seconds > 0:
            next_wait_seconds = backoff_seconds
        elif wait_seconds is not None:
            next_wait_seconds = wait_seconds
        else:
            next_wait_seconds = self.interval

        duration = max((finished_at - started_at).total_seconds(), 0.0)
        self._state.last_run = finished_at
        self._state.extra["round"] = round_num
        self._state.extra["last_poll_started_at"] = started_at
        self._state.extra["last_poll_finished_at"] = finished_at
        self._state.extra["last_round_duration_seconds"] = duration
        self._state.extra["next_run_at"] = finished_at + timedelta(
            seconds=next_wait_seconds
        )
        self._state.extra["backoff_seconds"] = backoff_seconds

        if error is None:
            stats = dict(stats or {})
            total_new = sum(stats.values())
            self._state.items_count = total_new
            self._state.total_items += total_new
            self._state.extra["last_round_new"] = total_new
            self._state.extra["last_success_at"] = finished_at
            self._state.extra["stats"] = stats
            self._state.extra["channel_stats"] = stats
            self._state.extra["active_channels"] = [
                channel for channel, count in stats.items() if count > 0
            ]
            self._state.extra["recent_items"] = [
                {
                    "time": finished_at.strftime("%H:%M:%S"),
                    "title": f"{channel}: {count}",
                }
                for channel, count in stats.items()
                if count > 0
            ][:5]
            self._state.extra["consecutive_failures"] = 0
            self._state.last_error = None
            self._state.status = MonitorStatus.RUNNING
            return

        self._state.items_count = 0
        self._state.extra["last_round_new"] = 0
        self._state.extra["stats"] = {}
        self._state.extra["channel_stats"] = {}
        self._state.extra["active_channels"] = []
        self._state.extra["recent_items"] = []
        self._state.extra["adaptive_idle_rounds"] = 0
        self._state.extra["adaptive_next_interval"] = self.interval
        self._state.extra["consecutive_failures"] = (
            int(self._state.extra.get("consecutive_failures", 0)) + 1
        )
        self._state.last_error = f"Investing: {error}"
        self._state.status = MonitorStatus.ERROR

    def _run(self):
        """运行监控"""
        round_num = 1

        while not self.should_stop():
            started_at = None
            try:
                if not self.wait_if_paused():
                    break
                started_at = datetime.now()
                stats = self._monitor.crawl_incremental(
                    channels=self.channels,
                    delay=self.delay,
                    max_pages=self.max_pages,
                )
                finished_at = datetime.now()
                total_new = sum(dict(stats or {}).values())
                next_wait_seconds = self._compute_next_wait_seconds(total_new)
                self._record_poll_result(
                    started_at=started_at,
                    finished_at=finished_at,
                    round_num=round_num,
                    stats=stats,
                    wait_seconds=next_wait_seconds,
                )

                round_num += 1

                # 等待下一轮，支持中断
                if not self.wait_interval(next_wait_seconds):
                    break

            except Exception as e:
                finished_at = datetime.now()
                self._record_poll_result(
                    started_at=started_at or finished_at,
                    finished_at=finished_at,
                    round_num=round_num,
                    error=e,
                    backoff_seconds=10,
                )
                # 失败后等待10秒再重试
                if not self.wait_interval(10):
                    break


class LongZhongAdapter(MonitorAdapter):
    """隆众资讯监控适配器"""

    def __init__(
        self,
        keywords: List[str],
        interval: int = 30,
        no_history: bool = True,
    ):
        super().__init__(name="隆众资讯")
        self.keywords = keywords
        self.interval = interval
        self.no_history = no_history
        self._runtime = None
        self._configure_runtime_metadata(
            mode="embedded-runtime",
            worker_count=len(keywords),
            controller_ready=False,
        )
        self._state.extra["keywords"] = keywords
        self._state.extra["interval"] = interval
        self._state.extra["interval_unit"] = "minutes"
        self._state.extra["runtime_mode"] = "embedded"

    def _runtime_controller(self):
        """获取嵌入式 runtime 的调度控制器。"""
        if self._runtime is None:
            return None
        return getattr(self._runtime, "controller", None)

    def _sync_runtime_metadata(self) -> None:
        controller = self._runtime_controller()
        self._state.extra["runtime_controller_ready"] = controller is not None
        if self._runtime is None:
            self._state.extra["runtime_active_workers"] = 0
        else:
            self._state.extra["runtime_active_workers"] = len(self.keywords)

    def _sync_runtime_state(self) -> None:
        """将正式 runtime 的状态快照映射到统一控制台状态。"""
        if self._runtime is None or getattr(self._runtime, "state", None) is None:
            return

        snapshot = self._runtime.state.get_snapshot()
        status_map = {
            "idle": MonitorStatus.IDLE,
            "running": MonitorStatus.RUNNING,
            "paused": MonitorStatus.PAUSED,
            "error": MonitorStatus.ERROR,
        }
        self._state.status = status_map.get(snapshot.get("status"), self._state.status)
        self._state.last_error = snapshot.get("last_error")
        self._state.running_time = float(snapshot.get("uptime_seconds", 0.0))

        poll_history = snapshot.get("poll_history") or []
        recent_articles = snapshot.get("recent_articles") or []
        latest_poll = poll_history[0] if poll_history else None

        self._state.items_count = int(getattr(latest_poll, "new_count", 0))
        self._state.total_items = int(snapshot.get("today_success", 0))
        self._state.last_run = getattr(
            latest_poll,
            "poll_time",
            recent_articles[0].crawl_time if recent_articles else None,
        )

        self._state.extra["current_keyword"] = getattr(
            latest_poll,
            "keyword",
            recent_articles[0].keyword if recent_articles else None,
        )
        self._state.extra["next_poll_time"] = snapshot.get("next_poll_time")
        self._state.extra["total_polls"] = int(snapshot.get("total_polls", 0))
        self._state.extra["today_total"] = int(snapshot.get("today_total", 0))
        self._state.extra["today_success"] = int(snapshot.get("today_success", 0))
        self._state.extra["today_failed"] = int(snapshot.get("today_failed", 0))
        self._state.extra["today_skipped"] = int(snapshot.get("today_skipped", 0))
        self._state.extra["recent_items"] = [
            {
                "time": article.crawl_time.strftime("%H:%M:%S"),
                "title": article.title,
            }
            for article in recent_articles[:5]
        ]

    def pause(self):
        """优先委托正式 runtime 暂停。"""
        controller = self._runtime_controller()
        if controller is not None:
            controller.pause()
            self._sync_runtime_state()
            return
        super().pause()

    def resume(self):
        """优先委托正式 runtime 恢复。"""
        controller = self._runtime_controller()
        if controller is not None:
            controller.resume()
            self._sync_runtime_state()
            return
        super().resume()

    def run_now(self):
        """优先委托正式 runtime 立即运行。"""
        controller = self._runtime_controller()
        if controller is not None:
            controller.run_now()
            self._sync_runtime_state()
            return
        super().run_now()

    def get_state(self):
        """优先返回正式 runtime 的映射状态。"""
        if self._runtime is not None:
            self._sync_runtime_state()
            return self._state
        return super().get_state()

    def _run(self):
        """运行监控 - 复用正式 runner/scheduler/state 链路。"""
        try:
            from monitor.runner import (
                build_monitor_runtime,
                start_monitor_runtime,
                stop_monitor_runtime,
            )

            self._runtime = build_monitor_runtime(
                keywords=self.keywords,
                interval_minutes=self.interval,
                no_history=self.no_history,
                enable_pid=False,
                print_preflight=False,
            )
            start_monitor_runtime(self._runtime)

            while not self.should_stop():
                self._sync_runtime_state()
                if not self.wait_interval(1):
                    break

        except Exception as e:
            self._state.status = MonitorStatus.ERROR
            self._state.last_error = f"初始化失败: {e}"
        finally:
            if self._runtime is not None:
                try:
                    self._sync_runtime_state()
                    from monitor.runner import stop_monitor_runtime

                    stop_monitor_runtime(self._runtime, wait_for_job=True, timeout=60.0)
                finally:
                    self._runtime = None
