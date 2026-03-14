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

    def _on_new_items(self, channel_name: str, items: list):
        """处理新快讯"""
        if items:
            self._state.items_count += len(items)
            self._state.total_items += len(items)
            self._state.last_run = datetime.now()
            self._state.extra["last_channel"] = channel_name
            self._state.extra["last_items"] = [
                {
                    "title": item.get("title", "")[:50],
                    "time": item.get("display_time_str", ""),
                }
                for item in items[:5]
            ]

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
                    if not first_run:
                        time.sleep(self.interval)
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
                    time.sleep(5)

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
    ):
        super().__init__(name="Investing.com")
        self.channels = channels
        self.interval = interval
        self.proxy = proxy
        self.output_dir = output_dir
        self._monitor = InvestingMonitor(output_dir=output_dir, proxy=proxy)
        self._state.extra["channels"] = channels
        self._state.extra["interval"] = interval
        self._state.extra["proxy"] = proxy

    def _run(self):
        """运行监控"""
        round_num = 1

        while not self.should_stop():
            try:
                self._state.last_run = datetime.now()
                stats = self._monitor.crawl_incremental(
                    channels=self.channels, delay=3.0, max_pages=3
                )

                total_new = sum(stats.values())
                self._state.items_count = total_new
                self._state.total_items += total_new
                self._state.extra["round"] = round_num
                self._state.extra["stats"] = stats

                # 成功后恢复状态
                if self._state.status == MonitorStatus.ERROR:
                    self._state.status = MonitorStatus.RUNNING

                round_num += 1

                # 等待下一轮，支持中断
                for _ in range(self.interval):
                    if self.should_stop():
                        break
                    time.sleep(1)

            except Exception as e:
                self._state.status = MonitorStatus.ERROR
                self._state.last_error = f"Investing: {e}"
                # 失败后等待10秒再重试
                for _ in range(10):
                    if self.should_stop():
                        break
                    time.sleep(1)


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
        self._state.extra["keywords"] = keywords
        self._state.extra["interval"] = interval

    def _run(self):
        """运行监控 - 使用简化的调度逻辑"""
        try:
            from clients import OilChemCookiesManager
            from config import get_settings
            from crawl.pipeline import extract_from_keyword_async_multithread

            settings = get_settings()

            # Cookie 管理器
            cookies_manager = OilChemCookiesManager(settings.crawler.cookies_file)
            if not cookies_manager.load_cookies():
                self._state.status = MonitorStatus.ERROR
                self._state.last_error = "Cookie 加载失败"
                return

            # 如果不跳过历史，先执行历史爬取
            if not self.no_history:
                for keyword in self.keywords:
                    if self.should_stop():
                        break

                    self._state.last_run = datetime.now()
                    self._state.extra["current_keyword"] = keyword

                    extract_from_keyword_async_multithread(
                        keyword=keyword,
                        pages_to_crawl=3,
                        days_back=30,
                        output_formats=settings.output.default_formats.copy(),
                        qiniu_config=(
                            settings.get_qiniu_config()
                            if settings.output.upload_to_qiniu
                            else None
                        ),
                        save_locally=settings.output.save_locally,
                        upload_to_qiniu=settings.output.upload_to_qiniu,
                        max_crawl_workers=settings.crawler.max_crawl_workers,
                        max_upload_workers=settings.crawler.max_upload_workers,
                    )

            # 持续监控模式
            round_num = 1
            while not self.should_stop():
                try:
                    self._state.last_run = datetime.now()
                    self._state.extra["round"] = round_num

                    for keyword in self.keywords:
                        if self.should_stop():
                            break

                        self._state.extra["current_keyword"] = keyword

                        # 执行增量爬取
                        extract_from_keyword_async_multithread(
                            keyword=keyword,
                            pages_to_crawl=3,
                            days_back=None,
                            hours_back=None,
                            output_formats=settings.output.default_formats.copy(),
                            qiniu_config=(
                                settings.get_qiniu_config()
                                if settings.output.upload_to_qiniu
                                else None
                            ),
                            save_locally=settings.output.save_locally,
                            upload_to_qiniu=settings.output.upload_to_qiniu,
                            max_crawl_workers=settings.crawler.max_crawl_workers,
                            max_upload_workers=settings.crawler.max_upload_workers,
                        )

                        self._state.items_count += 1  # 简化计数
                        self._state.total_items += 1

                    # 成功后恢复状态
                    if self._state.status == MonitorStatus.ERROR:
                        self._state.status = MonitorStatus.RUNNING

                    round_num += 1

                    # 等待下一轮（分钟转秒）
                    wait_seconds = self.interval * 60
                    for _ in range(wait_seconds):
                        if self.should_stop():
                            break
                        time.sleep(1)

                except Exception as e:
                    self._state.status = MonitorStatus.ERROR
                    self._state.last_error = f"隆众: {e}"
                    # 失败后等待1分钟再重试
                    for _ in range(60):
                        if self.should_stop():
                            break
                        time.sleep(1)

        except Exception as e:
            self._state.status = MonitorStatus.ERROR
            self._state.last_error = f"初始化失败: {e}"
