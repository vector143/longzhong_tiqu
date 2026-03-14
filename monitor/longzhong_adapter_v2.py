"""
改进的隆众资讯监控适配器

不直接调用 run_monitor，而是复制其核心逻辑并支持状态更新
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.adapter import MonitorAdapter, MonitorStatus
from clients import OilChemCookiesManager
from config import get_settings
from crawl.pipeline import extract_from_keyword_async_multithread


class LongZhongAdapterV2(MonitorAdapter):
    """隆众资讯监控适配器 - 改进版"""

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
        self._scheduler = None

    def _run(self):
        """运行监控 - 使用简化的调度逻辑"""
        try:
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
