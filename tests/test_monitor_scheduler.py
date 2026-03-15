from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl.pipeline import CrawlResult
from monitor.scheduler import CrawlScheduler
from monitor.state import MonitorState


class _DummyGate:
    def __init__(self) -> None:
        self.enter_count = 0

    def __enter__(self) -> "_DummyGate":
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _DummyRateLimiter:
    def __init__(self) -> None:
        self.acquire_count = 0

    def acquire(self, blocking: bool = True) -> bool:
        del blocking
        self.acquire_count += 1
        return True


def _make_settings() -> SimpleNamespace:
    monitor_cfg = SimpleNamespace(
        default_keyword="原油",
        poll_interval_minutes=10,
        max_pages_per_poll=3,
        early_stop_threshold=10,
        validate_session_before_poll=False,
        max_retries=0,
        retry_base_delay=0.0,
        requests_per_minute=60,
        min_request_interval=0.1,
    )
    crawler_cfg = SimpleNamespace(
        default_delay=0.0,
        project_code="demo",
    )
    output_cfg = SimpleNamespace(default_formats=["json"])
    return SimpleNamespace(
        monitor=monitor_cfg,
        crawler=crawler_cfg,
        output=output_cfg,
    )


def test_run_incremental_with_retry_does_not_wrap_incremental_with_request_gate(
    monkeypatch,
) -> None:
    monkeypatch.setattr("monitor.scheduler.get_settings", _make_settings)

    gate = _DummyGate()
    rate_limiter = _DummyRateLimiter()
    observed_kwargs = {}

    def fake_incremental_crawl(**kwargs) -> CrawlResult:
        observed_kwargs.update(kwargs)
        return CrawlResult(
            new_articles=[],
            skipped_count=0,
            success_count=1,
            failed_count=0,
            elapsed_time=0.01,
        )

    monkeypatch.setattr("monitor.scheduler.incremental_crawl", fake_incremental_crawl)

    scheduler = CrawlScheduler(
        state=MonitorState(),
        interval_minutes=1,
        keyword="原油",
        converter=object(),
        existing_ids=set(),
        output_formats=["json"],
        max_pages=3,
        early_stop_threshold=10,
        max_retries=0,
        request_gate=gate,
        rate_limiter=rate_limiter,
    )

    result = scheduler._run_incremental_with_retry()

    assert result.success_count == 1
    assert observed_kwargs["keyword"] == "原油"
    assert gate.enter_count == 0
    assert rate_limiter.acquire_count == 1
