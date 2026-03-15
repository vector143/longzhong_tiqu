from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import adapters as module
from monitor.adapter import MonitorStatus


def test_wallstreetcn_adapter_uses_runtime_project_relative_output_dir() -> None:
    adapter = module.WallStreetCNAdapter(channels=["oil-channel"])

    expected_dir = (
        Path(module.__file__).resolve().parent.parent / "output" / "report" / "cleaned"
    )
    assert Path(adapter.output_dir) == expected_dir


def test_wallstreetcn_adapter_exposes_detail_metadata() -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        important_only=True,
    )

    state = adapter.get_state()
    assert state.extra["important_only"] is True
    assert state.extra["output_dir"] == adapter.output_dir
    assert state.extra["channel_stats"] == {}


def test_wallstreetcn_adapter_records_standard_runtime_state_for_channel_poll() -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        interval=30,
    )
    started_at = datetime(2026, 3, 15, 9, 30, 0)
    finished_at = datetime(2026, 3, 15, 9, 30, 2)
    next_run_at = datetime(2026, 3, 15, 9, 30, 32)

    adapter._record_channel_poll_result(
        channel="oil-channel",
        started_at=started_at,
        finished_at=finished_at,
        new_count=2,
        next_run_at=next_run_at,
    )

    state = adapter.get_state()
    assert state.last_run == finished_at
    assert state.extra["last_success_at"] == finished_at
    assert state.extra["last_poll_started_at"] == started_at
    assert state.extra["last_poll_finished_at"] == finished_at
    assert state.extra["last_round_duration_seconds"] == 2.0
    assert state.extra["last_round_new"] == 2
    assert state.extra["next_run_at"] == next_run_at
    assert state.extra["channel_statuses"]["oil-channel"] == "running"
    assert state.extra["failed_channels"] == []


def test_wallstreetcn_adapter_run_now_broadcasts_to_all_channels() -> None:
    adapter = module.WallStreetCNAdapter(
        channels=["oil-channel", "gold-channel"],
        interval=30,
    )

    assert adapter._consume_run_now_broadcast(0) is None

    adapter.run_now()

    assert adapter._consume_run_now_broadcast(0) == 1
    assert adapter._consume_run_now_broadcast(0) == 1
    assert adapter._consume_run_now_broadcast(1) is None


def test_investing_adapter_marks_interval_unit_as_seconds() -> None:
    adapter = module.InvestingAdapter(channels=["economy"], interval=30)

    assert adapter.get_state().extra["interval_unit"] == "seconds"


def test_investing_adapter_uses_configurable_delay_and_max_pages(monkeypatch) -> None:
    captured = {}
    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda _seconds, poll_interval=0.2: False,
    )
    monkeypatch.setattr(
        adapter._monitor,
        "crawl_incremental",
        lambda channels, delay, max_pages: captured.update(
            {
                "channels": channels,
                "delay": delay,
                "max_pages": max_pages,
            }
        )
        or {"economy": 2},
    )

    adapter._run()

    assert captured == {
        "channels": ["economy"],
        "delay": 1.5,
        "max_pages": 5,
    }
    state = adapter.get_state()
    assert state.extra["delay"] == 1.5
    assert state.extra["max_pages"] == 5


