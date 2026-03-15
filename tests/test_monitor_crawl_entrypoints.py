from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl.investing_monitor import InvestingMonitor
from crawl.wallstreetcn import WallStreetCNLiveCrawler, WallStreetCNMonitor


def _build_wsj_item(item_id: int) -> Dict[str, Any]:
    return {
        "id": item_id,
        "title": f"快讯 {item_id}",
        "content_text": f"内容 {item_id}",
        "display_time_str": f"2026-03-14 10:{item_id % 60:02d}:00",
        "url": f"https://wallstreetcn.com/live/{item_id}",
    }


def test_investing_list_item_dedupe_uses_stable_identity_without_formatter(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(InvestingMonitor, "_load_seen_digests", lambda self: set())

    monitor = InvestingMonitor(output_dir=str(tmp_path), rate_limit=0)

    list_item = {
        "id": "4559066",
        "title": "Take Five: Deja vu?",
        "url": "https://www.investing.com/news/economy-news/take-five-deja-vu-4559066",
        "summary": "War in the Middle East...",
        "publish_time": "2026-03-13 07:36:25",
        "author": "Reuters",
        "category": "economy",
    }
    stable_digest = hashlib.sha1(
        f"{list_item['id']}|{list_item['url']}".encode("utf-8")
    ).hexdigest()
    monitor.seen_digests.add(stable_digest)

    class _FormatterGuard:
        def format_to_standard(self, _item):
            raise AssertionError("列表态判重不应依赖 formatter.format_to_standard")

    class _ListCrawler:
        def __init__(self, channel: str, proxy: str | None = None) -> None:
            self.channel = channel
            self.proxy = proxy

        def fetch_news_list(self, page: int, delay: float) -> Dict[str, Any]:
            del delay
            if page == 1:
                return {"success": True, "data": [dict(list_item)]}
            return {"success": True, "data": []}

    monitor.formatter = _FormatterGuard()
    monkeypatch.setattr(
        "crawl.investing_monitor.InvestingCommodityNewsCrawler", _ListCrawler
    )

    channel, count = monitor._crawl_channel_incremental(channel="economy", max_pages=1)

    assert channel == "economy"
    assert count == 0


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


def test_wallstreetcn_fetch_incremental_marks_incomplete_when_later_page_fails(
    monkeypatch,
):
    crawler = WallStreetCNLiveCrawler()
    responses = [
        {
            "success": True,
            "data": [_build_wsj_item(item_id) for item_id in range(120, 110, -1)],
            "next_cursor": "cursor-2",
            "error": None,
        },
        {
            "success": False,
            "data": [],
            "next_cursor": None,
            "error": "network timeout",
        },
    ]

    def fake_fetch_lives(**_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(crawler, "fetch_lives", fake_fetch_lives)

    result = crawler.fetch_incremental_with_meta(last_id=100, limit=10)

    assert result.complete is False
    assert [item["id"] for item in result.items] == list(range(120, 110, -1))


def test_wallstreetcn_monitor_does_not_advance_last_id_when_fetch_is_incomplete(
    monkeypatch,
):
    class _BaselineCrawler:
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
                return [_build_wsj_item(100)]
            return []

    crawler = _BaselineCrawler()
    monitor = WallStreetCNMonitor(crawler=crawler, poll_interval=1)
    collected_ids: List[int] = []
    sleep_calls = {"count": 0}
    poll_results = [([_build_wsj_item(105)], False)]

    def fake_sleep(_seconds: int) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] > 1:
            raise KeyboardInterrupt

    def fake_fetch_for_poll():
        if poll_results:
            return poll_results.pop(0)
        return [], True

    def callback(items: List[Dict[str, Any]]) -> None:
        collected_ids.extend(item["id"] for item in items)

    monkeypatch.setattr("crawl.wallstreetcn.time.sleep", fake_sleep)
    monkeypatch.setattr(monitor, "_fetch_new_items_for_poll", fake_fetch_for_poll)

    monitor.start(callback=callback)

    assert monitor.last_id == 100
    assert collected_ids == [105]


def test_wallstreetcn_monitor_does_not_emit_duplicate_items_before_watermark_commit(
    monkeypatch,
):
    class _BaselineCrawler:
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
                return [_build_wsj_item(100)]
            return []

    crawler = _BaselineCrawler()
    monitor = WallStreetCNMonitor(crawler=crawler, poll_interval=1)
    collected_ids: List[int] = []
    sleep_calls = {"count": 0}
    poll_results = [
        ([_build_wsj_item(105), _build_wsj_item(104)], False),
        ([_build_wsj_item(105), _build_wsj_item(104), _build_wsj_item(103)], True),
    ]

    def fake_sleep(_seconds: int) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] > 2:
            raise KeyboardInterrupt

    def fake_fetch_for_poll():
        if poll_results:
            return poll_results.pop(0)
        return [], True

    def callback(items: List[Dict[str, Any]]) -> None:
        collected_ids.extend(item["id"] for item in items)

    monkeypatch.setattr("crawl.wallstreetcn.time.sleep", fake_sleep)
    monkeypatch.setattr(monitor, "_fetch_new_items_for_poll", fake_fetch_for_poll)

    monitor.start(callback=callback)

    assert monitor.last_id == 105
    assert collected_ids == [105, 104, 103]


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
