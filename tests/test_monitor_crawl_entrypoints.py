from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl.investing_monitor import InvestingMonitor
from crawl.wallstreetcn import WallStreetCNMonitor


def test_investing_list_item_quick_dedupe_matches_saved_article(monkeypatch, tmp_path):
    monkeypatch.setattr(InvestingMonitor, "_load_seen_digests", lambda self: set())

    monitor = InvestingMonitor(output_dir=str(tmp_path))

    list_item = {
        "id": "4559066",
        "title": "Take Five: Deja vu?",
        "url": "https://www.investing.com/news/economy-news/take-five-deja-vu-4559066",
        "summary": "War in the Middle East...",
        "publish_time": "2026-03-13 07:36:25",
        "author": "Reuters",
        "category": "economy",
    }
    saved_item = {
        **list_item,
        "content": "LONDON, March 13 (Reuters) - War in the Middle East continues.",
    }

    saved_digest = monitor.formatter.format_to_standard(saved_item)["content_digest"]
    monitor.seen_digests.add(saved_digest)

    quick_digest = monitor.formatter.format_to_standard(list_item)["content_digest"]

    assert monitor._is_duplicate(quick_digest) is True


def test_investing_fetch_articles_concurrent_uses_fresh_crawler_instances(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(InvestingMonitor, "_load_seen_digests", lambda self: set())

    monitor = InvestingMonitor(output_dir=str(tmp_path), max_workers=2)
    monkeypatch.setattr(monitor, "_save_article", lambda article, channel: True)

    created_crawlers: List["_WorkerCrawler"] = []

    class _WorkerCrawler:
        def __init__(self, channel: str, proxy: str | None = None) -> None:
            self.channel = channel
            self.proxy = proxy
            self.calls: List[str] = []
            created_crawlers.append(self)

        def fetch_article_content(self, article_url: str) -> Dict[str, Any]:
            self.calls.append(article_url)
            return {
                "success": True,
                "content": f"正文 {article_url}",
                "html_content": f"<p>{article_url}</p>",
                "publish_time": "2026-03-14 10:00:00",
                "author": "Reuters",
                "error": None,
            }

    class _OriginalCrawler:
        channel = "economy"

        def fetch_article_content(self, article_url: str) -> Dict[str, Any]:
            raise AssertionError(
                f"should not reuse shared crawler session: {article_url}"
            )

    monkeypatch.setattr(
        "crawl.investing_monitor.InvestingCommodityNewsCrawler", _WorkerCrawler
    )

    news_items = [
        {
            "id": "4559066",
            "title": "Take Five: Deja vu?",
            "url": "https://www.investing.com/news/economy-news/take-five-deja-vu-4559066",
            "summary": "War in the Middle East...",
            "publish_time": "2026-03-13 07:36:25",
            "author": "Reuters",
            "category": "economy",
        },
        {
            "id": "4559067",
            "title": "Commodities edge higher",
            "url": "https://www.investing.com/news/commodities-news/commodities-edge-higher-4559067",
            "summary": "Prices ticked up...",
            "publish_time": "2026-03-13 07:40:25",
            "author": "Reuters",
            "category": "commodities",
        },
    ]

    saved_articles = monitor._fetch_articles_concurrent(
        news_items,
        channel="economy",
        crawler=_OriginalCrawler(),
    )

    assert len(saved_articles) == 2
    assert len(created_crawlers) == 2
    assert all(len(worker.calls) == 1 for worker in created_crawlers)


class OverflowCrawler:
    def __init__(self) -> None:
        self.incremental_calls = 0

    def fetch_incremental(
        self,
        last_id: int | None = None,
        channel: str = "global-channel",
        limit: int = 20,
        important_only: bool = False,
        min_score: int = 1,
    ) -> List[Dict[str, Any]]:
        del channel, limit, important_only, min_score

        if last_id is None:
            return [self._item(item_id) for item_id in range(100, 90, -1)]

        self.incremental_calls += 1
        if self.incremental_calls == 1:
            return [self._item(item_id) for item_id in range(125, 105, -1)]
        if self.incremental_calls == 2:
            return [self._item(item_id) for item_id in range(105, 100, -1)]
        return []

    @staticmethod
    def _item(item_id: int) -> Dict[str, Any]:
        return {
            "id": item_id,
            "title": f"快讯 {item_id}",
            "content_text": f"内容 {item_id}",
            "display_time_str": f"2026-03-14 10:{item_id % 60:02d}:00",
            "url": f"https://wallstreetcn.com/live/{item_id}",
        }


def test_wallstreetcn_monitor_drains_all_new_items_from_single_poll(monkeypatch):
    crawler = OverflowCrawler()
    monitor = WallStreetCNMonitor(crawler=crawler, poll_interval=1)

    collected_ids: List[int] = []
    sleep_calls = {"count": 0}

    def fake_sleep(_seconds: int) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] > 1:
            raise KeyboardInterrupt

    def callback(items: List[Dict[str, Any]]) -> None:
        collected_ids.extend(item["id"] for item in items)

    monkeypatch.setattr("crawl.wallstreetcn.time.sleep", fake_sleep)

    monitor.start(callback=callback)

    assert collected_ids == list(range(125, 100, -1))
