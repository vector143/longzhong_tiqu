"""
具体监控适配器实现
"""

import sys
import time
from datetime import datetime
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
        self._state.extra["channels"] = channels
        self._state.extra["interval"] = interval
        self._state.extra["interval_unit"] = "seconds"
        self._state.extra["important_only"] = important_only
        self._state.extra["output_dir"] = self.output_dir
        self._state.extra["channel_stats"] = {}

    def _on_new_items(self, channel_name: str, items: list):
        """处理新快讯"""
        if items:
            self._state.items_count += len(items)
            self._state.total_items += len(items)
            self._state.last_run = datetime.now()
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

    def _run(self):
        """运行监控"""
        import threading
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
            while not self.should_stop():
                try:
                    if not self.wait_if_paused():
                        break
                    if not first_run:
                        if not self.wait_interval(self.interval):
                            break
                    first_run = False

                    new_items = crawler.fetch_incremental(
                        last_id=monitor.last_id,
                        channel=channel,
                        important_only=self.important_only,
                    )

                    if new_items:
                        callback(new_items)
                        ids = [item["id"] for item in new_items if item.get("id")]
                        if ids:
                            monitor.last_id = max(ids)

                    # 成功后恢复状态
                    if self._state.status == MonitorStatus.ERROR:
                        self._state.status = MonitorStatus.RUNNING

                except Exception as e:
                    self._state.status = MonitorStatus.ERROR
                    self._state.last_error = f"{channel}: {e}"
                    if not self.wait_interval(5):
                        break

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
    ):
        super().__init__(name="Investing.com")
        self.channels = channels
        self.interval = interval
        self.proxy = proxy
        self.output_dir = output_dir
        self.delay = delay
        self.max_pages = max_pages
        self._monitor = InvestingMonitor(output_dir=output_dir, proxy=proxy)
        self._state.extra["channels"] = channels
        self._state.extra["interval"] = interval
        self._state.extra["interval_unit"] = "seconds"
        self._state.extra["proxy"] = proxy
        self._state.extra["output_dir"] = output_dir
        self._state.extra["delay"] = delay
        self._state.extra["max_pages"] = max_pages

    def _run(self):
        """运行监控"""
        round_num = 1

        while not self.should_stop():
            try:
                if not self.wait_if_paused():
                    break
                self._state.last_run = datetime.now()
                stats = self._monitor.crawl_incremental(
                    channels=self.channels,
                    delay=self.delay,
                    max_pages=self.max_pages,
                )

                total_new = sum(stats.values())
                self._state.items_count = total_new
                self._state.total_items += total_new
                self._state.extra["round"] = round_num
                self._state.extra["stats"] = stats
                self._state.extra["recent_items"] = [
                    {
                        "time": self._state.last_run.strftime("%H:%M:%S"),
                        "title": f"{channel}: {count}",
                    }
                    for channel, count in stats.items()
                    if count > 0
                ][:5]

                # 成功后恢复状态
                if self._state.status == MonitorStatus.ERROR:
                    self._state.status = MonitorStatus.RUNNING

                round_num += 1

                # 等待下一轮，支持中断
                if not self.wait_interval(self.interval):
                    break

            except Exception as e:
                self._state.status = MonitorStatus.ERROR
                self._state.last_error = f"Investing: {e}"
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
        self._state.extra["keywords"] = keywords
        self._state.extra["interval"] = interval
        self._state.extra["interval_unit"] = "minutes"
        self._state.extra["runtime_mode"] = "embedded"

    def _runtime_controller(self):
        """获取嵌入式 runtime 的调度控制器。"""
        if self._runtime is None:
            return None
        return getattr(self._runtime, "controller", None)

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