def test_investing_adapter_tracks_standard_runtime_state_on_success(
    monkeypatch,
) -> None:
    started_at = datetime(2026, 3, 15, 9, 30, 0)
    finished_at = datetime(2026, 3, 15, 9, 30, 2)

    class _FakeDatetime:
        values = [started_at, finished_at]

        @classmethod
        def now(cls):
            if cls.values:
                return cls.values.pop(0)
            return finished_at

    adapter = module.InvestingAdapter(
        channels=["commodities", "economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    monkeypatch.setattr(module, "datetime", _FakeDatetime)
    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda _seconds, poll_interval=0.2: False,
    )
    monkeypatch.setattr(
        adapter._monitor,
        "crawl_incremental",
        lambda channels, delay, max_pages: {
            "commodities": 2,
            "economy": 0,
        },
    )

    adapter._run()

    state = adapter.get_state()
    assert state.last_run == finished_at
    assert state.extra["last_poll_started_at"] == started_at
    assert state.extra["last_poll_finished_at"] == finished_at
    assert state.extra["last_success_at"] == finished_at
    assert state.extra["last_round_duration_seconds"] == 2.0
    assert state.extra["last_round_new"] == 2
    assert state.extra["next_run_at"] == finished_at + timedelta(seconds=30)
    assert state.extra["channel_stats"] == {"commodities": 2, "economy": 0}
    assert state.extra["active_channels"] == ["commodities"]
    assert state.extra["consecutive_failures"] == 0
    assert state.extra["backoff_seconds"] == 0


def test_investing_adapter_tracks_backoff_state_on_failure(monkeypatch) -> None:
    failed_at = datetime(2026, 3, 15, 9, 30, 5)

    class _FakeDatetime:
        values = [failed_at, failed_at]

        @classmethod
        def now(cls):
            if cls.values:
                return cls.values.pop(0)
            return failed_at

    adapter = module.InvestingAdapter(
        channels=["economy"],
        interval=30,
        delay=1.5,
        max_pages=5,
    )

    monkeypatch.setattr(module, "datetime", _FakeDatetime)
    monkeypatch.setattr(
        adapter,
        "wait_interval",
        lambda _seconds, poll_interval=0.2: False,
    )

    def _raise_error(channels, delay, max_pages):
        del channels, delay, max_pages
        raise RuntimeError("boom")

    monkeypatch.setattr(adapter._monitor, "crawl_incremental", _raise_error)

    adapter._run()

    state = adapter.get_state()
    assert state.status == MonitorStatus.ERROR
    assert state.last_error == "Investing: boom"
    assert state.extra["last_poll_started_at"] == failed_at
    assert state.extra["last_poll_finished_at"] == failed_at
    assert state.extra["next_run_at"] == failed_at + timedelta(seconds=10)
    assert state.extra["consecutive_failures"] == 1
    assert state.extra["backoff_seconds"] == 10


def test_longzhong_adapter_marks_interval_unit_as_minutes() -> None:
    adapter = module.LongZhongAdapter(keywords=["原油"], interval=30)

    assert adapter.get_state().extra["interval_unit"] == "minutes"


def test_longzhong_adapter_delegates_control_to_embedded_runtime() -> None:
    class _DummyController:
        def __init__(self) -> None:
            self.pause_calls = 0
            self.resume_calls = 0
            self.run_now_calls = 0
            self.is_paused = False
            self.is_running = True

        def pause(self) -> None:
            self.pause_calls += 1
            self.is_paused = True

        def resume(self) -> None:
            self.resume_calls += 1
            self.is_paused = False

        def run_now(self) -> None:
            self.run_now_calls += 1

    controller = _DummyController()
    adapter = module.LongZhongAdapter(keywords=["原油"], interval=30)
    adapter._runtime = type("Runtime", (), {"controller": controller})()

    adapter.pause()
    adapter.resume()
    adapter.run_now()

    assert controller.pause_calls == 1
    assert controller.resume_calls == 1
    assert controller.run_now_calls == 1


def test_longzhong_adapter_maps_embedded_runtime_snapshot_to_unified_state() -> None:
    snapshot = {
        "status": "running",
        "last_error": None,
        "next_poll_time": datetime(2026, 3, 15, 9, 45, 0),
        "today_total": 7,
        "today_success": 5,
        "today_failed": 1,
        "today_skipped": 1,
        "total_polls": 3,
        "uptime_seconds": 120.0,
        "recent_articles": [
            type(
                "Article",
                (),
                {
                    "keyword": "原油",
                    "title": "测试文章",
                    "crawl_time": datetime(2026, 3, 15, 9, 31, 0),
                    "publish_time": "2026-03-15 09:30:00",
                },
            )()
        ],
        "poll_history": [
            type(
                "Poll",
                (),
                {
                    "keyword": "原油",
                    "poll_time": datetime(2026, 3, 15, 9, 32, 0),
                    "new_count": 4,
                    "success_count": 4,
                    "failed_count": 0,
                    "skipped_count": 1,
                    "elapsed_seconds": 2.5,
                },
            )()
        ],
    }

    class _DummyState:
        def get_snapshot(self):
            return snapshot

    adapter = module.LongZhongAdapter(keywords=["原油"], interval=30)
    adapter._runtime = type(
        "Runtime", (), {"state": _DummyState(), "controller": None}
    )()

    state = adapter.get_state()

    assert state.status == MonitorStatus.RUNNING
    assert state.items_count == 4
    assert state.total_items == 5
    assert state.last_run == datetime(2026, 3, 15, 9, 32, 0)
    assert state.extra["recent_items"][0]["title"] == "测试文章"
